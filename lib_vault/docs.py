"""Long files in the chat: a PDF of hundreds of pages, a novel in Markdown. The whole text is kept on the message; what
the model is given each turn is what fits in its context:
- all of it, when it fits;
- else the pages asked for by number ("page 57", "pages 10-14", "trang 12"), then the pages most about the question
  (its rarer words count more), in the order of the document, each with its page number;
- for a question about the whole of it (sum it up, the main points, an outline…), the document is first read part
  by part and each part summed up (once: the summaries stay with the file), and the model answers from those and
  the pages on the question."""

from __future__ import annotations

import math
import re

from . import websearch

CHUNK = 1800        # characters of one part of a file that is not split in pages
PAGE = re.compile(r"^--- page (\d+) ---\n", re.M)
WHOLE = re.compile(
    r"\b(summar\w*|sum (it|this|them) up|overview|outline|main (points|ideas)|key (points|takeaways)|tl;?dr|"
    r"whole|entire|all (the )?(pages|chapters)|table of contents|chapters?|gist)\b|"
    r"tóm tắt|tổng quan|tổng hợp|ý chính|nội dung chính|toàn bộ|cả (file|tài liệu|cuốn|quyển|sách)|mục lục|dàn ý|các chương",
    re.I)
ASKED = re.compile(r"\b(?:pages?|pp?\.|trang)\s*(\d{1,4})(?:\s*(?:-|–|to|đến|tới)\s*(\d{1,4}))?", re.I)
DIGEST_SYSTEM = (
    "You read one part of a long document and write notes on it for someone who will answer questions about the "
    "whole document without seeing it. In the document's language or English, at most 180 words: what this part "
    "covers, its key facts, names, numbers and definitions, and any conclusion. Plain sentences, no preamble."
)


def parts(f):
    """[(label, text)]: a PDF's pages ("page 12"), else parts of about CHUNK characters ("part 3")."""
    text = f.get("text") or ""
    marks = list(PAGE.finditer(text))
    if marks:
        out = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            out.append((f"page {m.group(1)}", text[m.end():end].strip()))
        return out
    out, chunk, n = [], "", 0
    for para in re.split(r"(\n\s*\n)", text):
        if len(chunk) + len(para) > CHUNK and chunk.strip():
            n += 1
            out.append((f"part {n}", chunk.strip()))
            chunk = ""
        while len(para) > CHUNK * 2:  # one huge paragraph: cut it
            n += 1
            out.append((f"part {n}", para[:CHUNK].strip()))
            para = para[CHUNK:]
        chunk += para
    if chunk.strip():
        out.append((f"part {n + 1}", chunk.strip()))
    return out


def wants_whole(question):
    return bool(WHOLE.search(question or ""))


def asked_pages(question):
    """The page numbers the question names: "page 7", "pages 10-14", "trang 3 đến 5"."""
    out = []
    for a, b in ASKED.findall(question or ""):
        lo, hi = int(a), int(b or a)
        if hi < lo:
            lo, hi = hi, lo
        out += [n for n in range(lo, min(hi, lo + 40) + 1) if n not in out]
    return out


def _score(items, question):
    """Each part's score for the question: the question's words in it, rarer words counting more."""
    words = websearch.terms(question)
    low = [t.lower() for _, t in items]
    if not words:
        return [0.0] * len(items)
    idf = {w: math.log(1 + len(low) / (1 + sum(w in t for t in low))) for w in words}
    return [sum(idf[w] * min(4, t.count(w)) for w in words) / (1 + len(t) / 4000) for t in low]


def view(f, question, chars):
    """What the model reads of a text file, in at most chars characters."""
    text = f.get("text") or ""
    if len(text) <= chars:
        return text
    items = parts(f)
    total = f.get("pages") or len(items)
    kind = "pages" if items and items[0][0].startswith("page") else "parts"
    digest = f.get("digest") or []
    head = (f"[{total} {kind}, too long to read at once. Shown: "
            + ("notes on every part of it, then " if digest else "")
            + f"the {kind} most about the question, with their numbers; the others are left out. Ask for {kind} by "
            "number to read them.]\n")
    out, used = [head], len(head)
    if digest:
        notes = "Notes on the whole document:\n" + "\n".join(f"- {d['label']}: {d['text']}" for d in digest) + "\n"
        notes = notes[:int(chars * 0.6)]
        out.append(notes)
        used += len(notes)
    number = {label: i for i, (label, _) in enumerate(items)}
    chosen = [number[f"page {n}"] for n in asked_pages(question) if f"page {n}" in number]
    scores = _score(items, question)
    ranked = sorted(range(len(items)), key=lambda i: -scores[i]) if any(scores) else []
    if not ranked and not chosen and not digest:  # nothing to go by: the start, where a document says what it is
        ranked = list(range(len(items)))
    picked, room = [], chars - used
    for i in chosen + ranked:
        if i in picked:
            continue
        piece = len(items[i][1]) + len(items[i][0]) + 12
        if piece > room:
            if i in chosen and room > 400:  # a page asked for is shown, if only its start
                picked.append(i)
                room = 0
            continue
        picked.append(i)
        room -= piece
        if room < 300:
            break
    for i in sorted(picked):
        label, body = items[i]
        out.append(f"--- {label} ---\n{body[:max(0, chars - used - 20)]}\n")
        used += len(out[-1])
        if used >= chars:
            break
    return "".join(out)[:chars]


def views(messages, question, chars):
    """{(message id, file index): what the model reads of it} for the long text files in these messages; the room
    shared out by their lengths, the files of the last message first."""
    files = [(m["id"], i, f) for m in messages for i, f in enumerate(m.get("files") or []) if f.get("kind") == "text"]
    total = sum(len(f.get("text") or "") for _, _, f in files)
    if total <= chars:
        return {}
    out = {}
    for mid, i, f in files:
        share = max(2000, int(chars * len(f.get("text") or "") / total))
        out[(mid, i)] = view(f, question, share)
    return out


def needs_digest(messages, question, chars):
    """The long text files the question is about as a whole and that have no notes yet."""
    if not wants_whole(question):
        return []
    files = [f for m in messages for f in m.get("files") or [] if f.get("kind") == "text"]
    return [f for f in files if len(f.get("text") or "") > chars and not f.get("digest")]


def digest(f, chars, complete, stop):
    """Notes on every part of a long file, read in groups as big as the context allows; steps for the page."""
    items = parts(f)
    groups, group, size = [], [], 0
    for label, body in items:
        if group and size + len(body) > chars:
            groups.append(group)
            group, size = [], 0
        group.append((label, body))
        size += len(body)
    if group:
        groups.append(group)
    notes = []
    for n, group in enumerate(groups):
        if stop.is_set():
            return
        first, last = group[0][0], group[-1][0]
        label = first if first == last else f"{first}–{last.split()[-1]}"
        yield {"step": f"Reading {f.get('name')}: {label} ({n + 1} of {len(groups)})…"}
        text = "\n\n".join(f"--- {l} ---\n{b}" for l, b in group)[:chars]
        notes.append({"label": label, "text": complete([{"role": "system", "content": DIGEST_SYSTEM},
                                                        {"role": "user", "content": text}], 320).strip()})
    f["digest"] = notes
