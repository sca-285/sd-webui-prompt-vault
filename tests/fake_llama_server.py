#!/usr/bin/env python3
"""A stand-in for llama-server, for the checks: /health, and /v1/chat/completions that streams back what it was
given (how many messages, images and system words, then the last user words), a few words a chunk.
When asked to think (chat_template_kwargs.enable_thinking) it reasons first: as reasoning_content, or inside
<think> tags in the answer when FAKE_THINK=tags; asked not to, it still opens with an empty <think></think>, as Qwen3 does.
It refuses the newer memory flags when FAKE_OLD=1, as an old llama.cpp build does."""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

args = sys.argv[1:]
if os.environ.get("FAKE_OLD") and any(a in args for a in ("--no-kv-offload", "--no-mmproj-offload", "--cpu-moe")):
    print("error: invalid argument: --no-kv-offload", flush=True)
    sys.exit(1)
if os.environ.get("FAKE_OLD_FA") and "-fa" in args and args[args.index("-fa") + 1] in ("on", "off", "auto"):
    print(f"error: invalid argument: {args[args.index('-fa') + 1]}", flush=True)  # -fa took no value before mid 2025
    sys.exit(1)
port = int(args[args.index("--port") + 1])
model = args[args.index("-m") + 1] if "-m" in args else ""
# Gemma's and Mistral's chat templates refuse turns that do not alternate, as llama-server then does; Qwen's do not
STRICT = any(w in os.path.basename(model).lower() for w in ("gemma", "mistral"))
if "gemma-4" in os.path.basename(model).lower() and os.environ.get("FAKE_OLD_ARCH"):
    print("llama_model_load: error loading model: error loading model architecture: unknown model architecture: 'gemma4'", flush=True)
    sys.exit(1)
with open(os.environ.get("FAKE_ARGS_LOG", os.devnull), "a") as f:
    f.write(" ".join(args) + "\n")


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":  # a word of up to 9 letters is one token, a longer one two, a phrase one a word
            words = body["content"].split()
            tokens = [t for w in words for t in ([sum(map(ord, w)) % 50000] if len(w) <= 9 else [1, 2])]
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"tokens": tokens}).encode())
            return
        msgs = body["messages"]
        roles = [m["role"] for m in msgs if m["role"] != "system"]
        if os.environ.get("FAKE_BODY_LOG"):  # what each request asked, for the checks to read
            with open(os.environ["FAKE_BODY_LOG"], "a", encoding="utf-8") as f:
                f.write(json.dumps({"model": os.path.basename(model), "roles": [m["role"] for m in msgs],
                                    "system": next((m["content"] for m in msgs if m["role"] == "system"), ""),
                                    "images": sum(1 for m in msgs if isinstance(m["content"], list)
                                                  for p in m["content"] if p.get("type") == "image_url"),
                                    "temperature": body.get("temperature"), "stream": bool(body.get("stream")),
                                    "kwargs": body.get("chat_template_kwargs")}, ensure_ascii=False) + "\n")
        if STRICT and (any(m["role"] == "system" for m in msgs[1:]) or
                       any(r != ("user" if i % 2 == 0 else "assistant") for i, r in enumerate(roles))):
            self.send_response(500); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"error": {"code": 500, "type": "server_error",
                                                   "message": "Conversation roles must alternate user/assistant/user/assistant/..."}}).encode())
            return
        images = sum(1 for m in msgs if isinstance(m["content"], list) for p in m["content"] if p.get("type") == "image_url")
        last = msgs[-1]["content"]
        words = last if isinstance(last, str) else " ".join(p.get("text", "") for p in last if p.get("type") == "text")
        system = next((m["content"] for m in msgs if m["role"] == "system"), "")
        answer = f"messages={len(msgs)} images={images} system={len(system)} temp={body.get('temperature')} top_k={body.get('top_k')}" + \
            (f" blocked={len(body['logit_bias'])}" if body.get("logit_bias") else "") + f" | {words[:200]}"
        think = (body.get("chat_template_kwargs") or {}).get("enable_thinking")
        reason = f"the user wants {words[:40]}; a short answer will do"
        tags = os.environ.get("FAKE_THINK") == "tags"
        if not think:
            answer = "<think>\n\n</think>\n\n" + answer
        elif tags:
            answer = f"<think>{reason}</think>" + answer
        if "Reply with JSON only" in system:  # Verify's plan: what to look up
            asked = words.split("The user's message:\n", 1)[-1].split("\n\n", 1)[0]
            lazy = "no check" in asked or asked.startswith("lazy")  # a small model planning nothing
            answer = json.dumps({"queries": [] if lazy else [asked[:60]],
                                 "models": ["Illustrious XL"] if "checkpoint" in asked and not lazy else []})
        elif words.startswith("Before your answer reaches the user"):  # Verify's correction: what it was given
            answer = "REVISED | " + words.split("\n\n", 1)[-1][:400]
        if not body.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"message": {"content": answer}}]}).encode())
            return
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        if think and not tags:
            for i in range(0, len(reason), 9):
                chunk = {"choices": [{"delta": {"reasoning_content": reason[i:i + 9]}}]}
                self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")); self.wfile.flush()
                time.sleep(float(os.environ.get("FAKE_DELAY", "0.01")))
        for i in range(0, len(answer), 12):
            chunk = {"choices": [{"delta": {"content": answer[i:i + 12]}}]}
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")); self.wfile.flush()
            time.sleep(float(os.environ.get("FAKE_DELAY", "0.01")))
        self.wfile.write(b"data: [DONE]\n\n")


ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
