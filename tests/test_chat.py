"""Qwen Chat with a stand-in llama-server (tests/fake_llama_server.py): conversations, files, streaming, stop,
saving, exporting, importing; and where the model is placed (VRAM or RAM)."""
import base64, io, json, os, struct, sys, tempfile, threading, time
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from modules import shared
from lib_vault import api, chat, gguf, llama, qwen
from fastapi import FastAPI
from fastapi.testclient import TestClient

tmp = tempfile.mkdtemp()


def fake_gguf(path, layers, experts=0, size_mb=1):
    def s(x):
        b = x.encode()
        return struct.pack("<Q", len(b)) + b
    kv = [s("general.architecture") + struct.pack("<I", 8) + s("qwen3vl"),
          s("tokenizer.ggml.scores") + struct.pack("<I", 9) + struct.pack("<IQ", 6, 3) + struct.pack("<3f", 1, 2, 3),
          s("qwen3vl.block_count") + struct.pack("<I", 4) + struct.pack("<I", layers),
          s("qwen3vl.expert_count") + struct.pack("<I", 4) + struct.pack("<I", experts)]
    with open(path, "wb") as f:
        f.write(b"GGUF" + struct.pack("<IQQ", 3, 0, len(kv)) + b"".join(kv))
        f.truncate(size_mb * 1024 * 1024)


model, mmproj = os.path.join(tmp, "qwen.gguf"), os.path.join(tmp, "mmproj.gguf")
fake_gguf(model, 36, size_mb=8)
fake_gguf(mmproj, 1)
assert gguf.info(model) == {"arch": "qwen3vl", "layers": 36, "experts": 0, "context": 0}, gguf.info(model)
os.environ["FAKE_ARGS_LOG"] = os.path.join(tmp, "args.log")
for k, v in {"pv_llama_server_path": os.path.abspath("tests/fake_llama_server.py"), "pv_vlm_model_path": model,
             "pv_vlm_mmproj_path": mmproj, "pv_vlm_unload_sd": False, "pv_vlm_idle_minutes": 0, "pv_vlm_context": 4096,
             "pv_vlm_memory": "All on GPU", "pv_vlm_port": 18079}.items():
    setattr(shared.opts, k, v)

# ---- where the model goes
GB = 1024 ** 3
def placed(mode, free=None, size_gb=None):
    shared.opts.pv_vlm_memory = mode
    qwen._free_vram_gb = lambda: free
    real = os.path.getsize
    if size_gb:
        os.path.getsize = lambda p: size_gb * GB if p == model else real(p)
    try:
        return qwen._memory_args(model, mmproj)
    finally:
        os.path.getsize = real
assert placed("All on GPU")[:2] == ["-ngl", "99"]
assert "--no-kv-offload" in placed("KV cache in RAM")
assert placed("RAM only")[:2] == ["-ngl", "0"]
assert placed("Low VRAM")[:2] == ["-ngl", "18"], placed("Low VRAM")
assert placed("Auto", free=24, size_gb=8)[:2] == ["-ngl", "99"]
part = placed("Auto", free=9, size_gb=8)  # 9 GB free, 4 for SD: about half the layers
assert part[0] == "-ngl" and 10 <= int(part[1]) <= 25 and "--no-kv-offload" in part, part
fake_gguf(model, 48, experts=128, size_mb=8)
assert "--cpu-moe" in placed("Auto", free=9, size_gb=16), placed("Auto", free=9, size_gb=16)
assert "--cpu-moe" in placed("Low VRAM")
fake_gguf(model, 36, size_mb=8)
print("memory placement ok:", qwen.MEMORY["note"])
shared.opts.pv_vlm_memory = "KV cache in RAM"
qwen._free_vram_gb = lambda: None

app = FastAPI(); api.register(app); c = TestClient(app); B = "/prompt-vault/api/chat"


def send(cid, text, files=None, path="/send"):
    events = []
    with c.stream("POST", B + path, json={"id": cid, "text": text, "files": files or [], "context": ""}) as r:
        assert r.status_code == 200, r.read()
        for line in r.iter_lines():
            if line:
                events.append(json.loads(line))
    return events


cid = c.post(B + "/new").json()["chat"]["id"]
ev = send(cid, "a red-haired knight at sunset")
assert ev[0]["start"] and ev[-1]["done"], ev
deltas = [e["delta"] for e in ev if "delta" in e]
assert len(deltas) > 3 and "".join(deltas) == ev[-1]["message"]["text"], ev
assert ev[-1]["message"]["text"].startswith("messages=2 images=0") and "red-haired knight" in ev[-1]["message"]["text"]
one = c.get(B + "/one", params={"id": cid}).json()["chat"]
assert one["title"].startswith("a red-haired knight") and len(one["messages"]) == 2
print("chat ok:", ev[-1]["message"]["text"])

