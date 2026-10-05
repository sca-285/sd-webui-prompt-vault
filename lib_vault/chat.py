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

from . import settings, store

DEFAULT_SYSTEM = (
    "You are Qwen, a creative assistant inside Stable Diffusion WebUI. You help write image prompts and talk about "
    "ideas, images, stories and anything else the user brings. Answer in the user's language. When you give an image "
    "prompt, put it alone in a ``` code block, as comma-separated Danbooru-style tags unless the user asks for prose."
)
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
    return str(settings.opt("pv_chat_system") or "").strip() or DEFAULT_SYSTEM


# ------------------------------------------------------------------ conversations


def _blank(system=None):
    now = time.time()
    return {"id": uuid.uuid4().hex[:12], "title": "New conversation", "created": now, "updated": now,
            "system": (system if system is not None else _system_default()), "messages": [], "saved_as": ""}


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
    return {"chats": live, "saved": saved, "system_default": _system_default()}


def get(cid):
    with _lock:
        return dict(_get(cid))


def new(system=None):
    with _lock:
        c = _blank(system)
        _chats[c["id"]] = c
        return dict(c)


def delete(cid):
    with _lock:
        _chats.pop(str(cid), None)
        _stops.pop(str(cid), None)
    return listing()


def update(cid, title=None, system=None):
    with _lock:
        c = _get(cid)
        if title is not None and str(title).strip():
            c["title"] = str(title).strip()[:120]
        if system is not None:
            c["system"] = str(system)[:8000]
        _touch(c)
        return dict(c)


def remove_message(cid, mid):
    with _lock:
        c = _get(cid)
        c["messages"] = [m for m in c["messages"] if m["id"] != mid]
        _touch(c)
        return dict(c)


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
        return dict(c)


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
        return dict(c)


def _from_data(data, saved_as=""):
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise store.VaultError("That is not a Qwen Chat conversation.")
    c = _blank(str(data.get("system") or _system_default()))
    c["title"] = str(data.get("title") or "Conversation")[:120]
    c["created"] = float(data.get("created") or c["created"])
    for m in data["messages"]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
            c["messages"].append({"id": str(m.get("id") or uuid.uuid4().hex[:10]), "role": m["role"], "text": str(m.get("text") or ""),
                                  "files": [f for f in (m.get("files") or []) if isinstance(f, dict)], "time": m.get("time") or c["created"],
                                  "tokens": int(m.get("tokens") or _tokens(str(m.get("text") or ""), m.get("files") or []))})
    c["saved_as"] = saved_as
    return c


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
                return dict(c)
        c = _from_data(data, saved_as=name)
        c["id"] = str(data.get("id") or c["id"]) if str(data.get("id") or "") not in _chats else c["id"]
        _chats[c["id"]] = c
        return dict(c)


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
        return dict(c)


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
    """A rough count, to keep a conversation within the model's context."""
    n = len(text or "") / 3.2
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


def _window(c, max_tokens):
    """The messages that fit in the context, the newest kept; how many older ones were left out."""
    budget = int(settings.opt("pv_vlm_context")) - max_tokens - _tokens(c["system"], []) - 64
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


def send(cid, words, files=None, context="", regenerate=False):
    """A generator of events for the page: {"start"}, {"delta": text}..., then {"done", "message"} or {"error"}."""
    from . import qwen

    with _lock:
        c = _get(cid)
        if regenerate:
            while c["messages"] and c["messages"][-1]["role"] == "assistant":
                c["messages"].pop()
            if not c["messages"]:
                raise store.VaultError("Nothing to answer again.")
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
        window, left_out = _window(c, max_tokens)
        messages = ([{"role": "system", "content": c["system"]}] if c["system"].strip() else []) + \
                   [{"role": m["role"], "content": _content(m)} for m in window]

    def events():
        yield {"start": True, "left_out": left_out}
        text, thought, started = [], [], time.time()
        split = _ThinkSplit()
        try:
            with qwen._SdAside():
                qwen.SERVER.restart_if_changed(qwen._placement())
                url = qwen.SERVER.ensure()
            import requests

            think = bool(settings.opt("pv_chat_think"))
            body = {"messages": messages, "max_tokens": max_tokens * (3 if think else 1),
                    "temperature": float(settings.opt("pv_chat_temperature")), "stream": True,
                    "chat_template_kwargs": {"enable_thinking": think}}
            with requests.post(f"{url}/v1/chat/completions", json=body, stream=True, timeout=(10, 600)) as res:
                if res.status_code != 200:
                    raise RuntimeError(f"the Qwen server answered {res.status_code}: {res.text[:300]}")
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
        except Exception as exc:
            if not text:
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
        with _lock:
            live = _chats.get(cid)
            if live is not None and answer:
                live["messages"].append(reply)
                _touch(live)
        yield {"done": True, "message": reply, "status": qwen.MEMORY.get("note", "")}

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


def stop(cid):
    ev = _stops.get(str(cid))
    if ev:
        ev.set()
    return {"stopped": bool(ev)}
