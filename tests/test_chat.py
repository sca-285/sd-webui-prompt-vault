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

# a thinking model: its reasoning comes apart from the answer, given by llama-server or between <think> tags
shared.opts.pv_chat_think = True
for how in ("reasoning_content", "tags"):
    os.environ["FAKE_THINK"] = how
    qwen.SERVER.stop()
    ev = send(cid, "think about a castle")
    thinking = "".join(e["thinking"] for e in ev if "thinking" in e)
    answer = "".join(e["delta"] for e in ev if "delta" in e)
    msg = ev[-1]["message"]
    assert thinking.startswith("the user wants think about a castle") and msg["thinking"] == thinking.strip(), (how, ev)
    assert "<think>" not in answer and "</think>" not in msg["text"] and answer == msg["text"], (how, msg)
shared.opts.pv_chat_think = False
os.environ.pop("FAKE_THINK")
ev = send(cid, "no thinking now")  # Qwen3's empty <think></think>: neither shown nor kept
assert "thinking" not in ev[-1]["message"] and not any("thinking" in e for e in ev), ev
assert ev[-1]["message"]["text"].startswith("messages=") and "".join(e["delta"] for e in ev if "delta" in e) == ev[-1]["message"]["text"]
split, got = chat._ThinkSplit(), []
for piece in ["<thi", "nk>wei", "gh it</th", "ink>the an", "swer"]:
    got += split.feed(piece)
assert "".join(p for k, p in got if k == "thinking") == "weigh it" and "".join(p for k, p in got if k == "delta") == "the answer", got
assert qwen.strip_thinking("<think>hmm</think>\n\n1girl, red hair") == "1girl, red hair"
assert qwen.strip_thinking("hmm, so</think>1girl") == "1girl" and qwen.strip_thinking("<think>cut off") == ""
print("thinking ok")

# versions: your message edited, an answer asked again; the earlier ones kept, with what followed them
vc = c.post(B + "/new").json()["chat"]["id"]
send(vc, "a cat")
send(vc, "make it orange")
def msgs(cid=None):
    return c.get(B + "/one", params={"id": cid or vc}).json()["chat"]["messages"]
first = msgs()
ev = send(vc, "", path="/regenerate")  # the last answer again
m = msgs()
assert len(m) == 4 and m[3]["versions"] == 2 and m[3]["version"] == 2 and "others" not in m[3], m[3]
ev = []
with c.stream("POST", B + "/edit", json={"id": vc, "message": first[0]["id"], "text": "a dog"}) as r:
    ev = [json.loads(x) for x in r.iter_lines() if x]
m = msgs()
assert len(m) == 2 and m[0]["text"] == "a dog" and m[0]["versions"] == 2 and m[0]["version"] == 2 and "a dog" in m[1]["text"], m
back = c.post(B + "/version", json={"id": vc, "message": m[0]["id"], "step": -1}).json()["chat"]["messages"]
assert [x["text"] for x in back[:3]] == ["a cat", first[1]["text"], "make it orange"] and back[3]["versions"] == 2, back
older = c.post(B + "/version", json={"id": vc, "message": back[3]["id"], "step": -1}).json()["chat"]["messages"]
assert older[3]["text"] == first[3]["text"] and older[3]["version"] == 1
assert c.post(B + "/version", json={"id": vc, "message": back[0]["id"], "step": -1}).json()["chat"]["messages"][0]["version"] == 1  # the first stays first
fwd = c.post(B + "/version", json={"id": vc, "message": back[0]["id"], "step": 1}).json()["chat"]["messages"]
assert len(fwd) == 2 and fwd[0]["text"] == "a dog"
with c.stream("POST", B + "/regenerate", json={"id": vc, "message": msgs()[1]["id"]}) as r:  # an answer in the middle
    list(r.iter_lines())
