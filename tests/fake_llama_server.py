#!/usr/bin/env python3
"""A stand-in for llama-server, for the checks: /health, and /v1/chat/completions that streams back what it was
given (how many messages, images and system words, then the last user words), a few words a chunk.
It refuses the newer memory flags when FAKE_OLD=1, as an old llama.cpp build does."""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

args = sys.argv[1:]
if os.environ.get("FAKE_OLD") and any(a in args for a in ("--no-kv-offload", "--no-mmproj-offload", "--cpu-moe")):
    print("error: invalid argument: --no-kv-offload", flush=True)
    sys.exit(1)
port = int(args[args.index("--port") + 1])
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
        msgs = body["messages"]
        images = sum(1 for m in msgs if isinstance(m["content"], list) for p in m["content"] if p.get("type") == "image_url")
        last = msgs[-1]["content"]
        words = last if isinstance(last, str) else " ".join(p.get("text", "") for p in last if p.get("type") == "text")
        system = next((m["content"] for m in msgs if m["role"] == "system"), "")
        answer = f"messages={len(msgs)} images={images} system={len(system)} | {words[:200]}"
        if not body.get("stream"):
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"choices": [{"message": {"content": answer}}]}).encode())
            return
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
        for i in range(0, len(answer), 12):
            chunk = {"choices": [{"delta": {"content": answer[i:i + 12]}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode()); self.wfile.flush()
            time.sleep(float(os.environ.get("FAKE_DELAY", "0.01")))
        self.wfile.write(b"data: [DONE]\n\n")


ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
