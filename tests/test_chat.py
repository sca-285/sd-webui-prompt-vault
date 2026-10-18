"""Qwen Chat with a stand-in llama-server (tests/fake_llama_server.py): conversations, files, streaming, stop,
saving, exporting, importing; and where the model is placed (VRAM or RAM)."""
import base64, io, json, os, re, struct, sys, tempfile, threading, time
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from modules import shared
from lib_vault import api, chat, context, docs, gguf, llama, qwen, verify
from fastapi import FastAPI
from fastapi.testclient import TestClient

tmp = tempfile.mkdtemp()


def fake_gguf(path, layers, experts=0, size_mb=1, arch="qwen3vl", name="", projector="", extra=None):
    def s(x):
        b = x.encode()
        return struct.pack("<Q", len(b)) + b
    kv = [s("general.architecture") + struct.pack("<I", 8) + s("clip" if projector else arch)]
    kv += [s("general.name") + struct.pack("<I", 8) + s(name)] if name else []
    kv += [s("clip.projector_type") + struct.pack("<I", 8) + s(projector)] if projector else []
    kv += [
          s("tokenizer.ggml.scores") + struct.pack("<I", 9) + struct.pack("<IQ", 6, 3) + struct.pack("<3f", 1, 2, 3),
          s(f"{arch}.block_count") + struct.pack("<I", 4) + struct.pack("<I", layers),
          s(f"{arch}.expert_count") + struct.pack("<I", 4) + struct.pack("<I", experts)]
    for key, value in (extra or {}).items():  # numbers as uint32, words as strings, floats as float32
        kind, packed = (8, s(value)) if isinstance(value, str) else (6, struct.pack("<f", value)) if isinstance(value, float) \
            else (4, struct.pack("<I", value))
        kv.append(s(key) + struct.pack("<I", kind) + packed)
    with open(path, "wb") as f:
        f.write(b"GGUF" + struct.pack("<IQQ", 3, 0, len(kv)) + b"".join(kv))
        f.truncate(size_mb * 1024 * 1024)


model, mmproj = os.path.join(tmp, "qwen.gguf"), os.path.join(tmp, "mmproj.gguf")
fake_gguf(model, 36, size_mb=8)
fake_gguf(mmproj, 1, projector="qwen3vl_merger")
assert gguf.info(model) == {"arch": "qwen3vl", "layers": 36, "experts": 0, "context": 0, "name": "", "basename": "", "size": "",
                            "projector": "", "attention": {}}, gguf.info(model)
os.environ["FAKE_ARGS_LOG"] = os.path.join(tmp, "args.log")
for k, v in {"pv_llama_server_path": os.path.abspath("tests/fake_llama_server.py"), "pv_vlm_model_path": model,
             "pv_vlm_mmproj_path": mmproj, "pv_vlm_unload_sd": False, "pv_vlm_idle_minutes": 0, "pv_vlm_context": 4096,
             "pv_vlm_memory": "All on GPU", "pv_vlm_port": 18079}.items():
    setattr(shared.opts, k, v)

# ---- the context: its memory (KV cache), stretching it past what the model was trained for, the window
GB = 1024 ** 3
q3 = os.path.join(tmp, "Qwen3-32B-Q4_K_M.gguf")  # Qwen3-32B's shape: 64 layers, 8 KV heads of 128, trained for 40K
fake_gguf(q3, 64, arch="qwen3", extra={"qwen3.context_length": 40960, "qwen3.embedding_length": 5120, "qwen3.attention.head_count": 64,
                                       "qwen3.attention.head_count_kv": 8, "qwen3.attention.key_length": 128, "qwen3.attention.value_length": 128})
assert gguf.info(q3)["attention"]["attention.head_count_kv"] == 8 and gguf.info(q3)["context"] == 40960
assert abs(context.kv_gb(q3, 32768, "f16") - 8.0) < 0.01  # 256 KB a token
assert abs(context.kv_gb(q3, 32768, "q8_0") - 4.25) < 0.01 and abs(context.kv_gb(q3, 32768, "q4_0") - 2.25) < 0.01
g3 = os.path.join(tmp, "gemma-3-27b-it.gguf")  # Gemma 3: 5 layers in 6 keep only the last 1024 tokens
fake_gguf(g3, 62, arch="gemma3", extra={"gemma3.context_length": 131072, "gemma3.embedding_length": 5376, "gemma3.attention.head_count": 32,
                                        "gemma3.attention.head_count_kv": 16, "gemma3.attention.key_length": 128,
                                        "gemma3.attention.value_length": 128, "gemma3.attention.sliding_window": 1024})
full = 62 * 16 * 256 * 2
assert abs(context.kv_gb(g3, 32768, "f16") - (full / 6 * 32768 + full * 5 / 6 * 1024) / GB) < 0.001, context.kv_gb(g3, 32768, "f16")
hy = os.path.join(tmp, "Qwen3.5-hybrid.gguf")  # a hybrid: one layer in 4 attends
fake_gguf(hy, 48, arch="qwen35", extra={"qwen35.embedding_length": 4096, "qwen35.attention.head_count": 32,
                                       "qwen35.attention.head_count_kv": 4, "qwen35.full_attention_interval": 4})
assert abs(context.kv_gb(hy, 8192, "f16") - 12 * 4 * 256 * 2 * 8192 / GB) < 0.001
assert context.kv_gb(model, 8192, "f16") == 8192 / 1024 * 0.14  # a file that does not say: the rule of thumb
shared.opts.pv_vlm_context = 131072; shared.opts.pv_vlm_rope = "Auto"; shared.opts.pv_vlm_kv_type = "q8_0"
assert context.server_args(q3) == ["-c", "131072", "-ctk", "q8_0", "-ctv", "q8_0", "-fa", "on", "--rope-scaling", "yarn", "--rope-scale", "3.2",
                                   "--yarn-orig-ctx", "40960"], context.server_args(q3)