assert msgs()[1]["versions"] == 2
# kept through saving and import, with every version
data = json.loads(c.get(B + "/export", params={"id": vc, "fmt": "json"}).json()["text"])
imp = c.post(B + "/import", json={"data": data}).json()["chat"]
assert imp["messages"][0]["versions"] == 2 and imp["messages"][1]["versions"] == 2
again = c.post(B + "/version", json={"id": imp["id"], "message": imp["messages"][0]["id"], "step": -1}).json()["chat"]["messages"]
assert len(again) == 4 and again[3]["versions"] == 2
# nothing came of a new answer: the earlier one is back
qwen.SERVER.stop(); good = shared.opts.pv_llama_server_path; shared.opts.pv_llama_server_path = "/no/server"
r = c.post(B + "/regenerate", json={"id": vc})
shared.opts.pv_llama_server_path = good
m = msgs()
assert len(m) == 2 and m[1]["versions"] == 2 and m[1]["text"], m
assert c.post(B + "/edit", json={"id": vc, "message": m[1]["id"], "text": "x"}).status_code == 400  # only your own
print("versions ok")

# help with your own message: nothing is sent, nothing is kept
def assist(cid, mode, text):
    with c.stream("POST", B + "/assist", json={"id": cid, "mode": mode, "text": text, "context": "1girl, red hair"}) as r:
        assert r.status_code == 200, r.read()
        return [json.loads(x) for x in r.iter_lines() if x]
before = len(c.get(B + "/one", params={"id": cid}).json()["chat"]["messages"])
ev = assist(cid, "enhance", "make her look sad pls")
deltas = "".join(e["delta"] for e in ev if "delta" in e)
done = ev[-1]
assert done["done"] and f"system={len(chat.ENHANCE_SYSTEM)}" in done["text"] and done["text"] == deltas.strip(), ev
assert "messages=2 images=0" in deltas and "| The conversation so far" in deltas  # one system prompt, one request with the talk
ev = assist(cid, "write", "")
assert f"system={len(chat.WRITE_SYSTEM)}" in ev[-1]["text"], ev[-1]
ev = assist("", "write", "a castle")  # before any conversation
assert ev[-1]["done"] and "a castle" in ev[-1]["text"]
assert len(c.get(B + "/one", params={"id": cid}).json()["chat"]["messages"]) == before
assert c.post(B + "/assist", json={"id": cid, "mode": "enhance", "text": " "}).status_code == 400
assert c.post(B + "/assist", json={"id": cid, "mode": "poem", "text": "x"}).status_code == 400
assert chat.tidy_draft('Improved message: "Make her hair silver"') == "Make her hair silver"
assert chat.tidy_draft('She said "hi" and left') == 'She said "hi" and left'
seen, real = [], chat._stream
chat._stream = lambda messages, *a, **k: (seen.append(messages), iter(()))[1]
list(chat.assist(cid, "enhance", "make her look sad pls", "1girl, red hair"))
chat._stream = real
asked = seen[0][1]["content"]
assert seen[0][0]["content"] == chat.ENHANCE_SYSTEM and asked.endswith("make her look sad pls") and "1girl, red hair" in asked
assert asked.startswith("The conversation so far:") and "User: a red-haired knight" in asked, asked[:300]
print("assist ok")

# how full the context is, and what is kept for the answer (three times as much when the model thinks first)
x = c.get(B + "/one", params={"id": cid}).json()["chat"]["context"]
from lib_vault import settings as pv_settings
assert x["size"] == pv_settings.opt("pv_vlm_context") and x["reserve"] == pv_settings.opt("pv_chat_max_tokens") and 0 < x["used"] < x["room"] < x["size"], x
shared.opts.pv_chat_think = True
assert c.get(B + "/one", params={"id": cid}).json()["chat"]["context"]["room"] == x["room"] - 2 * x["reserve"]
shared.opts.pv_chat_think = False
assert chat._tokens("Cô gái tóc đỏ đứng dưới mưa", []) > chat._tokens("The girl with red hair in rain", [])  # accents count more
print("context meter ok")

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

# choosing the model from Muse's card: the .gguf files found, the projector picked for the model
from lib_vault import settings as pv_settings
vlm = os.path.join(pv_settings.webui_models_dir(), "VLM")
os.makedirs(os.path.join(vlm, "huihui-30b"), exist_ok=True)
for name in ("Qwen3VL-4B-Instruct-Q8_0.gguf", "mmproj-Qwen3VL-4B-Instruct-F16.gguf", "Qwen3VL-8B-Instruct-Q6_K.gguf",
             "mmproj-Qwen3VL-8B-Instruct-F16.gguf", os.path.join("huihui-30b", "Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated-Q4_K_M.gguf"),
             os.path.join("huihui-30b", "mmproj-F16.gguf")):
    fake_gguf(os.path.join(vlm, name), 36)
