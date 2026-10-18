"""The chat model's context: how long it is, what its memory (the KV cache) costs, and which messages of a conversation
go into it.

What happens when a conversation outgrows it, from the cheapest to the best:
- llama-server's own context shift (--context-shift) drops tokens from the middle while it writes. Never used here:
  every request leaves room for its answer, so the server never has to.
- The window: the newest messages that fit; the oldest are left out unread. It moves in steps, not one message a
  turn, so the start of what the model reads stays the same and llama-server reuses its cache of it (only the new
  messages are read, not the whole conversation every turn).
- Compact: the older part summed up into the system prompt, the last messages kept (chat.compact; by itself near
  the limit). Wrap up: a new conversation started from a summary of this one (chat.wrap_up).

The context's length and memory:
- KV cache type: the cache in f16 (exact), q8_0 (half the memory, no loss you can see) or q4_0 (a quarter, some loss).
- RoPE: a context longer than the model was trained for is stretched with YaRN (Auto), else held to what it was
  trained for (Off). A model whose file already says how it is scaled is never stretched again.
- Sliding-window attention (Gemma 2 and 3) and hybrid models (Qwen3.5, Qwen3-Next) keep a full cache in only some of
  their layers; the estimate counts that."""

from __future__ import annotations

import math
import os

from . import gguf, settings

KV_TYPES = ("f16", "q8_0", "q4_0")
KV_BYTES = {"f16": 2.0, "q8_0": 34 / 32, "q4_0": 18 / 32}  # bytes per number, with the block scales
ROPE_MODES = ("Auto", "Off")
SLIDE = 0.7       # when the window must move, it moves until the messages take this much of the room
MARGIN = 64       # tokens kept free besides the answer's, for the template's own words
# layers that keep only a window of the context (sliding-window attention): the share of them, by architecture
SWA_SHARE = {"gemma2": 1 / 2, "gemma3": 5 / 6, "gemma3n": 5 / 6, "cohere2": 3 / 4}


def kv_type():
    value = str(settings.opt("pv_vlm_kv_type") or "f16")
    return value if value in KV_TYPES else "f16"


def _model():
    return settings.clean_path(settings.opt("pv_vlm_model_path"))


def _info(path=None):
    path = path or _model()
    return gguf.info(path) if path and os.path.isfile(path) else gguf.info("")


def _scaled(info):
    """Whether the file already says how its positions are stretched (then its context_length is the stretched one)."""
    a = info.get("attention") or {}
    return str(a.get("rope.scaling.type") or "none") not in ("none", "") and float(a.get("rope.scaling.factor") or 1) > 1


def trained(path=None):
    """The context the model was trained for (its file's context_length), or 0 when it does not say."""
    return int(_info(path).get("context") or 0)


def size(path=None):
    """The context llama-server is started with: the one in Settings, held to what the model was trained for when
    RoPE is Off (or the file is already scaled)."""
    wanted = int(settings.opt("pv_vlm_context"))
    info = _info(path)
    native = int(info.get("context") or 0)
    if native and wanted > native and (str(settings.opt("pv_vlm_rope")) == "Off" or _scaled(info)):
        return native
    return wanted


def rope_args(path=None):
    """YaRN flags when the context is longer than the model was trained for (RoPE: Auto), else none."""
    info = _info(path)
    native, ctx = int(info.get("context") or 0), size(path)
    if not native or ctx <= native or _scaled(info) or str(settings.opt("pv_vlm_rope")) == "Off":
        return []
    factor = math.ceil(ctx / native * 10) / 10
    return ["--rope-scaling", "yarn", "--rope-scale", f"{factor:g}", "--yarn-orig-ctx", str(native)]


def server_args(path=None):
    """llama-server's flags for the context: its length, the cache's type, the stretching."""
    out = ["-c", str(size(path))]
    if kv_type() != "f16":
        out += ["-ctk", kv_type(), "-ctv", kv_type()]
    return out + rope_args(path)