# the newer flags were given; an old build is started without them
assert "--no-kv-offload" in open(os.environ["FAKE_ARGS_LOG"]).read().splitlines()[-1]

# files: an image and a Markdown file
from PIL import Image
buf = io.BytesIO(); Image.new("RGB", (64, 48), (200, 30, 30)).save(buf, "PNG")
png = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
ev = send(cid, "what is in these?", [{"kind": "image", "name": "red.png", "data": png},
                                     {"kind": "text", "name": "notes.md", "data": "# Notes\nshe wears silver armor"}])
text = ev[-1]["message"]["text"]
assert "images=1" in text and "silver armor" in text and "what is in these?" in text, text
msgs = c.get(B + "/one", params={"id": cid}).json()["chat"]["messages"]
assert msgs[2]["files"][0]["kind"] == "image" and msgs[2]["files"][0]["url"].startswith("data:image/jpeg")
print("files ok")

# again: the last answer replaced
ev = send(cid, "", path="/regenerate")
assert ev[-1]["done"] and len(c.get(B + "/one", params={"id": cid}).json()["chat"]["messages"]) == 4

# stop in the middle
os.environ["FAKE_DELAY"] = "1.0"
qwen.SERVER.stop()
holder = {}
def talk():
    holder["ev"] = send(cid, "a long one, please " * 5)
t = threading.Thread(target=talk); t.start()
time.sleep(4.0)
c.post(B + "/stop", json={"id": cid})
stopped_at = time.time()
t.join(30)
print("stopped after %.1fs" % (time.time() - stopped_at))
os.environ["FAKE_DELAY"] = "0.01"
assert holder["ev"][-1]["done"] and holder["ev"][-1]["message"]["stopped"], holder["ev"][-1]
print("stop ok")

# keeping: save, export, open again, import
saved = c.post(B + "/save", json={"id": cid}).json()["chat"]["saved_as"]
assert saved and os.path.isfile(os.path.join(chat.chats_dir(), saved))
lst = c.get(B).json()
assert any(s["name"] == saved for s in lst["saved"]) and any(x["id"] == cid for x in lst["chats"])
md = c.get(B + "/export", params={"id": cid, "fmt": "md"}).json()
assert md["name"].endswith(".md") and "## You" in md["text"] and "## Qwen" in md["text"] and "[image: red.png]" in md["text"]
js = c.get(B + "/export", params={"id": cid, "fmt": "json"}).json()
data = json.loads(js["text"])
imp = c.post(B + "/import", json={"data": data}).json()["chat"]
assert imp["id"] != cid and len(imp["messages"]) == len(data["messages"])
chat._chats.pop(cid)  # as after a restart: only the saved one is left
back = c.post(B + "/open", json={"name": saved}).json()["chat"]
assert back["saved_as"] == saved and len(back["messages"]) == len(data["messages"])
send(back["id"], "and one more")  # a saved conversation stays saved as it goes on
with open(os.path.join(chat.chats_dir(), saved), encoding="utf-8") as f:
    assert len(json.load(f)["messages"]) == len(data["messages"]) + 2
c.post(B + "/unsave", json={"id": back["id"]})
assert not os.path.isfile(os.path.join(chat.chats_dir(), saved))
print("save, export, import ok")

# a long conversation keeps within the context: the oldest messages are left out
big = c.post(B + "/new").json()["chat"]["id"]
for i in range(6):
    ev = send(big, f"part {i} " + "word " * 900)
assert ev[0]["left_out"] > 0 and ev[-1]["done"], ev[0]
print("context window ok: left out", ev[0]["left_out"])

# an old llama.cpp without the memory flags
qwen.SERVER.stop()
os.environ["FAKE_OLD"] = "1"
ev = send(big, "still there?")
assert ev[-1]["done"] and "--no-kv-offload" not in open(os.environ["FAKE_ARGS_LOG"]).read().splitlines()[-1], ev[-1]
os.environ.pop("FAKE_OLD")
print("old build ok")

assert c.post(B + "/send", json={"id": "nope", "text": "hi"}).status_code == 400
assert c.post(B + "/send", json={"id": big, "text": ""}).status_code == 400
c.post(B + "/delete", json={"id": big})
qwen.SERVER.stop()
print("ALL OK")