M = "/prompt-vault/api/qwen/models"
lst = c.get(M).json()
names = [m["name"] for m in lst["models"]]
assert "Qwen3VL-8B-Instruct-Q6_K.gguf" in names and all("mmproj" not in n for n in names), names
assert len(lst["mmprojs"]) == 4 and any(d.endswith("VLM") for d in lst["dirs"]), lst
pick = lambda name: next(m["path"] for m in lst["models"] if m["name"] == name)
got = c.post(M, json={"model": pick("Qwen3VL-8B-Instruct-Q6_K.gguf")}).json()
assert got["model"].endswith("Qwen3VL-8B-Instruct-Q6_K.gguf") and got["mmproj"].endswith("mmproj-Qwen3VL-8B-Instruct-F16.gguf"), got
got = c.post(M, json={"model": pick("Huihui-Qwen3-VL-30B-A3B-Instruct-abliterated-Q4_K_M.gguf")}).json()
assert got["mmproj"].endswith(os.path.join("huihui-30b", "mmproj-F16.gguf")), got["mmproj"]
got = c.post(M, json={"memory": "Low VRAM"}).json()
assert got["memory"] == "Low VRAM" and shared.opts.pv_vlm_memory == "Low VRAM"
assert c.post(M, json={"think": True}).json()["think"] and shared.opts.pv_chat_think is True
assert not c.post(M, json={"think": False}).json()["think"]
assert c.post(M, json={"model": "/nowhere/x.gguf"}).status_code == 400
assert c.post(M, json={"memory": "Lots"}).status_code == 400
print("model choice ok")

# a DFlash draft beside its model is not one to pick
fake_gguf(os.path.join(os.path.dirname(c.get(M).json()["models"][0]["path"]), "dflash-Qwen3.8-27B-ABLITERATED-BF16.gguf"), 5)
got = c.get(M).json()
assert not any("dflash" in m["name"] for m in got["models"]) and got["drafts"][0]["name"].startswith("dflash-"), got
assert qwen.DRAFT.search("Qwen3.8-27B-MTP-Q8_0.gguf") and not qwen.DRAFT.search("Qwen3.8-27B-Q4_K_M.gguf")
print("drafts ok")

# folders on another drive: several for Qwen, one for Prompt Vault's own models
other, third, own = (tempfile.mkdtemp(prefix=p) for p in ("drive-d-", "drive-e-", "pv-models-"))
fake_gguf(os.path.join(other, "Far-Qwen3-VL-8B.Q5_K_M.gguf"), 36)
fake_gguf(os.path.join(other, "Far-Qwen3-VL-8B.mmproj-f16.gguf"), 1)
os.environ["PV_FAR"] = third
F = "/prompt-vault/api/qwen/folders"
got = c.post(F, json={"qwen_dirs": f'"{other}"; $PV_FAR', "models_dir": own}).json()
assert any(m["name"] == "Far-Qwen3-VL-8B.Q5_K_M.gguf" for m in got["models"]), got["models"]
assert got["dirs"][:2] == [other, third] and got["models_base"] == own and not got["missing"], got
assert pv_settings.models_dir("wd14") == os.path.join(own, "wd14") and os.path.isdir(os.path.join(own, "wd14"))
far = next(m["path"] for m in got["models"] if m["name"].startswith("Far-"))
assert c.post(M, json={"model": far}).json()["mmproj"].endswith("Far-Qwen3-VL-8B.mmproj-f16.gguf")
bad = c.post(F, json={"qwen_dirs": "/no/such/drive"})
assert bad.status_code == 400 and "Not found" in bad.json()["error"]
assert c.post(F, json={"models_dir": "/no/such/place"}).status_code == 400
c.post(F, json={"qwen_dirs": "", "models_dir": ""})
assert pv_settings.models_base().endswith(os.path.join("models", "prompt_vault"))
print("folders ok")

assert c.post(B + "/send", json={"id": "nope", "text": "hi"}).status_code == 400
assert c.post(B + "/send", json={"id": big, "text": ""}).status_code == 400
c.post(B + "/delete", json={"id": big})
qwen.SERVER.stop()
print("ALL OK")
