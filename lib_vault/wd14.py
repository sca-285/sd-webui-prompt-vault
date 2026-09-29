"""WD14 tagger (SmilingWolf's v3 models): image -> Danbooru tags with a confidence each.

An ONNX model and its selected_tags.csv, run with onnxruntime on the CPU by
default: a second or two per image and no VRAM. The model is loaded on first use
and let go after a few idle minutes.
"""

from __future__ import annotations

import csv
import os
import threading
import time

from . import TAG, download, settings

# tags whose underscores are part of the face, not word separators
KAOMOJI = {"0_0", "(o)_(o)", "+_+", "+_-", "._.", "<o>_<o>", "<|>_<|>", "=_=", ">_<", "3_3", "6_9", ">_o", "@_@",
           "^_^", "o_o", "u_u", "x_x", "|_|", "||_||"}
CATEGORIES = {0: "general", 1: "artist", 3: "copyright", 4: "character", 5: "meta", 9: "rating"}

_lock = threading.RLock()
_state = {"session": None, "name": None, "tags": None, "last": 0.0, "reaper": None}
_vocab = {"name": None, "items": None}


def _folder(label):
    repo = settings.WD14_MODELS.get(label) or next(iter(settings.WD14_MODELS.values()))
    return repo, os.path.join(settings.models_dir("wd14"), repo.split("/")[-1])


def files(label=None, fetch=True):
    """(model.onnx, selected_tags.csv) of the chosen model, downloaded when missing."""
    label = label or settings.opt("pv_wd14_model")
    repo, folder = _folder(label)
    model, tags = os.path.join(folder, "model.onnx"), os.path.join(folder, "selected_tags.csv")
    if fetch:
        download.fetch(repo, "selected_tags.csv", tags)
        download.fetch(repo, "model.onnx", model)
    return model, tags


def _read_tags(path):
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out.append((row["name"], int(row.get("category", 0) or 0), int(row.get("count", 0) or 0)))
    return out


def vocabulary():
    """[(tag, category, count)] of any downloaded WD14 model, for suggestions; [] when
    none is downloaded yet. Tags are given with spaces, as they are typed."""
    root = settings.models_dir("wd14")
    best = None
    preferred = _folder(settings.opt("pv_wd14_model"))[1]
    candidates = [os.path.join(preferred, "selected_tags.csv")]
    candidates += [os.path.join(root, d, "selected_tags.csv") for d in sorted(os.listdir(root))]
    for path in candidates:
        if os.path.isfile(path):
            best = path
            break
    if best is None:
        return []
    if _vocab["name"] != best:
        items = []
        for name, cat, count in _read_tags(best):
            if cat == 9:
                continue
            items.append((name if name in KAOMOJI else name.replace("_", " "), CATEGORIES.get(cat, "general"), count))
        _vocab.update(name=best, items=items)
    return _vocab["items"]


def _session(label):
    with _lock:
        if _state["session"] is not None and _state["name"] == label:
            _state["last"] = time.time()
            return _state["session"], _state["tags"]
        import onnxruntime as ort

        model, tags = files(label)
        providers = ["CPUExecutionProvider"]
        if bool(settings.opt("pv_wd14_gpu")):
            available = ort.get_available_providers()
            providers = [p for p in ("CUDAExecutionProvider", "ROCMExecutionProvider", "DmlExecutionProvider")
                         if p in available] + providers
        print(f"{TAG} WD14: loading {os.path.basename(os.path.dirname(model))} ({providers[0]})")
        session = ort.InferenceSession(model, providers=providers)
        _state.update(session=session, name=label, tags=_read_tags(tags), last=time.time())
        if _state["reaper"] is None or not _state["reaper"].is_alive():
            _state["reaper"] = threading.Thread(target=_reap, daemon=True)
            _state["reaper"].start()
        return session, _state["tags"]


def _reap():
    while True:
        time.sleep(20)
        with _lock:
            if _state["session"] is None:
                _state["reaper"] = None
                return
            minutes = int(settings.opt("pv_wd14_idle_minutes"))
            if minutes > 0 and time.time() - _state["last"] > minutes * 60:
                unload()
                _state["reaper"] = None
                return


def unload():
    with _lock:
        was = _state["session"] is not None
        _state.update(session=None, name=None, tags=None)
    if was:
        print(f"{TAG} WD14: model unloaded")
    return was


def _prepare(image, size):
    """v3 models: RGB on white, padded square, resized, BGR, 0-255 floats, NHWC."""
    import numpy as np
    from PIL import Image

    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
        canvas.alpha_composite(image)
        image = canvas
    image = image.convert("RGB")
    side = max(image.size)
    square = Image.new("RGB", (side, side), (255, 255, 255))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    if side != size:
        square = square.resize((size, size), Image.BICUBIC)
    array = np.asarray(square, dtype=np.float32)[:, :, ::-1]
    return np.ascontiguousarray(array[None, ...])


def _format(name):
    if name not in KAOMOJI and not bool(settings.opt("pv_wd14_underscores")):
        name = name.replace("_", " ")
    if bool(settings.opt("pv_wd14_escape")):
        name = name.replace("(", "\\(").replace(")", "\\)")
    return name


def tag(image, general=0.35, character=0.85, rating=False):
    """(tags text, note, [(tag, confidence)])."""
    if image is None:
        return "", "Load an image first.", []
    started = time.time()
    try:
        label = settings.opt("pv_wd14_model")
        session, tags = _session(label)
        inp = session.get_inputs()[0]
        size = inp.shape[1] if isinstance(inp.shape[1], int) else 448
        probs = session.run(None, {inp.name: _prepare(image, size)})[0][0]
    except Exception as exc:
        print(f"{TAG} WD14 failed: {exc}")
        return "", f"WD14: {exc}", []

    exclude = {t.strip().lower().replace(" ", "_") for t in str(settings.opt("pv_wd14_exclude") or "").split(",")
               if t.strip()}
    found_char, found_gen, ratings = [], [], []
    for (name, cat, _), p in zip(tags, probs):
        p = float(p)
        if name.lower() in exclude:
            continue
        if cat == 9:
            ratings.append((name, p))
        elif cat == 4 and p >= character:
            found_char.append((name, p))
        elif cat not in (4, 9) and p >= general:
            found_gen.append((name, p))
    found_char.sort(key=lambda x: -x[1])
    found_gen.sort(key=lambda x: -x[1])
    picked = found_char + found_gen
    if rating and ratings:
        picked.append(max(ratings, key=lambda x: x[1]))
    result = ", ".join(_format(n) for n, _ in picked)
    scored = [(_format(n), p) for n, p in picked]
    note = f"WD14: {len(picked)} tags ({len(found_char)} character) in {time.time() - started:.1f}s"
    return result, note, scored
