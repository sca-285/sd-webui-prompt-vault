"""What a .gguf file says about itself: how many layers, how many experts. Read from its header only,
so a 20 GB model takes a few milliseconds; used to put as much of Qwen on the GPU as fits, the rest in RAM."""

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
            wanted = key == "general.architecture" or key.endswith((".block_count", ".expert_count", ".context_length"))
            value = _value(f, kind, wanted)
            if wanted:
                out[key] = value
    arch = out.get("general.architecture", "")
    return {"arch": arch, "layers": int(out.get(f"{arch}.block_count") or 0), "experts": int(out.get(f"{arch}.expert_count") or 0),
            "context": int(out.get(f"{arch}.context_length") or 0)}


def info(path):
    """{"arch", "layers", "experts", "context"}; zeros when the file cannot be read."""
    try:
        return dict(_info(os.path.abspath(path), os.path.getmtime(path)))
    except Exception:
        return {"arch": "", "layers": 0, "experts": 0, "context": 0}
