"""Prompts as lists of pieces: split, compare, join.

A piece is what sits between two top-level commas. Commas inside brackets
("(red hair, blue eyes:1.2)") or inside <lora:...> do not split.
"""

from __future__ import annotations

import re

_OPEN = "([{<"
_CLOSE = ")]}>"
_WEIGHT = re.compile(r"^\((.*):\s*[-+]?\d*\.?\d+\s*\)$", re.DOTALL)


def split(prompt):
    """'a, (b, c:1.2), <lora:x:1>' -> ['a', '(b, c:1.2)', '<lora:x:1>']"""
    pieces, depth, current, escaped = [], 0, [], False
    for ch in prompt or "":
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\":
            current.append(ch)
            escaped = True
            continue
        if ch in _OPEN:
            depth += 1
        elif ch in _CLOSE and depth:
            depth -= 1
        if ch in ",\n" and depth == 0:
            pieces.append("".join(current))
            current = []
            continue
        current.append(ch)
    pieces.append("".join(current))
    return [p.strip() for p in pieces if p.strip()]


def key(piece):
    """What a piece is, for comparing: weights, emphasis brackets, escapes, case and
    underscores stripped. '((Red_Hair))' and '(red hair:1.2)' are both 'red hair'."""
    s = (piece or "").strip()
    for _ in range(4):
        m = _WEIGHT.match(s)
        if m:
            s = m.group(1).strip()
            continue
        if len(s) > 2 and s[0] in "([" and s[-1] == {"(": ")", "[": "]"}[s[0]] and not s.endswith("\\)"):
            s = s[1:-1].strip()
            continue
        break
    s = s.replace("\\(", "(").replace("\\)", ")")
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip().lower()


def join(pieces):
    return ", ".join(p for p in pieces if p)


def is_special(piece):
    """LoRA / embedding / BREAK / wildcard pieces: kept as they are, never sent to a model."""
    p = piece.strip()
    return p.startswith("<") or p == "BREAK" or p.startswith("__") or bool(_WEIGHT.match(p))


def dedupe(pieces):
    seen, out = set(), []
    for p in pieces:
        k = key(p)
        if k and k not in seen:
            seen.add(k)
            out.append(p)
    return out


def merge(current, addition, mode="Append"):
    """Put addition into current. Append skips pieces already there."""
    addition = (addition or "").strip()
    if not addition:
        return current or ""
    if mode == "Replace" or not (current or "").strip():
        return addition
    if "," not in addition and len(addition.split()) > 8:
        # a sentence: never split it into pieces
        return f"{current.strip().rstrip(',')}, {addition}"
    have = {key(p) for p in split(current)}
    new = [p for p in split(addition) if key(p) not in have]
    if not new:
        return current
    return f"{current.strip().rstrip(',')}, {join(new)}"


def looks_like_sentence(piece):
    return len(piece.split()) > 4 or piece.rstrip().endswith(".")