assert context.server_args(g3) == ["-c", "131072", "-ctk", "q8_0", "-ctv", "q8_0", "-fa", "on"]  # trained for 128K already
shared.opts.pv_vlm_rope = "Off"
assert context.server_args(q3)[:2] == ["-c", "40960"] and "--rope-scaling" not in context.server_args(q3)
assert context.describe(q3)["rope"] == "held to the model's own"
scaled = os.path.join(tmp, "Qwen3-yarn.gguf")  # the file says it is stretched already: never again
fake_gguf(scaled, 64, arch="qwen3", extra={"qwen3.context_length": 131072, "qwen3.rope.scaling.type": "yarn", "qwen3.rope.scaling.factor": 4.0})
shared.opts.pv_vlm_rope = "Auto"; shared.opts.pv_vlm_context = 32768
assert context.rope_args(scaled) == [] and context.rope_args(q3) == []
shared.opts.pv_vlm_context = 4096; shared.opts.pv_vlm_kv_type = "f16"
assert context.server_args(model) == ["-c", "4096"]
# flash attention: Auto leaves it to the server unless the cache is quantized; On, Off; a -fa of your own wins
shared.opts.pv_vlm_kv_type = "q4_0"
assert context.server_args(model) == ["-c", "4096", "-ctk", "q4_0", "-ctv", "q4_0", "-fa", "on"]
shared.opts.pv_vlm_kv_type = "f16"; shared.opts.pv_vlm_flash = "On"
assert context.flash_args() == ["-fa", "on"]
shared.opts.pv_vlm_flash = "Off"
assert context.flash_args() == ["-fa", "off"]
shared.opts.pv_vlm_extra_args = "--threads 8 -fa"
assert context.flash_args() == []
shared.opts.pv_vlm_extra_args = ""; shared.opts.pv_vlm_flash = "Auto"
assert llama._old_flash(["x", "-fa", "on", "-c", "1"]) == ["x", "-fa", "-c", "1"] and llama._old_flash(["-fa", "off", "y"]) == ["y"]
# the window: all that fits; when it moves, it moves far, and then stays put while the rest fits (the server's cache)
shared.opts.pv_chat_max_tokens = 1024; shared.opts.pv_chat_think = False
conv = {"system": "", "messages": [{"id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant", "text": "", "tokens": 400} for i in range(6)]}
assert context.window(conv) == (conv["messages"], 0) and "start" not in conv  # 2400 of 3008: all
conv["messages"] += [{"id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant", "text": "", "tokens": 400} for i in range(6, 10)]
kept, left = context.window(conv)
assert left == 6 and kept[0]["id"] == "m6" and conv["start"] == "m6", (left, conv.get("start"))  # down to 70%, from a message of yours
conv["messages"] += [{"id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant", "text": "", "tokens": 400} for i in range(10, 12)]
assert context.window(conv)[0][0]["id"] == "m6"  # the same start: the cache of it is used again
conv["messages"] += [{"id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant", "text": "", "tokens": 400} for i in range(12, 14)]
assert context.window(conv)[0][0]["id"] == "m10" and conv["start"] == "m10"
del conv["messages"][2:]
assert context.window(conv) == (conv["messages"], 0) and "start" not in conv  # all fits again: from the first
assert llama.explain("V cache quantization requires flash_attn").startswith("A q8_0 or q4_0 KV cache needs flash attention")
print("context ok")


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

# what llama-server streams is UTF-8 with no charset said: curly quotes and Vietnamese come through whole
u8 = c.post(B + "/new").json()["chat"]["id"]
ev = send(u8, "“Come closer,” he said — the day’s cô gái tóc đỏ")
assert "“Come closer,” he said — the day’s cô gái tóc đỏ" in ev[-1]["message"]["text"], ev[-1]["message"]["text"]
c.post(B + "/delete", json={"id": u8})
broken = "“Come closer,” he said. cô gái — day’s".encode("utf-8").decode("latin-1")
assert chat.unmangle(broken) == "“Come closer,” he said. cô gái — day’s"
for fine in ("“Come closer,” he said. cô gái", "café, naïve, Ünïcödé", "plain"):
    assert chat.unmangle(fine) == fine
imp = c.post(B + "/import", json={"data": {"title": "old", "messages": [{"role": "assistant", "text": broken}]}}).json()["chat"]
assert imp["messages"][0]["text"].startswith("“Come closer,”"), imp["messages"][0]["text"]
c.post(B + "/delete", json={"id": imp["id"]})
print("utf-8 ok")

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

