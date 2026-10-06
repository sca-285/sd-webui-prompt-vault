"""Qwen Chat: conversations with the Qwen model of the Vault tab, on Muse's card and in the Vault tab alike.

Conversations live in the WebUI's memory: closing the WebUI (its terminal) ends them. One you want to keep
is saved, as JSON, in prompt_vault/chats/ (and kept saved as it goes on); any can be exported as Markdown
or JSON. Images (png, jpeg, webp) are shown to the model; text and Markdown files are read into the
conversation. What the model says is the model's: nothing here filters it.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import threading
import time
import uuid

from . import chat_presets, settings, store

DEFAULT_SYSTEM = chat_presets.BUILTIN[0]["text"]
TEXT_LIMIT = 60000      # characters of one text file
FILE_LIMIT = 8          # files on one message
IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp")

_lock = threading.RLock()
_chats = {}             # id -> conversation, the newest last
_stops = {}             # id -> threading.Event, set by Stop


def chats_dir():
    path = os.path.join(settings.data_dir(), "chats")
    os.makedirs(path, exist_ok=True)
    return path


def _system_default():
    return chat_presets.default()[1]


# ------------------------------------------------------------------ conversations


def _blank(system=None, preset=None):
    now = time.time()
    if preset and system is None and chat_presets.find(preset):
        system = chat_presets.find(preset)["text"]
    elif system is None:
        preset, system = chat_presets.default()
    return {"id": uuid.uuid4().hex[:12], "title": "New conversation", "created": now, "updated": now,
            "system": system, "preset": preset or "", "messages": [], "saved_as": ""}


def _view(c):
    """A conversation as the page sees it: the messages on the chosen path, each with which version it is
    ("version" of "versions"); the other versions stay here."""
    out = dict(c)
    out["messages"] = [_shown(m) for m in c["messages"]]
    out["context"] = _context(c)
    return out


def _shown(m):
    out = {k: v for k, v in m.items() if k != "others"}
    if m.get("others"):
        order = sorted([m.get("v", 0)] + [t[0].get("v", 0) for t in m["others"]])
        out["versions"], out["version"] = len(order), order.index(m.get("v", 0)) + 1
    return out


def _brief(c):
    return {"id": c["id"], "title": c["title"], "updated": c["updated"], "count": len(c["messages"]), "saved_as": c["saved_as"]}


def _get(cid):
    c = _chats.get(str(cid or ""))
    if c is None:
        raise store.VaultError("That conversation is gone (the WebUI was restarted?). Start a new one.")
    return c


def listing():
    """The conversations of this session, the newest first, and the saved ones on disk."""
    with _lock:
        live = [_brief(c) for c in sorted(_chats.values(), key=lambda c: -c["updated"])]
    saved = []
    for name in sorted(os.listdir(chats_dir()), reverse=True):
        if name.endswith(".json"):
            path = os.path.join(chats_dir(), name)
            try:
                with open(path, encoding="utf-8") as f:
                    head = json.load(f)
                saved.append({"name": name, "title": str(head.get("title") or name), "updated": head.get("updated") or os.path.getmtime(path),
                              "count": len(head.get("messages") or [])})
            except Exception:
                continue
    return {"chats": live, "saved": saved, "system_default": _system_default(), "presets": chat_presets.listing(),
            "banned": str(settings.opt("pv_chat_banned") or ""), "cliches": CLICHES}


def get(cid):
    with _lock:
        return _view(_get(cid))


def new(system=None, preset=None):
    with _lock:
        c = _blank(system, preset)
        _chats[c["id"]] = c
        return _view(c)


def delete(cid):
    with _lock:
        _chats.pop(str(cid), None)
        _stops.pop(str(cid), None)
    return listing()


def update(cid, title=None, system=None, preset=None):
    with _lock:
        c = _get(cid)
        if title is not None and str(title).strip():
            c["title"] = str(title).strip()[:120]
        if system is not None:
            c["system"] = str(system)[:8000]
            known = chat_presets.find(preset) if preset else None
            c["preset"] = preset if known and known["text"].strip() == c["system"].strip() else ""  # changed by hand: no preset
        _touch(c)
        return _view(c)


def remove_message(cid, mid):
    with _lock:
        c = _get(cid)
        c["messages"] = [m for m in c["messages"] if m["id"] != mid]
        _touch(c)
        return _view(c)


def _at(c, mid):
    for i, m in enumerate(c["messages"]):
        if m["id"] == mid:
            return i
    raise store.VaultError("That message is not in the conversation any more.")


def _branch(c, i):
    """The messages from i on put aside as a version of their own; (the versions put aside, the new one's number)."""
    tail = c["messages"][i:]
    del c["messages"][i:]
    others = tail[0].pop("others", []) if tail else []
    if tail:
        others.append(tail)
    return others, max([t[0].get("v", 0) for t in others] or [-1]) + 1


def _unbranch(c, others):
    """Nothing came of a new version: the newest one put aside is back."""
    if others:
        tail = others.pop()
        if others:
            tail[0]["others"] = others
        c["messages"].extend(tail)


def switch(cid, mid, step):
    """Another version of a message (step -1 or +1), and what followed it in that version."""
    with _lock:
        c = _get(cid)
        i = _at(c, mid)
        head = c["messages"][i]
        tails = head.pop("others", []) + [c["messages"][i:]]
        tails.sort(key=lambda t: t[0].get("v", 0))
        at = next(n for n, t in enumerate(tails) if t[0] is head)
        pick = tails.pop(max(0, min(len(tails), at + int(step))))
        if tails:
            pick[0]["others"] = tails
        c["messages"][i:] = pick
        _touch(c)
        return _view(c)


def _touch(c):
    c["updated"] = time.time()
    if c["saved_as"]:
        _write(c)


# ------------------------------------------------------------------ keeping and exporting


def _slug(text):
    s = re.sub(r"[^\w\- ]+", "", str(text or ""), flags=re.UNICODE).strip().replace(" ", "-")
    return (s or "conversation")[:48]


def _write(c):
    store.write_json(os.path.join(chats_dir(), c["saved_as"]), c)


def save(cid):
    """Kept on disk from now on, every new message with it."""
    with _lock:
        c = _get(cid)
        if not c["saved_as"]:
            c["saved_as"] = f"{time.strftime('%Y-%m-%d_%H%M', time.localtime(c['created']))}_{_slug(c['title'])}.json"
        _write(c)
        return _view(c)


def unsave(cid):
    """Not kept any more: the file goes, the conversation stays in this session."""
    with _lock:
        c = _get(cid)
        if c["saved_as"]:
            try:
                os.remove(os.path.join(chats_dir(), os.path.basename(c["saved_as"])))
            except FileNotFoundError:
                pass
        c["saved_as"] = ""
        return _view(c)


def _from_data(data, saved_as=""):
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise store.VaultError("That is not a Qwen Chat conversation.")
    c = _blank(str(data.get("system") or _system_default()))
    c["title"] = str(data.get("title") or "Conversation")[:120]
    c["preset"] = str(data.get("preset") or "") if str(data.get("system") or "").strip() else c["preset"]
    c["created"] = float(data.get("created") or c["created"])
    c["messages"] = _messages(data["messages"], c["created"])
    c["saved_as"] = saved_as
    return c


def unmangle(text):
    """UTF-8 that was read as Latin-1 (answers saved before 1.1.0's fix: â€œ for “, cÃ´ for cô), read again as UTF-8.
    Text that is not that comes back as it was."""
    text = str(text or "")
    if not re.search("[\u00c2-\u00f4][\u0080-\u00bf]", text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _messages(items, when):
    out = []
    for m in items if isinstance(items, list) else []:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            text = unmangle(m.get("text"))
            one = {"id": str(m.get("id") or uuid.uuid4().hex[:10]), "role": m["role"], "text": text,
                   "files": [f for f in (m.get("files") or []) if isinstance(f, dict)], "time": m.get("time") or when,
                   "tokens": int(m.get("tokens") or _tokens(text, m.get("files") or []))}
            for key in ("thinking", "stopped", "seconds", "context"):
                if m.get(key):
                    one[key] = m[key]
            one["v"] = int(m.get("v") or 0)
            others = [t for t in (_messages(t, when) for t in (m.get("others") or [])) if t]
            if others:
                one["others"] = others
            out.append(one)
    return out


def open_saved(name):
    """A saved conversation back in this session (still saved: what follows is kept too)."""
    name = os.path.basename(str(name or ""))
    path = os.path.join(chats_dir(), name)
    if not os.path.isfile(path):
        raise store.VaultError("That saved conversation is not there any more.")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    with _lock:
        for c in _chats.values():
            if c["saved_as"] == name:
                return _view(c)
        c = _from_data(data, saved_as=name)
        c["id"] = str(data.get("id") or c["id"]) if str(data.get("id") or "") not in _chats else c["id"]
        _chats[c["id"]] = c
        return _view(c)


def delete_saved(name):
    name = os.path.basename(str(name or ""))
    try:
        os.remove(os.path.join(chats_dir(), name))
    except FileNotFoundError:
        pass
    with _lock:
        for c in _chats.values():
            if c["saved_as"] == name:
                c["saved_as"] = ""
    return listing()


def import_data(data):
    with _lock:
        c = _from_data(data)
        _chats[c["id"]] = c
        return _view(c)


def export(cid, fmt="md"):
    """{"name", "text", "type"}: the conversation as a Markdown or JSON file."""
    with _lock:
        c = json.loads(json.dumps(_get(cid)))
    base = _slug(c["title"])
    if fmt == "json":
        return {"name": base + ".json", "text": json.dumps(c, ensure_ascii=False, indent=1), "type": "application/json"}
    out = [f"# {c['title']}", "", f"_{time.strftime('%Y-%m-%d %H:%M', time.localtime(c['created']))} · Qwen Chat (Prompt Vault)_", ""]
    if c["system"]:
        out += ["> **System:** " + c["system"].replace("\n", "\n> "), ""]
    for m in c["messages"]:
        out.append("## " + ("You" if m["role"] == "user" else "Qwen"))
        for f in m.get("files") or []:
            out.append(f"*[{f.get('kind')}: {f.get('name')}]*")
        out += ["", m["text"], ""]
    return {"name": base + ".md", "text": "\n".join(out), "type": "text/markdown"}


# ------------------------------------------------------------------ files on a message


def _image_file(name, data_url):
    from PIL import Image

    from . import qwen

    head, _, b64 = str(data_url).partition(",")
    if not head.startswith("data:image/"):
        raise store.VaultError(f"{name}: not an image")
    image = Image.open(io.BytesIO(base64.b64decode(b64)))
    image.load()
    url, size = qwen._encode(image, int(settings.opt("pv_vlm_max_image_side")))
    return {"kind": "image", "name": name, "url": url, "w": size[0], "h": size[1]}


def _text_file(name, content):
    content = str(content or "")
    cut = len(content) > TEXT_LIMIT
    return {"kind": "text", "name": name, "text": content[:TEXT_LIMIT], "cut": cut, "chars": len(content)}


def read_files(files):
    out = []
    for f in (files or [])[:FILE_LIMIT]:
        if not isinstance(f, dict):
            continue
        name = os.path.basename(str(f.get("name") or "file"))[:120]
        if f.get("kind") == "image":
            out.append(_image_file(name, f.get("data")))
        else:
            out.append(_text_file(name, f.get("data")))
    return out


def _tokens(text, files):
    """A rough count, to keep a conversation within the model's context: English runs about 3.2 characters a token,
    Vietnamese, Chinese and the like fewer (their accented and non-Latin letters count double)."""
    text = text or ""
    wide = sum(1 for ch in text if ord(ch) > 127)
    n = (len(text) - wide) / 3.2 + wide / 1.6
    for f in files or []:
        n += (f.get("w", 1024) * f.get("h", 1024) / 1024) if f.get("kind") == "image" else len(f.get("text") or "") / 3.2
    return int(n) + 8


# ------------------------------------------------------------------ talking


def _content(m):
    """A message as the model reads it: images as images, files as text, then the words."""
    parts = []
    for f in m.get("files") or []:
        if f.get("kind") == "image" and f.get("url"):
            parts.append({"type": "image_url", "image_url": {"url": f["url"]}})
        elif f.get("kind") == "text":
            note = " (cut: the file is longer)" if f.get("cut") else ""
            parts.append({"type": "text", "text": f"File {f.get('name')}{note}:\n```\n{f.get('text', '')}\n```"})
    words = m["text"]
    if m.get("context"):
        words = f"{m['context']}\n\n{words}" if words else m["context"]
    if not parts:
        return words
    if words:
        parts.append({"type": "text", "text": words})
    return parts


def _reserve():
    """Tokens kept free for the answer: the longest answer, three times that when the model thinks first."""
    return int(settings.opt("pv_chat_max_tokens")) * (3 if settings.opt("pv_chat_think") else 1)


def _room(c):
    """Tokens the messages may take: the context, less the answer's share, the system prompt and a margin."""
    return int(settings.opt("pv_vlm_context")) - _reserve() - _tokens(c["system"], []) - 64


def _context(c):
    """How full the context is: {"used", "room", "size", "reserve"}, in tokens (estimated)."""
    used = sum(m.get("tokens") or _tokens(m["text"], m.get("files")) for m in c["messages"])
    return {"used": used, "room": max(0, _room(c)), "size": int(settings.opt("pv_vlm_context")), "reserve": _reserve()}


def _window(c, max_tokens=None):
    """The messages that fit in the context, the newest kept; how many older ones were left out."""
    budget = _room(c)
    kept, used = [], 0
    for m in reversed(c["messages"]):
        need = m.get("tokens") or _tokens(m["text"], m.get("files"))
        if kept and used + need > budget:
            break
        kept.append(m)
        used += need
    kept.reverse()
    while kept and kept[0]["role"] == "assistant":  # a conversation the model reads starts with the user
        kept.pop(0)
    return kept, len(c["messages"]) - len(kept)


# ------------------------------------------------------------------ banned words

# a start for the Banned words box: the words and phrases AI writing leans on
CLICHES = ("tapestry, testament, delve, intricate, palpable, ozone, ministrations, unspoken, kaleidoscope, symphony, "
           "a mix of, barely above a whisper, shivers down her spine, sent shivers, eyes sparkled with, maybe, just maybe, "
           "can't help but, a dance of, the air was thick with, mischievous glint, padded across the room")


def banned():
    """The banned words and phrases from Settings, each once."""
    out, seen = [], set()
    for part in re.split(r"[\n,;]+", str(settings.opt("pv_chat_banned") or "")):
        word = part.strip()
        if word and word.lower() not in seen:
            seen.add(word.lower())
            out.append(word)
    return out[:300]


def set_banned(text):
    from . import qwen

    qwen._set_opt("pv_chat_banned", str(text or "")[:20000])
    return {"banned": str(settings.opt("pv_chat_banned") or ""), "words": banned()}


_token_ids = {}  # (model, text) -> its tokens, from llama-server's /tokenize


def _logit_bias(url, model, words):
    """[[token id, false]] for each banned single word that is one token on its own (bare, after a space, in any of
    its capitals): llama-server then never writes it. A word of several tokens is not blocked this way, since blocking
    its pieces would block them in every other word too; it is only asked to be avoided."""
    import requests

    ids = set()
    for word in words:
        if re.search(r"\s", word):
            continue
        for v in {word, word.lower(), word.capitalize(), word.upper()}:
            for text in (v, " " + v):
                key = (model, text)
                if key not in _token_ids:
                    try:
                        got = requests.post(f"{url}/tokenize", json={"content": text, "add_special": False}, timeout=5).json()
                        _token_ids[key] = [t for t in got.get("tokens") or [] if isinstance(t, int)]
                    except Exception:
                        return [[i, False] for i in sorted(ids)]  # an old server without /tokenize: asked only
                if len(_token_ids[key]) == 1:
                    ids.add(_token_ids[key][0])
    return [[i, False] for i in sorted(ids)]


def _ask_to_avoid(messages, words):
    """The banned words in the system prompt too: what blocking cannot catch (phrases, other forms) is asked."""
    note = "Never use these words or phrases, in any form or language: " + "; ".join(words) + "."
    out = [dict(m) for m in messages]
    if out and out[0]["role"] == "system":
        out[0]["content"] = f"{out[0]['content']}\n\n{note}"
    else:
        out.insert(0, {"role": "system", "content": note})
    return out


def banned_in(text, words=None):
    """The banned words and phrases that are in a text anyway."""
    low = str(text or "").lower()
    return [w for w in (banned() if words is None else words)
            if re.search(r"(?<!\w)" + re.escape(w.lower()) + r"(?!\w)", low)]


def _stream(messages, max_tokens, think, stop, text, thought, temperature=None):
    """The model's answer as it comes: {"delta"} and {"thinking"} events; the pieces are kept in text and thought."""
    from . import qwen

    split = _ThinkSplit()
    with qwen._SdAside():
        qwen.SERVER.restart_if_changed(qwen._placement())
        url = qwen.SERVER.ensure()
    import requests

    words = banned()
    bias = _logit_bias(url, qwen.SERVER.model, words) if words else []
    if words:
        messages = _ask_to_avoid(messages, words)
    body = {"messages": messages, "max_tokens": max_tokens * (3 if think else 1),
            "temperature": float(settings.opt("pv_chat_temperature") if temperature is None else temperature), "stream": True,
            "chat_template_kwargs": {"enable_thinking": think}}
    if bias:
        body["logit_bias"] = bias
    with requests.post(f"{url}/v1/chat/completions", json=body, stream=True, timeout=(10, 600)) as res:
        if res.status_code != 200:
            raise RuntimeError(f"the Qwen server answered {res.status_code}: {res.text[:300]}")
        res.encoding = "utf-8"  # llama-server sends UTF-8 without saying so; requests would read it as Latin-1
        for line in res.iter_lines(decode_unicode=True):
            if stop.is_set():
                break
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                d = json.loads(data)["choices"][0].get("delta", {})
            except Exception:
                continue
            qwen.SERVER.touch()
            if d.get("reasoning_content"):  # a thinking model's reasoning, given apart by llama-server
                thought.append(d["reasoning_content"])
                yield {"thinking": d["reasoning_content"]}
            for kind, piece in split.feed(d.get("content") or ""):  # or inside the answer, between <think> tags
                into = thought if kind == "thinking" else text
                if not "".join(into).strip():  # the blank lines around an empty <think></think>: not shown
                    piece = piece.lstrip()
                if piece:
                    into.append(piece)
                    yield {kind: piece}


def send(cid, words, files=None, context="", regenerate=False, edit=None, again=None):
    """A generator of events for the page: {"start"}, {"delta": text}..., then {"done", "message"} or {"error"}.

    regenerate: a new answer to the last message (again: to the one answered by that answer); edit: that message of
    yours, with new words, answered anew. Either way the earlier version is kept, with what followed it."""
    from . import qwen

    branch = None  # (the versions put aside, the new version's number) for the answer to come
    with _lock:
        c = _get(cid)
        if regenerate:
            i = _at(c, again) if again else len(c["messages"])
            if not again and c["messages"] and c["messages"][-1]["role"] == "assistant":
                i -= 1
            if c["messages"][i:i + 1] and c["messages"][i]["role"] == "assistant":
                branch = _branch(c, i)
            if not c["messages"] or c["messages"][-1]["role"] != "user":
                _unbranch(c, branch[0] if branch else [])
                raise store.VaultError("Nothing to answer again.")
        elif edit:
            i = _at(c, edit)
            old = c["messages"][i]
            if old["role"] != "user":
                raise store.VaultError("Only your own messages can be edited.")
            words = str(words or "").strip()
            got = read_files(files) if files else old.get("files") or []
            if not words and not got:
                raise store.VaultError("Write something, or add a file.")
            others, v = _branch(c, i)
            msg = {"id": uuid.uuid4().hex[:10], "role": "user", "text": words, "files": got, "time": time.time(),
                   "context": old.get("context", ""), "v": v, "others": others}
            msg["tokens"] = _tokens(words + msg["context"], got)
            c["messages"].append(msg)
            _touch(c)
        else:
            words = str(words or "").strip()
            got = read_files(files)
            if not words and not got:
                raise store.VaultError("Write something, or add a file.")
            msg = {"id": uuid.uuid4().hex[:10], "role": "user", "text": words, "files": got, "time": time.time(),
                   "context": str(context or "")[:6000]}
            msg["tokens"] = _tokens(words + msg["context"], got)
            c["messages"].append(msg)
            if c["title"] == "New conversation":
                first = words or (got[0]["name"] if got else "")
                c["title"] = (first[:60] + ("…" if len(first) > 60 else "")) or "Conversation"
            _touch(c)
        stop = _stops[c["id"]] = threading.Event()
        max_tokens = int(settings.opt("pv_chat_max_tokens"))
        window, left_out = _window(c)
        messages = ([{"role": "system", "content": c["system"]}] if c["system"].strip() else []) + \
                   [{"role": m["role"], "content": _content(m)} for m in window]

    def events():
        yield {"start": True, "left_out": left_out}
        text, thought, started = [], [], time.time()
        try:
            yield from _stream(messages, max_tokens, bool(settings.opt("pv_chat_think")), stop, text, thought)
        except Exception as exc:
            if not text:
                if branch:
                    with _lock:
                        if cid in _chats:
                            _unbranch(_chats[cid], branch[0])
                yield {"error": f"Qwen: {exc}"}
                return
        answer = "".join(text).strip()
        if "</think>" in answer:  # a template that opens <think> itself: only the closing tag came back
            before, _, answer = answer.rpartition("</think>")
            thought.insert(0, before)
            answer = answer.strip()
        reply = {"id": uuid.uuid4().hex[:10], "role": "assistant", "text": answer, "files": [], "time": time.time(),
                 "stopped": stop.is_set(), "seconds": round(time.time() - started, 1)}
        if "".join(thought).strip():
            reply["thinking"] = "".join(thought).strip()
        reply["tokens"] = _tokens(answer, [])
        hits = banned_in(answer)
        if hits:
            reply["banned_hits"] = hits
        with _lock:
            live = _chats.get(cid)
            if live is not None and answer:
                if branch:
                    reply["others"], reply["v"] = branch
                live["messages"].append(reply)
                _touch(live)
            elif live is not None and branch:
                _unbranch(live, branch[0])
        yield {"done": True, "message": _shown(reply), "status": qwen.MEMORY.get("note", "")}

    return events()


class _ThinkSplit:
    """Streamed text cut into the reasoning (inside <think>...</think>) and the answer, however the pieces fall."""

    def __init__(self):
        self.inside, self.buf = False, ""

    def feed(self, piece):
        out = []
        self.buf += piece
        while self.buf:
            tag = "</think>" if self.inside else "<think>"
            at = self.buf.find(tag)
            if at < 0:  # keep what could be the start of a tag for the next piece
                keep = next((n for n in range(len(tag) - 1, 0, -1) if self.buf.endswith(tag[:n])), 0)
                ready, self.buf = self.buf[:len(self.buf) - keep], self.buf[len(self.buf) - keep:]
                if ready:
                    out.append(("thinking" if self.inside else "delta", ready))
                break
            if at:
                out.append(("thinking" if self.inside else "delta", self.buf[:at]))
            self.buf = self.buf[at + len(tag):]
            self.inside = not self.inside
        return out


# ------------------------------------------------------------------ help with your own message

ENHANCE_SYSTEM = (
    "You improve a message the user is about to send to an AI assistant inside an image-prompt tool (Stable Diffusion "
    "WebUI). Rewrite their draft so the assistant understands it better and answers it better: clear, specific and "
    "complete, in the same language and the same voice as the draft. Keep everything they ask for and every detail "
    "they give; add only what sharpens the request (for an image or a prompt: subject, look, setting, lighting, mood, "
    "style, framing; for a question: what they want back and in what form). Do not answer it. No preamble, no quotes, "
    "no notes: write only the improved message."
)
WRITE_SYSTEM = (
    "You write the user's next message in their conversation with an AI assistant inside an image-prompt tool "
    "(Stable Diffusion WebUI). Write it as the user, in the first person, in the language the user writes in "
    "(English when there is nothing to go by) and the way they write. One message that moves their work forward: a "
    "variation, a detail, a fix, the next step, or a fresh idea when the conversation is new. When the user gives a "
    "hint, follow it. Do not answer as the assistant. No preamble, no quotes, no notes: write only the message."
)
ASSIST_MODES = {"enhance": (ENHANCE_SYSTEM, 0.5), "write": (WRITE_SYSTEM, 0.9)}


def _transcript(c, limit=12, chars=1500):
    lines = []
    for m in c["messages"][-limit:]:
        words = m["text"] if len(m["text"]) <= chars else m["text"][:chars] + " […]"
        names = ", ".join(f.get("name", "") for f in m.get("files") or [])
        lines.append(("User" if m["role"] == "user" else "Assistant") + (f" [files: {names}]" if names else "") + ": " + words)
    return "\n\n".join(lines)


def tidy_draft(text):
    """What the model wrote, as a message: no "Improved message:" before it, no quotes or code fence around it."""
    text = str(text or "").strip()
    text = re.sub(r"^(here(?: is|'s)[^\n:]*:|improved (?:message|draft|version)\s*:|message\s*:|user\s*:)\s*", "", text, flags=re.I)
    if text.startswith("```") and text.endswith("```") and text.count("```") == 2:
        text = text[3:-3].split("\n", 1)[-1] if "\n" in text[3:-3] else text[3:-3]
    for a, b in (('"', '"'), ("“", "”"), ("«", "»")):
        inner = text[1:-1]
        if len(text) > 1 and text.startswith(a) and text.endswith(b) and a not in inner and b not in inner:
            text = inner
    return text.strip()


def assist(cid, mode, draft="", context=""):
    """Help with the message you are writing, not sent: "enhance" rewrites your draft, "write" writes one for you (your
    draft, if any, as a hint). Events: {"start"}, {"delta"}..., then {"done", "text"} or {"error"}."""
    if mode not in ASSIST_MODES:
        raise store.VaultError("Enhance or write?")
    draft = str(draft or "").strip()
    if mode == "enhance" and not draft:
        raise store.VaultError("Write a draft first: Enhance makes it better.")
    system, temperature = ASSIST_MODES[mode]
    with _lock:
        c = _chats.get(str(cid or ""))
        so_far = _transcript(c) if c else ""
        stop = _stops[str(cid or "assist")] = threading.Event()
    parts = []
    if so_far:
        parts.append("The conversation so far:\n\n" + so_far)
    if context:
        parts.append("The prompt the user is working on:\n" + str(context)[:4000])
    if mode == "enhance":
        parts.append("The user's draft, to improve:\n" + draft)
    else:
        parts.append(("The user's hint for the message: " + draft) if draft else "Write the user's next message.")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": "\n\n".join(parts)}]

    def events():
        yield {"start": True}
        text, thought = [], []
        try:
            for ev in _stream(messages, 700, False, stop, text, thought, temperature):
                if "delta" in ev:
                    yield ev
        except Exception as exc:
            if not text:
                yield {"error": f"Qwen: {exc}"}
                return
        written = tidy_draft("".join(text))
        yield {"done": True, "text": written, "stopped": stop.is_set(), "banned_hits": banned_in(written)}

    return events()


def stop(cid):
    ev = _stops.get(str(cid))
    if ev:
        ev.set()
    return {"stopped": bool(ev)}
