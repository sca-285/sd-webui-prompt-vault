"""What a .gguf file says about itself: how many layers, how many experts, how its attention is shaped. Read from
its header only, so a 20 GB model takes a few milliseconds; used to put as much of the model on the GPU as fits,
the rest in RAM, and to size its context."""

from __future__ import annotations

import functools
import os
import struct

_SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}


def _read(f, fmt):
    size = struct.calcsize(fmt)
    data = f.read(size)
    if len(data) != size:
        raise ValueError("the file ends early")
    return struct.unpack(fmt, data)[0]


def _string(f):
    return f.read(_read(f, "<Q")).decode("utf-8", "replace")


def _value(f, kind, keep):
    if kind in _SCALAR:
        return _read(f, _SCALAR[kind])
    if kind == 8:
        return _string(f)
    if kind == 9:
        inner, count = _read(f, "<I"), _read(f, "<Q")
        if inner in _SCALAR and not keep:
            f.seek(struct.calcsize(_SCALAR[inner]) * count, os.SEEK_CUR)  # the tokenizer's long lists: skipped
            return None
        items = [_value(f, inner, keep) for _ in range(count)]
        return items if keep else None
    raise ValueError(f"unknown value type {kind}")


@functools.lru_cache(maxsize=8)
def _info(path, mtime):
    out = {}
    with open(path, "rb") as f:
        if f.read(4) != b"GGUF":
            raise ValueError("not a gguf file")
        _read(f, "<I")  # version
        _read(f, "<Q")  # tensors
        for _ in range(_read(f, "<Q")):
            key = _string(f)
            kind = _read(f, "<I")
            wanted = key in ("general.architecture", "general.name", "general.basename", "general.size_label",
                             "clip.projector_type", "clip.has_vision_encoder") \
                or key.endswith((".block_count", ".expert_count", ".context_length", ".embedding_length",
                                 ".attention.head_count", ".attention.head_count_kv", ".attention.key_length",
                                 ".attention.value_length", ".attention.sliding_window", ".full_attention_interval",
                                 ".rope.scaling.type", ".rope.scaling.factor", ".rope.scaling.original_context_length"))
            value = _value(f, kind, wanted)
            if wanted:
                out[key] = value
    arch = out.get("general.architecture", "")
    return {"arch": arch, "layers": int(out.get(f"{arch}.block_count") or 0), "experts": int(out.get(f"{arch}.expert_count") or 0),
            "context": int(out.get(f"{arch}.context_length") or 0), "name": str(out.get("general.name") or ""),
            "basename": str(out.get("general.basename") or ""), "size": str(out.get("general.size_label") or ""),
            "projector": str(out.get("clip.projector_type") or ""),
            # for the size of the context's memory (the KV cache) and whether it may be stretched (RoPE scaling)
            "attention": {k[len(arch) + 1:]: v for k, v in out.items() if arch and k.startswith(arch + ".")
                          and not k.endswith((".block_count", ".expert_count", ".context_length"))}}


def info(path):
    """{"arch", "layers", "experts", "context", "name", "basename", "size", "projector"} (projector: a vision projector's
    kind, e.g. gemma3, pixtral, glm4v, qwen3vl_merger); "attention": the rest of what the model says of itself
    (embedding_length, attention.head_count_kv, rope.scaling.type…). Zeros and "" when the file cannot be read."""
    try:
        return dict(_info(os.path.abspath(path), os.path.getmtime(path)))
    except Exception:
        return {"arch": "", "layers": 0, "experts": 0, "context": 0, "name": "", "basename": "", "size": "", "projector": "",
                "attention": {}}