def kv_per_token(info, cache=None):
    """Bytes the KV cache takes for one token of context, in every layer that keeps it; None when the file does not
    say enough. Returns (full layers' bytes, windowed layers' bytes, window)."""
    a = info.get("attention") or {}
    layers = int(info.get("layers") or 0)
    heads = a.get("attention.head_count")
    heads = max(heads) if isinstance(heads, list) and heads else heads
    width = int(a.get("embedding_length") or 0)
    kv_heads = a.get("attention.head_count_kv") or heads
    if not layers or not kv_heads or not (a.get("attention.key_length") or (width and heads)):
        return None
    per_layer = kv_heads if isinstance(kv_heads, list) else [kv_heads] * layers
    per_layer = [int(h or 0) for h in per_layer[:layers]] + [0] * max(0, layers - len(per_layer))
    k = int(a.get("attention.key_length") or width // int(heads))
    v = int(a.get("attention.value_length") or k)
    each = (k + v) * KV_BYTES[cache or kv_type()]
    interval = int(a.get("full_attention_interval") or 0)
    if interval > 1:  # a hybrid model: only every interval-th layer attends (and caches); the others keep a small state
        per_layer = [h if (i + 1) % interval == 0 else 0 for i, h in enumerate(per_layer)]
    share = SWA_SHARE.get(info.get("arch"), 0) if a.get("attention.sliding_window") else 0
    total = sum(per_layer) * each
    return total * (1 - share), total * share, int(a.get("attention.sliding_window") or 0)


def kv_gb(path=None, ctx=None, cache=None):
    """The KV cache's size in GB for the model and context: from the file's attention shape, else about 0.14 GB a
    thousand tokens (a 7-9B model in f16)."""
    info = _info(path)
    ctx = int(ctx or size(path))
    shape = kv_per_token(info, cache)
    if not shape:
        return ctx / 1024 * 0.14 * KV_BYTES[cache or kv_type()] / 2
    full, windowed, window = shape
    return (full * ctx + windowed * min(ctx, window or ctx)) / 1024 ** 3


def describe(path=None):
    """For Muse's model section: {"size", "trained", "kv_gb", "kv_type", "rope"}."""
    args = rope_args(path)
    return {"size": size(path), "trained": trained(path), "kv_gb": round(kv_gb(path), 2), "kv_type": kv_type(),
            "rope": f"YaRN ×{args[3]}" if args else ("held to the model's own" if size(path) < int(settings.opt("pv_vlm_context")) else "")}


# ------------------------------------------------------------------ a conversation in the context


def reserve():
    """Tokens kept free for the answer: the longest answer, three times that when the model thinks first."""
    return int(settings.opt("pv_chat_max_tokens")) * (3 if settings.opt("pv_chat_think") else 1)


def _need(m):
    from . import chat

    return m.get("tokens") or chat._tokens(m["text"], m.get("files"))


def room(c):
    """Tokens the messages may take: the context, less the answer's share, the system prompt and a margin."""
    from . import chat

    return size() - reserve() - chat._tokens(c["system"], []) - chat._tokens(c.get("summary") or "", []) - MARGIN


def usage(c):
    """How full the context is: {"used", "room", "size", "reserve"}, in tokens (estimated)."""
    from . import chat

    used = sum(_need(m) for m in c["messages"]) + chat._tokens(c.get("summary") or "", [])
    return {"used": used, "room": max(0, room(c)), "size": size(), "reserve": reserve()}


def window(c, extra=0):
    """The messages that go to the model, and how many older ones were left out. extra: tokens kept free besides the
    answer's (Verify's draft and what it found).

    All of them when they fit. When they do not, the window starts where it started last time (c["start"]) as long
    as the rest fits, and only then moves, far enough to leave room for several more turns: what the model reads
    begins the same way from turn to turn, so llama-server answers from its cache instead of reading it all again."""
    budget = room(c) - extra
    msgs = c["messages"]
    need = [_need(m) for m in msgs]
    first = 0
    if sum(need) > budget:
        first = next((i for i, m in enumerate(msgs) if m["id"] == c.get("start")), 0)
        if sum(need[first:]) > budget:
            target, used, first = budget * SLIDE, 0, len(msgs)
            while first > 0 and (used + need[first - 1] <= target or first == len(msgs)):
                first -= 1
                used += need[first]
    while first < len(msgs) - 1 and msgs[first]["role"] == "assistant":  # what the model reads starts with the user
        first += 1
    if first:
        c["start"] = msgs[first]["id"]
    else:
        c.pop("start", None)
    return msgs[first:], first