# PDF (text, or a scanned one's pages as images), JSON laid out, and text cut to what the context holds
def text_pdf(pages):
    objs, kids = [], []
    font = 3 + 2 * len(pages)
    for i, words in enumerate(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({words}) Tj ET".encode()
        kids.append(3 + 2 * i)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R /Resources << /Font << /F1 {font} 0 R >> >> >>".encode())
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()] \
        + objs + [b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for n, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer << /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return "data:application/pdf;base64," + base64.b64encode(out).decode()
got = chat.read_files([{"kind": "pdf", "name": "brief.pdf", "data": text_pdf(["A knight in silver armor at dawn", "The castle burns behind her"])}])
assert got[0]["kind"] == "text" and got[0]["pdf"] and got[0]["pages"] == 2, got
assert "--- page 1 ---\nA knight in silver armor at dawn" in got[0]["text"] and "--- page 2 ---\nThe castle burns" in got[0]["text"]
buf = io.BytesIO()
Image.new("RGB", (300, 200), (20, 120, 200)).save(buf, "PDF")
scanned = "data:application/pdf;base64," + base64.b64encode(buf.getvalue()).decode()
got = chat.read_files([{"kind": "pdf", "name": "scan.pdf", "data": scanned}])  # with a model that sees: read by it (OCR)
assert got[0]["kind"] == "text" and got[0]["ocr"]["todo"] == [1] and got[0]["text"] == "--- page 1 ---\n" + docs.UNREAD, got[0]["text"]
shared.opts.pv_chat_ocr = False  # no OCR: the first pages as images
got = chat.read_files([{"kind": "pdf", "name": "scan.pdf", "data": scanned}])
assert got[0]["kind"] == "image" and got[0]["name"] == "scan.pdf · page 1" and got[0]["url"].startswith("data:image/jpeg"), got
shared.opts.pv_chat_ocr = True
got = chat.read_files([{"kind": "text", "name": "card.json", "data": '{"name":"Aiko","hair":"red","tags":["1girl","sundress"]}'}])
assert got[0]["text"].startswith('{\n "name": "Aiko"'), got[0]["text"]
assert chat.read_files([{"kind": "text", "name": "broken.json", "data": "{not json"}])[0]["text"] == "{not json"
got = chat.read_files([{"kind": "text", "name": "novel.md", "data": "word " * 50000}])
assert not got[0]["cut"] and len(got[0]["text"]) == 250000  # kept whole: what the model reads is chosen each turn
pdfc = c.post(B + "/new").json()["chat"]["id"]
ev = send(pdfc, "what is this about?", [{"kind": "pdf", "name": "brief.pdf", "data": text_pdf(["A knight in silver armor at dawn"])}])
assert ev[-1]["done"] and "File brief.pdf" in ev[-1]["message"]["text"], ev[-1]  # the model was given its text
msg = c.get(B + "/one", params={"id": pdfc}).json()["chat"]["messages"][0]
assert msg["files"][0]["name"] == "brief.pdf" and msg["files"][0]["pdf"]
r = c.post(B + "/send", json={"id": pdfc, "text": "x", "files": [{"kind": "pdf", "name": "bad.pdf", "data": "data:application/pdf;base64,bm90IGEgcGRm"}]})
assert r.status_code == 400 and "cannot be read" in r.json()["error"], r.json()
c.post(B + "/delete", json={"id": pdfc})
print("pdf, json, long text ok")

# scanned pages: read by the vision model before the answer, page by page; a PDF with text and scanned pages mixed;
# stopped half way, the rest is read with the next message
import pypdf
def scan_pdf(n):
    pages = [Image.new("RGB", (400, 560), (30 * i, 90, 160)) for i in range(n)]
    buf = io.BytesIO()
    pages[0].save(buf, "PDF", save_all=True, append_images=pages[1:])
    return buf.getvalue()
writer = pypdf.PdfWriter()
for part in (base64.b64decode(text_pdf(["Chapter one: a knight in silver armor at dawn"]).split(",", 1)[1]), scan_pdf(2)):
    for page in pypdf.PdfReader(io.BytesIO(part)).pages:
        writer.add_page(page)
mixed = io.BytesIO(); writer.write(mixed)
mixed_url = "data:application/pdf;base64," + base64.b64encode(mixed.getvalue()).decode()
f = chat.read_files([{"kind": "pdf", "name": "mixed.pdf", "data": mixed_url}])[0]
assert f["pages"] == 3 and f["ocr"]["todo"] == [2, 3] and "Chapter one: a knight" in f["text"], f["text"]
stop_now = threading.Event()
steps = chat._ocr(f, stop_now)
assert next(steps)["step"] == "Reading the scan of mixed.pdf: page 2 (1 of 2)…"
stop_now.set()
assert list(steps) == [] and f["ocr"]["todo"] == [3] and f["ocr_pages"] == 1  # stopped: page 2 read, 3 left
assert "images=1" in docs.parts(f)[1][1] and docs.parts(f)[2][1] == docs.UNREAD, docs.parts(f)
oc = c.post(B + "/new").json()["chat"]["id"]
ev = send(oc, "what is on these pages?", [{"kind": "pdf", "name": "scan.pdf", "data": "data:application/pdf;base64," + base64.b64encode(scan_pdf(3)).decode()}])
steps = [e["step"] for e in ev if "step" in e]
assert steps == [f"Reading the scan of scan.pdf: page {n} ({n} of 3)…" for n in (1, 2, 3)] and ev[-1]["done"], steps
shown = c.get(B + "/one", params={"id": oc}).json()["chat"]["messages"][0]["files"][0]
assert shown["unread"] == 0 and shown["ocr_pages"] == 3 and "ocr" not in shown, shown
inner = chat._chats[oc]["messages"][0]["files"][0]
assert "ocr" not in inner and docs.UNREAD not in inner["text"] and inner["text"].count("Transcribe this page.") == 3, inner["text"][:300]
ev = send(oc, "and page 2?")
assert not [e for e in ev if "step" in e]  # read once
c.post(B + "/delete", json={"id": oc})
print("ocr ok")

# a PDF of 150 pages: kept whole; the model reads the pages on the question, the pages asked for by number, and for
# a question about all of it, notes on every part (written once)
from lib_vault import docs
book = [f"Page {n}: notes on castle walls, moats and gate towers of the old kingdom, chapter {n // 10}." for n in range(1, 151)]
book[96] = "Page 97: the dragon is named Vermithrax and sleeps under the bell tower."
prompt_log = os.path.join(tmp, "prompt.json")
os.environ["FAKE_PROMPT_LOG"] = prompt_log
qwen.SERVER.stop()  # started again with the log
def read_prompt():
    msgs = json.load(open(prompt_log, encoding="utf-8"))
    return "\n".join(p["text"] if isinstance(p, dict) else str(p) for m in msgs
                     for p in (m["content"] if isinstance(m["content"], list) else [m["content"]]) if not isinstance(p, dict) or "text" in p)
bc = c.post(B + "/new").json()["chat"]["id"]
ev = send(bc, "what is the dragon named?", [{"kind": "pdf", "name": "kingdom.pdf", "data": text_pdf(book)}])
seen_text = read_prompt()
room = chat._file_room(chat._chats[bc])
assert ev[-1]["done"] and "--- page 97 ---\nPage 97: the dragon is named Vermithrax" in seen_text, seen_text[:500]
assert "[150 pages, too long to read at once" in seen_text and len(seen_text) < room + 1500, (len(seen_text), room)
shown = c.get(B + "/one", params={"id": bc}).json()["chat"]["messages"][0]["files"][0]
assert shown["pages"] == 150 and "text" not in shown and shown["chars"] > 10000 and not shown["notes"], shown  # the page gets no text
full = chat._chats[bc]["messages"][0]["files"][0]
assert len(full["text"]) == shown["chars"] and "Page 150:" in full["text"]
assert chat._chats[bc]["messages"][0]["tokens"] < chat._tokens("", [full])  # counted as what the model reads of it
ev = send(bc, "now read pages 140-142 for me")
seen_text = read_prompt()
assert all(f"--- page {n} ---" in seen_text for n in (140, 141, 142)), seen_text[:300]
assert docs.asked_pages("trang 3 đến 5, page 9") == [3, 4, 5, 9] and docs.wants_whole("tóm tắt cả tài liệu này")
ev = send(bc, "summarize the whole document")
steps = [e["step"] for e in ev if "step" in e]
assert steps and steps[0].startswith("Reading kingdom.pdf: page 1–") and steps[-1].endswith("…") and ev[-1]["done"], steps
assert "of 1)" not in steps[0] and len(steps) >= 2, steps
seen_text = read_prompt()
assert "Notes on the whole document:" in seen_text and "- page 1–" in seen_text
assert c.get(B + "/one", params={"id": bc}).json()["chat"]["messages"][0]["files"][0]["notes"]
ev = send(bc, "and the main points again?")  # read once: not again
assert not [e for e in ev if "step" in e] and ev[-1]["done"]
os.environ.pop("FAKE_PROMPT_LOG")
c.post(B + "/delete", json={"id": bc})
print("long pdf ok")

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
    ev = send(c.post(B + "/new").json()["chat"]["id"], "think about a castle")
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
r = c.post(B + "/emoji", json={"hint": "sad cat in the rain"})
assert r.status_code == 200 and isinstance(r.json()["emoji"], list), r.text  # the fake answers words: no emoji
assert c.post(B + "/emoji", json={"hint": ""}).json()["emoji"] == []
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

# presets: built in, yours, the default for new conversations
from lib_vault import chat_presets
P = B + "/presets"
pr = c.get(P).json()
assert [p["id"] for p in pr["builtin"]] == ["assistant", "general", "search", "translator", "tagger", "natural", "video", "director", "story"] \
    and pr["default"] == "assistant"
assert [p["id"] for p in pr["builtin"] if p.get("search")] == ["search"]
assert all(p["text"] and p["name"] and p["hint"] for p in pr["builtin"]) and "image-to-video" in chat_presets.find("video")["text"]
assert "adult" in chat_presets.find("story")["text"]
v = c.post(B + "/new", json={"preset": "video"}).json()["chat"]
assert v["preset"] == "video" and v["system"] == chat_presets.find("video")["text"]
assert c.post(B + "/new").json()["chat"]["preset"] == "assistant"
got = c.post(P + "/save", json={"name": "Wan 2.2 motion", "text": "Only motion, 50 words."}).json()
assert got["saved"] == "my-wan-2-2-motion" and got["mine"][0]["name"] == "Wan 2.2 motion"
assert c.post(P + "/save", json={"name": "Wan 2.2 motion", "text": "Only motion, 60 words."}).json()["mine"][0]["text"].endswith("60 words.")
assert c.post(P + "/default", json={"id": "my-wan-2-2-motion"}).json()["default"] == "my-wan-2-2-motion"
n = c.post(B + "/new").json()["chat"]
assert n["preset"] == "my-wan-2-2-motion" and n["system"] == "Only motion, 60 words."
u = c.post(B + "/update", json={"id": n["id"], "system": "Only motion, 60 words. In Vietnamese.", "preset": "my-wan-2-2-motion"}).json()["chat"]
assert u["preset"] == "" and u["system"].endswith("Vietnamese.")  # changed by hand: no preset any more
assert c.post(P + "/delete", json={"id": "tagger"}).status_code == 400
assert c.post(P + "/default", json={"id": "nope"}).status_code == 400
after = c.post(P + "/delete", json={"id": "my-wan-2-2-motion"}).json()
assert not after["mine"] and after["default"] == "assistant"
assert c.get(B).json()["presets"]["builtin"][6]["id"] == "video"
for x in (v, n):
    c.post(B + "/delete", json={"id": x["id"]})
print("presets ok")

# banned words: a one-token word blocked while Qwen writes, a phrase asked to be avoided, hits reported
bw = c.post(B + "/banned", json={"text": "tapestry\nshivers down her spine, Kaleidoscope; tapestry"}).json()
assert bw["words"] == ["tapestry", "shivers down her spine", "Kaleidoscope"], bw
assert c.get(B).json()["banned"].startswith("tapestry") and "testament" in c.get(B).json()["cliches"]
bc = c.post(B + "/new").json()["chat"]["id"]
ev = send(bc, "a tapestry of light")
t = ev[-1]["message"]["text"]
# tapestry: one token, in 4 capitals x with and without a space (some the same) -> blocked; kaleidoscope: two tokens -> only asked
assert " blocked=" in t and ev[-1]["message"]["banned_hits"] == ["tapestry"], ev[-1]["message"]
assert chat._logit_bias("http://127.0.0.1:1", "none", ["shivers down"]) == []  # a phrase is never blocked token by token
assert chat.banned_in("Shivers down her spine, a TAPESTRY.") == ["tapestry", "shivers down her spine"]
assert chat.banned_in("tapestries") == []
asked = chat._ask_to_avoid([{"role": "system", "content": "Be brief."}], chat.banned())
assert asked[0]["content"].startswith("Be brief.") and "shivers down her spine" in asked[0]["content"]
c.post(B + "/banned", json={"text": ""})
ev = send(bc, "again, nothing banned")
assert "blocked=" not in ev[-1]["message"]["text"] and "banned_hits" not in ev[-1]["message"]
c.post(B + "/delete", json={"id": bc})
print("banned words ok")

# Verify: a draft, looked up on the web and its tags on Danbooru, corrected, then the answer
import fake_web
web = fake_web.start()
def seen_tavily(i):
    return [b for p, b in fake_web.seen if p == "/search" and "query" in b][i]
os.environ.update(PV_TAVILY_URL=web, PV_DDG_URL=web, PV_DDG_LITE_URL=web, PV_BRAVE_URL=web, PV_CIVITAI_URL=web, PV_WIKIPEDIA_URL=web, PV_DANBOORU_URL=web)
from lib_vault import websearch
def ask(cid, text, verify=True, path="/send"):
    with c.stream("POST", B + path, json={"id": cid, "text": text, "files": [], "context": "", "verify": verify}) as r:
        assert r.status_code == 200, r.read()
        return [json.loads(x) for x in r.iter_lines() if x]
vc = c.post(B + "/new").json()["chat"]["id"]
ev = ask(vc, "best sampler for illustrious xl")
steps = [e["step"] for e in ev if "step" in e]
assert steps[:3] == ["Writing a first draft…", "Choosing what to check…", "Searching: best sampler for illustrious xl"], steps
assert steps[3] == "Reading 2 pages…" and steps[-1].startswith("Correcting"), steps
m = ev[-1]["message"]
v = m["verify"]
assert v["sources"][0] == {"n": 1, "title": "Guide to best sampler for illustrious xl", "url": web + "/page/guide?x=1&y=2", "read": True}, v
assert v["sources"][1]["title"] == "Second “page”" and not v["sources"][1]["read"] and len(v["sources"]) == 2  # the advert left out
assert v["draft"].startswith("messages=2") and not v["problems"], v
# the page was read: the passage on the point, not its menu, scripts or the snippet
assert m["text"].startswith("REVISED | [1] Guide to") and "Euler a with 28 steps and CFG 5" in m["text"], m["text"]
assert "Sampler menu" not in m["text"] and "tracking" not in m["text"] and "Paragraph 3 " not in m["text"]
assert "".join(e.get("delta", "") for e in ev).strip() == m["text"]  # only the corrected answer is streamed
# a checkpoint named: Civitai's page of it too
ev = ask(vc, "which checkpoint is Illustrious XL based on")
v = ev[-1]["message"]["verify"]
assert v["models"] == ["Illustrious XL"] and "Looking up Illustrious XL on Civitai…" in [e.get("step") for e in ev], v
civ = next(x for x in v["sources"] if "Civitai" in x["title"])
assert civ["url"] == "https://civitai.com/models/795765" and civ["read"]
civ_text = websearch.civitai("Illustrious XL")[0]["text"]
assert civ_text.startswith("Checkpoint · base model Illustrious · version v2.0 · trigger words: masterpiece, best quality. Use CFG 5"), civ_text
# a small model planning nothing for a question of fact: the question itself is searched
ev = ask(vc, "lazy: what CFG for Pony v6")
assert ev[-1]["message"]["verify"]["queries"] == ["lazy: what CFG for Pony v6"] and ev[-1]["message"]["verify"]["sources"]
# DuckDuckGo asking for a captcha: its lite page instead, and said so (the page has nothing on "captcha": its snippet)
ev = ask(vc, "captcha me")
v = ev[-1]["message"]["verify"]
assert v["sources"][0]["title"] == "Lite guide" and not v["sources"][0]["read"] and "captcha" in v["problems"][0], v
# a prompt with made-up tags: Danbooru says which do not exist, and what is close
ev = ask(vc, "no check, just tags:\n```\n1girl, (red hair:1.2), glowing tapestry hair, sun dres, masterpiece, hatsune miku \\(cosplay\\)\n```")
v = ev[-1]["message"]["verify"]
assert not v["queries"] and [t["tag"] for t in v["tags"]] == ["glowing tapestry hair", "sun dres"], v
assert v["tags"][0]["suggest"] == ["glowing_hair", "long_hair"] and v["tags"][1]["suggest"] == ["sundress"]
assert "Not Danbooru tags: glowing tapestry hair (instead: glowing hair, long hair); sun dres (instead: sundress)" in ev[-1]["message"]["text"]
# nothing to look up and nothing wrong: the draft is the answer, no second pass
ev = ask(vc, "no check please")
assert ev[-1]["message"]["text"].startswith("messages=") and not any(e.get("step", "").startswith("Correcting") for e in ev)
# the search failing: Wikipedia instead; Off: nothing searched, still answers
ev = ask(vc, "fail this one")
v = ev[-1]["message"]["verify"]
assert v["sources"][0]["title"] == "Illustrious XL" and v["problems"][0].startswith("DuckDuckGo"), v
shared.opts.pv_search_engine = "Off"
n = len(fake_web.seen)
ev = ask(vc, "anything")
assert not ev[-1]["message"]["verify"]["sources"] and len(fake_web.seen) == n and ev[-1]["done"]
shared.opts.pv_search_engine = "SearXNG"; shared.opts.pv_searxng_url = web
ev = ask(vc, "what is the answer")
assert ev[-1]["message"]["verify"]["sources"][0]["url"] == "https://searx.example/one"
# Auto: SearXNG when set, else Brave with a key, else DuckDuckGo
shared.opts.pv_search_engine = "Auto"
assert websearch.search_all("x")[0][0]["engine"] == "SearXNG"
shared.opts.pv_searxng_url = ""; shared.opts.pv_brave_key = "brave-key"
found, problems = websearch.search_all("x")
assert found[0]["engine"] == "Brave" and found[0]["title"] == "From Brave" and not problems
shared.opts.pv_brave_key = "wrong"
found, problems = websearch.search_all("x")
assert found[0]["engine"] == "DuckDuckGo" and problems[0].startswith("Brave: 401"), problems
shared.opts.pv_brave_key = ""
# Tavily, first in Auto when it has a key: its results come with their passages, so its pages are not opened again
shared.opts.pv_tavily_key = "tavily-key"
found, problems = websearch.search_all("illustrious xl cfg")
assert found[0]["engine"] == "Tavily" and found[0]["read"] and not found[1]["read"] and not problems, found
assert seen_tavily(-1)["search_depth"] == "advanced" and seen_tavily(-1)["chunks_per_source"] == 3
n = len(fake_web.seen)
ev = ask(vc, "best cfg for illustrious xl")
v = ev[-1]["message"]["verify"]
assert v["sources"][0]["title"] == "Tavily on best cfg for illustrious xl" and v["sources"][0]["read"], v
assert "Reading 1 pages…" in [e.get("step") for e in ev]  # only the short one is opened
assert [p for p, _ in fake_web.seen[n:] if p.startswith("/page/")] == ["/page/guide"]
shared.opts.pv_tavily_key = "wrong"
found, problems = websearch.search_all("x")
assert found[0]["engine"] == "DuckDuckGo" and problems[0] == "Tavily: refused the key (HTTP 401)", problems
# the Web search preset: every message searched first, answered from the results (no draft), follow-ups too
shared.opts.pv_tavily_key = "tavily-key"
sc = c.post(B + "/new", json={"preset": "search"}).json()["chat"]
assert sc["preset"] == "search"
qwen.SERVER.stop(); os.environ["FAKE_PROMPT_LOG"] = os.path.join(tmp, "search-prompt.json")
ev = ask(sc["id"], "latest illustrious xl version", verify=False)
steps = [e["step"] for e in ev if "step" in e]
assert steps == ["Choosing what to search…", "Searching: latest illustrious xl version", "Reading 1 pages…", "Answering from what was found…"], steps
m = ev[-1]["message"]
assert m["verify"]["mode"] == "search" and "draft" not in m["verify"] and m["verify"]["sources"][0]["read"], m["verify"]
sent = json.load(open(os.environ["FAKE_PROMPT_LOG"], encoding="utf-8"))
last = sent[-1]["content"]
assert sent[-1]["role"] == "user" and last.startswith("latest illustrious xl version\n\n[Web search results for this message"), last[:200]
assert "[1] Tavily on latest illustrious xl version" in last and "Tavily passage" in last
assert sent[0]["role"] == "system" and "web search assistant" in sent[0]["content"]
ev = ask(sc["id"], "and its recommended sampler?", verify=False)  # the plan sees the conversation before
assert ev[-1]["message"]["verify"]["queries"] and ev[-1]["done"]
assert verify._conversation([{"role": "system", "content": "s"}, {"role": "user", "content": "illustrious xl?"},
                             {"role": "assistant", "content": "v2.0"}, {"role": "user", "content": "its sampler?"}]) \
    == "User: illustrious xl?\nAssistant: v2.0"
# pictures of who or what the message is about: Tavily's, Wikipedia's (a bigger thumbnail), the pages'; a logo, an
# icon-sized one and the same picture twice left out; the model told they are shown, not to make up its own
ev = ask(sc["id"], "who is Henry Cavill", verify=False)
assert "Finding pictures…" in [e.get("step") for e in ev], ev
m = ev[-1]["message"]
pics = m["pictures"]
assert [p["src"].rsplit("/", 1)[-1] for p in pics] == ["cavill-1.png", "640px-same-b.png"], [p["src"] for p in pics]
assert pics[0]["url"].startswith("data:image/jpeg;base64,") and pics[0]["title"] == "Henry Cavill at a premiere"
assert max(pics[0]["w"], pics[0]["h"]) == 640 and pics[1]["page"].endswith("/wiki/Illustrious_XL") and "pictures" not in m["verify"]
last = json.load(open(os.environ["FAKE_PROMPT_LOG"], encoding="utf-8"))[-1]["content"]
assert "2 pictures found for this are shown to the user beside your answer" in last and "do not describe them" in last
assert c.get(B + "/one", params={"id": sc["id"]}).json()["chat"]["messages"][-1]["pictures"][0]["src"].endswith("cavill-1.png")
# Verify: pictures only when the message asks for them in so many words
ev = ask(vc, "who is Henry Cavill")
assert "pictures" not in ev[-1]["message"] and "Finding pictures…" not in [e.get("step") for e in ev]
ev = ask(vc, "cho mình xem ảnh Henry Cavill")
assert len(ev[-1]["message"]["pictures"]) == 2
assert not verify.ASKS_PICTURES.search("ảnh hưởng của CFG") and not verify.ASKS_PICTURES.search("image prompt for a cat")
shared.opts.pv_search_pictures = False
ev = ask(sc["id"], "who is Henry Cavill", verify=False)
assert "pictures" not in ev[-1]["message"]
shared.opts.pv_search_pictures = True
assert websearch._bigger_thumb("https://up.org/thumb/a/ab/X.jpg/60px-X.jpg") == "https://up.org/thumb/a/ab/X.jpg/640px-X.jpg"
assert websearch.og_image('<meta property="og:image" content="/a.jpg">', "https://s.org/p/q") == "https://s.org/a.jpg"
os.environ.pop("FAKE_PROMPT_LOG"); qwen.SERVER.stop()
shared.opts.pv_tavily_key = ""
c.post(B + "/delete", json={"id": sc["id"]})
shared.opts.pv_search_read_pages = False
ev = ask(vc, "best sampler for illustrious xl")
assert not ev[-1]["message"]["verify"]["sources"][0]["read"] and "Use Euler a, 28 steps &amp; CFG 5" not in ev[-1]["message"]["text"]
assert "Use Euler a, 28 steps & CFG 5" in ev[-1]["message"]["text"]  # the snippet only
shared.opts.pv_search_read_pages = True
# Again and edit can verify too; without Verify nothing is looked up
again = ask(vc, "", path="/regenerate")
assert again[-1]["message"]["verify"]["sources"]
n = len(fake_web.seen)
plain = ask(vc, "no verify", verify=False)
assert "verify" not in plain[-1]["message"] and len(fake_web.seen) == n
assert websearch.passages("a\nb sampler cfg\nc", ["sampler", "cfg"], size=3) == ["b sampler cfg"]
assert "x" not in websearch.page_text("<nav>x</nav><p>kept</p>") and websearch.page_text("<nav>x</nav><p>kept</p>") == "kept"
assert websearch.tag_name("(kaleidoscope:1.2)") == "kaleidoscope" and websearch.tag_name("best quality") == ""
assert verify.code_tags("x ```\na, b, c\n``` y ```\nnot tags\n```") == ["a", "b", "c"]
c.post(B + "/delete", json={"id": vc})
print("verify ok")

# rewind: back to one of your messages, everything after it gone, a new answer
rc = c.post(B + "/new").json()["chat"]["id"]
for w in ("one", "two", "three"):
    send(rc, w)
before = c.get(B + "/one", params={"id": rc}).json()["chat"]["messages"]
with c.stream("POST", B + "/regenerate", json={"id": rc, "rewind": before[2]["id"]}) as r:
    ev = [json.loads(x) for x in r.iter_lines() if x]
after = c.get(B + "/one", params={"id": rc}).json()["chat"]["messages"]
assert [m["text"] for m in after[:3]] == ["one", before[1]["text"], "two"] and len(after) == 4, [m["text"] for m in after]
assert "versions" not in after[3] and ev[-1]["done"]  # gone, not kept as another version
assert c.post(B + "/regenerate", json={"id": rc, "rewind": after[3]["id"]}).status_code == 400
print("rewind ok")

# compact: the older part summed up and out of the model's memory, the last messages kept
for w in ("four", "five"):
    send(rc, w)
def run(path, cid):
    with c.stream("POST", B + path, json={"id": cid}) as r:
        return [json.loads(x) for x in r.iter_lines() if x]
ev = run("/compact", rc)
done = ev[-1]["chat"]
assert [e["step"] for e in ev if "step" in e][0].startswith("Summing up 4 earlier") and ev[-1]["done"], ev
assert [m["text"] for m in done["messages"]][::2] == ["four", "five"] and len(done["archived"]) == 4 and done["summary"], done
assert done["summary"].startswith("messages=2") and "User:\none" in done["summary"]  # what the model was given to sum up
base_system = len(chat.system_of({"system": done["system"]}))
ev = send(rc, "six")
assert f"messages=6 " in ev[-1]["message"]["text"] and f"system={len(chat.system_of(done))}" in ev[-1]["message"]["text"]
assert len(chat.system_of(done)) > base_system
assert run("/compact", c.post(B + "/new").json()["chat"]["id"])[-1]["error"] == "Nothing to compact yet."
md = c.get(B + "/export", params={"id": rc, "fmt": "md"}).json()["text"]
assert "_4 earlier messages, compacted:_" in md and "## You\n\none" in md
saved = c.post(B + "/save", json={"id": rc}).json()["chat"]["saved_as"]
chat._chats.pop(rc)
back = c.post(B + "/open", json={"name": saved}).json()["chat"]
assert back["summary"] == done["summary"] and len(back["archived"]) == 4
c.post(B + "/unsave", json={"id": back["id"]})
print("compact ok")

# wrap up: what it came to, and a fresh conversation that starts from it alone
ev = run("/wrap", back["id"])
fresh = ev[-1]["chat"]
assert fresh["title"].endswith("(continued)") and fresh["summary"] and fresh["messages"][0]["text"].startswith("📝 **Wrap-up of")
ev = send(fresh["id"], "go on")
assert "messages=2 " in ev[-1]["message"]["text"] and f"system={len(chat.system_of(fresh))}" in ev[-1]["message"]["text"]
assert len(c.get(B + "/one", params={"id": back["id"]}).json()["chat"]["messages"]) > 2  # the old one stays as it was
print("wrap up ok")

# nearly full: compacted by itself before the answer, nothing left out unread
small = c.post(B + "/import", json={"data": {"title": "long", "messages": [
    {"role": r_, "text": ("A long scene on a balcony at dusk, wind and city lights. " * 12)} for r_ in ["user", "assistant"] * 6]}}).json()["chat"]
shared.opts.pv_vlm_context = 2048
x = c.get(B + "/one", params={"id": small["id"]}).json()["chat"]["context"]
assert x["used"] > x["room"] * 0.9, x
ev = send(small["id"], "and now?")
steps = [e["step"] for e in ev if "step" in e]
assert steps and steps[0].startswith("Summing up") and ev[-1]["done"], ev[:3]
after = c.get(B + "/one", params={"id": small["id"]}).json()["chat"]
assert after["archived"] and after["summary"] and ev[1]["left_out"] == 0 if "left_out" in ev[1] else True
shared.opts.pv_chat_autocompact = False
small2 = c.post(B + "/import", json={"data": {"title": "long", "messages": [
    {"role": r_, "text": ("A long scene. " * 50)} for r_ in ["user", "assistant"] * 6]}}).json()["chat"]
ev = send(small2["id"], "and now?")
assert not any("step" in e for e in ev) and ev[0]["left_out"] > 0  # off: the oldest are left out, as before
shared.opts.pv_chat_autocompact = True
shared.opts.pv_vlm_context = 8192
for x_ in (rc, fresh["id"], small["id"], small2["id"]):
    c.post(B + "/delete", json={"id": x_})
print("auto compact ok")

# keeping: save, export, open again, import
saved = c.post(B + "/save", json={"id": cid}).json()["chat"]["saved_as"]
assert saved and os.path.isfile(os.path.join(chat.chats_dir(), saved))
lst = c.get(B).json()
assert any(s["name"] == saved for s in lst["saved"]) and any(x["id"] == cid for x in lst["chats"])
md = c.get(B + "/export", params={"id": cid, "fmt": "md"}).json()
assert md["name"].endswith(".md") and "## You" in md["text"] and "## Assistant" in md["text"] and "[image: red.png]" in md["text"]
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

# a long conversation keeps within the context: with compacting off, the oldest messages are left out
shared.opts.pv_chat_autocompact = False
big = c.post(B + "/new").json()["chat"]["id"]
for i in range(6):
    ev = send(big, f"part {i} " + "word " * 900)
assert ev[0]["left_out"] > 0 and ev[-1]["done"], ev[0]
shared.opts.pv_chat_autocompact = True
print("context window ok: left out", ev[0]["left_out"])

# an older llama-server, before -fa took on/off: started with -fa alone
shared.opts.pv_vlm_flash = "On"
os.environ["FAKE_OLD_FA"] = "1"
qwen.SERVER.stop()
ev = send(big, "flash")
last = open(os.environ["FAKE_ARGS_LOG"]).read().splitlines()[-1].split()
assert ev[-1]["done"] and "-fa" in last and last[last.index("-fa") + 1] not in ("on", "off", "auto"), last
os.environ.pop("FAKE_OLD_FA"); shared.opts.pv_vlm_flash = "Auto"
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
    fake_gguf(os.path.join(vlm, name), 36, projector="qwen3vl_merger" if "mmproj" in name else "")
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

# other families: Gemma, Mistral, GLM with their projectors, and a model for words only
from lib_vault import families
first_model = c.get(M).json()["model"]
fam = os.path.join(vlm, "families")
os.makedirs(fam, exist_ok=True)
for name, arch, title, proj in (("gemma-3-12b-it-abliterated.Q4_K_M.gguf", "gemma3", "Gemma 3 12b It Abliterated", ""),
                                ("mmproj-gemma-3-12b-f16.gguf", "", "", "gemma3"),
                                ("Mistral-Small-3.2-24B-Instruct-abliterated-Q4_K_M.gguf", "llama", "Mistral Small 3.2 24B Instruct", ""),
                                ("mmproj-Mistral-Small-3.2-24B-f16.gguf", "", "", "pixtral"),
                                ("GLM-4.1V-9B-Thinking-Q4_K_M.gguf", "glm4", "GLM 4.1V 9B Thinking", ""),
                                ("mmproj-GLM-4.1V-9B-f16.gguf", "", "", "glm4v"),
                                ("Mistral-Nemo-12B-Instruct-Q5_K_M.gguf", "llama", "Mistral Nemo Instruct 2407", "")):
    fake_gguf(os.path.join(fam, name), 40, arch=arch or "qwen3vl", name=title, projector=proj)
got = c.get(M).json()
byname = {m["name"]: m for m in got["models"] + got["mmprojs"]}
assert byname["gemma-3-12b-it-abliterated.Q4_K_M.gguf"]["family_label"] == "Gemma" and byname["mmproj-gemma-3-12b-f16.gguf"]["family"] == "gemma"
assert byname["Mistral-Small-3.2-24B-Instruct-abliterated-Q4_K_M.gguf"]["family"] == "mistral"  # a "llama" inside, Mistral by name
assert byname["mmproj-Mistral-Small-3.2-24B-f16.gguf"]["family"] == "mistral" and byname["GLM-4.1V-9B-Thinking-Q4_K_M.gguf"]["family"] == "glm"
for model_name, proj in (("gemma-3-12b-it-abliterated.Q4_K_M.gguf", "mmproj-gemma-3-12b-f16.gguf"),
                         ("Mistral-Small-3.2-24B-Instruct-abliterated-Q4_K_M.gguf", "mmproj-Mistral-Small-3.2-24B-f16.gguf"),
                         ("GLM-4.1V-9B-Thinking-Q4_K_M.gguf", "mmproj-GLM-4.1V-9B-f16.gguf"),
                         ("Mistral-Nemo-12B-Instruct-Q5_K_M.gguf", "")):  # no projector of its own: words only, never another's
    chosen = c.post(M, json={"model": byname[model_name]["path"]}).json()
    assert os.path.basename(chosen["mmproj"]) == proj and chosen["vision"] == bool(proj), (model_name, chosen["mmproj"])
# Gemma: its recommended sampling, --jinja, its projector
g = c.post(M, json={"model": byname["gemma-3-12b-it-abliterated.Q4_K_M.gguf"]["path"]}).json()
assert g["family_label"] == "Gemma" and g["model_name"] == "Gemma 3 12b It Abliterated" and g["sampling"]["temperature"] == 1.0
gc_ = c.post(B + "/new").json()["chat"]["id"]
ev = send(gc_, "hello gemma")
assert "temp=1.0 top_k=64" in ev[-1]["message"]["text"], ev[-1]["message"]["text"]
argv = open(os.environ["FAKE_ARGS_LOG"]).read().splitlines()[-1]
assert "--jinja" in argv and "mmproj-gemma-3-12b-f16.gguf" in argv, argv
send(gc_, "this one", [{"kind": "image", "name": "red.png", "data": png}])
# Gemma's template wants turns that alternate: an answer removed (or one that failed) leaves two of yours in a row
msgs_now = c.get(B + "/one", params={"id": gc_}).json()["chat"]["messages"]
c.post(B + "/remove-message", json={"id": gc_, "message": msgs_now[-1]["id"]})
ev = send(gc_, "and again, after the answer was removed")
assert ev[-1].get("done") and "messages=4" in ev[-1]["message"]["text"], ev[-1]  # system + you, Gemma, you (two merged)
with c.stream("POST", B + "/assist", json={"id": gc_, "mode": "write", "text": ""}) as r:
    assert json.loads(list(r.iter_lines())[-1]).get("done")
print("alternating turns ok")
# a llama.cpp older than the model: said so, with what to do
g4 = os.path.join(fam, "gemma-4-26B-A4B-it-abliterated.Q4_K_M.gguf")
fake_gguf(g4, 30, arch="gemma4", name="Gemma 4 26B A4B It Abliterated")
c.post(M, json={"model": g4})
os.environ["FAKE_OLD_ARCH"] = "1"
ev = send(c.post(B + "/new").json()["chat"]["id"], "hello gemma 4")
os.environ.pop("FAKE_OLD_ARCH")
assert ev[-1]["error"].startswith("Gemma: This llama.cpp does not know the model's architecture (gemma4)"), ev[-1]
assert "latest llama.cpp" in ev[-1]["error"]
from lib_vault import llama
assert llama.explain("ggml_cuda: cudaMalloc failed: out of memory").startswith("Not enough VRAM")
assert llama.explain("clip_init: failed to load model 'mmproj-x.gguf'").startswith("The vision projector")
assert llama.explain("all good") == ""
c.post(M, json={"model": byname["gemma-3-12b-it-abliterated.Q4_K_M.gguf"]["path"]})
print("startup errors explained ok")
# words only: no projector given to the server, images refused, the earlier one told about in words
c.post(M, json={"model": byname["Mistral-Nemo-12B-Instruct-Q5_K_M.gguf"]["path"]})
ev = send(gc_, "and now?")
argv = open(os.environ["FAKE_ARGS_LOG"]).read().splitlines()[-1]
assert "--mmproj" not in argv and "images=0" in ev[-1]["message"]["text"] and "temp=0.15" in ev[-1]["message"]["text"], (argv, ev[-1])
r = c.post(B + "/send", json={"id": gc_, "text": "look", "files": [{"kind": "image", "name": "a.png", "data": png}]})
assert r.status_code == 400 and "reads no images" in r.json()["error"]
assert chat._content({"text": "hi", "files": [{"kind": "image", "name": "red.png", "url": "data:x"}]}, vision=False)[0]["text"].startswith("[an image, red.png")
# my temperature instead of the family's
shared.opts.pv_chat_sampling = "My temperature"
assert "temp=0.7 top_k=None" in send(gc_, "mine")[-1]["message"]["text"]
shared.opts.pv_chat_sampling = "Recommended for the model"
# back to vision with the chooser's "none": words only on purpose
c.post(M, json={"model": byname["gemma-3-12b-it-abliterated.Q4_K_M.gguf"]["path"]})
assert c.post(M, json={"mmproj": ""}).json()["vision"] is False
c.post(B + "/delete", json={"id": gc_})
assert families._tell("graphic novel") == "" and families._tell("Phi-4-mini") == "phi" and families._tell("llama3") == "llama"
c.post(M, json={"model": first_model})
print("families ok")

# every feature that asks the model, with each family: none fails, Gemma's and Mistral's strict templates are
# satisfied, nobody but Qwen is told it is Qwen, images go only to a model that sees
from PIL import Image as _Image
log = os.path.join(tempfile.mkdtemp(prefix="bodies-"), "bodies.jsonl")
os.environ["FAKE_BODY_LOG"] = log
def stream_events(path, body):
    with c.stream("POST", B + path, json=body) as r:
        assert r.status_code == 200, (path, r.read())
        return [json.loads(x) for x in r.iter_lines() if x]
def exercise(model_path):
    c.post(M, json={"model": model_path})
    qwen.SERVER.stop()
    open(log, "w").close()
    vision = qwen.has_vision()
    cid = c.post(B + "/new").json()["chat"]["id"]
    c.post(B + "/update", json={"id": cid, "system": chat.OLD_ASSISTANT})  # a conversation from before: "You are Qwen"
    evs = [send(cid, "hi there"), send(cid, "a castle at dusk"), stream_events("/regenerate", {"id": cid})]
    first = c.get(B + "/one", params={"id": cid}).json()["chat"]["messages"][0]
    evs.append(stream_events("/edit", {"id": cid, "message": first["id"], "text": "hello again"}))
    evs.append(send(cid, "three"))
    two = c.get(B + "/one", params={"id": cid}).json()["chat"]["messages"][2]
    evs.append(stream_events("/regenerate", {"id": cid, "rewind": two["id"]}))
    evs.append(stream_events("/assist", {"id": cid, "mode": "enhance", "text": "make it rain"}))
    evs.append(stream_events("/assist", {"id": cid, "mode": "write", "text": ""}))
    evs.append(stream_events("/send", {"id": cid, "text": "best sampler?", "files": [], "context": "", "verify": True}))
    c.post(B + "/banned", json={"text": "tapestry"})
    evs.append(send(cid, "a tapestry"))
    c.post(B + "/banned", json={"text": ""})
    shared.opts.pv_chat_think = True
    evs.append(send(cid, "think first"))
    shared.opts.pv_chat_think = False
    for w in ("four", "five"):
        evs.append(send(cid, w))
    evs.append(stream_events("/compact", {"id": cid}))
    evs.append(send(cid, "after compacting"))
    wrapped = stream_events("/wrap", {"id": cid})
    evs.append(wrapped)
    evs.append(send(wrapped[-1]["chat"]["id"], "after the wrap-up"))
    img = _Image.new("RGB", (64, 48), (200, 30, 30))
    notes = [qwen.read_image(img, "tags")[1], qwen.read_image(img, "description")[1], qwen.rewrite("1girl, red hair", "Tags → sentence")[1]]
    if vision:
        evs.append(send(cid, "this", [{"kind": "image", "name": "red.png", "data": png}]))
    errors = [e["error"] for ev in evs for e in ev if "error" in e]
    bodies = [json.loads(x) for x in open(log, encoding="utf-8")]
    return vision, errors, notes, bodies
report = {}
for name in ("gemma-3-12b-it-abliterated.Q4_K_M.gguf", "Mistral-Small-3.2-24B-Instruct-abliterated-Q4_K_M.gguf",
             "GLM-4.1V-9B-Thinking-Q4_K_M.gguf", "Mistral-Nemo-12B-Instruct-Q5_K_M.gguf"):
    vision, errors, notes, bodies = exercise(byname[name]["path"])
    label = families.label(families.of_model(byname[name]["path"]))
    assert not errors, (name, errors)
    told_qwen = [b["system"][:80] for b in bodies if re.search(r"\b(You are|I am) Qwen\b", b["system"] or "")]
    assert not told_qwen, (name, told_qwen)
    assert any(f"You are {label}" in (b["system"] or "") for b in bodies), (name, "the old Assistant text names the model in use")
    for b in bodies:  # one system prompt first, then turns that alternate, starting with the user
        rest = [r_ for r_ in b["roles"] if r_ != "system"]
        assert b["roles"].count("system") <= 1 and (not b["roles"] or b["roles"][0] in ("system", "user")), (name, b["roles"])
        assert all(r_ == ("user" if i % 2 == 0 else "assistant") for i, r_ in enumerate(rest)), (name, b["roles"])
    assert vision == any(b["images"] for b in bodies), (name, vision)  # images only to a model that sees
    if vision:
        assert all(not n.startswith(("Qwen", "The model:")) for n in notes) and notes[0].startswith(label), (name, notes)
    else:
        assert notes[0].startswith("The model in use reads no images") and not notes[2].startswith("The model in use"), (name, notes)
    report[label + ("" if vision else " (words only)")] = len(bodies)
os.environ.pop("FAKE_BODY_LOG")
qwen.SERVER.stop()
print("every feature with every family ok:", report)

# folders on another drive: several for Qwen, one for Prompt Vault's own models
other, third, own = (tempfile.mkdtemp(prefix=p) for p in ("drive-d-", "drive-e-", "pv-models-"))
fake_gguf(os.path.join(other, "Far-Qwen3-VL-8B.Q5_K_M.gguf"), 36)
fake_gguf(os.path.join(other, "Far-Qwen3-VL-8B.mmproj-f16.gguf"), 1, projector="qwen3vl_merger")
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
