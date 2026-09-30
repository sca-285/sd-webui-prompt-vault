"""Muse: timed idea cards, drawn over every tab by javascript/prompt_vault_muse.js.

Packs ship in data/muse_packs. Packs of your own go in <data folder>/muse/packs and
win over a shipped pack with the same id. Muse's settings and the optional avatar
live in <data folder>/muse, next to the library, so updates never touch them.

A pack is a JSON file made of scenes. A scene holds things that belong together: who is
there, what they do, where, in what light. An idea takes one scene of one pack, then one
entry of each of its lists, so every combination makes sense:

  {"id": "...", "name": "...", "nsfw": false,
   "styles": [...], "negatives": [...],          <- for every scene of the pack
   "scenes": [
     {"title": "Rainy café window",
      "subjects": [...], "actions": [...], "settings": [...],
      "lighting": [...], "camera": [...], "details": [...]}]}

A list a scene leaves out comes from the pack, so the pack's own lists must suit every
scene. A pack without scenes (the first format) is one big scene.
"""

from __future__ import annotations

import base64
import glob
import json
import os
import random
import re
import threading
import uuid

from . import TAG, settings, store, text

EXT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK_DIR = os.path.join(EXT_ROOT, "data", "muse_packs")
SLOTS = ("subjects", "actions", "settings", "lighting", "camera", "styles", "details")
DETAIL_CHANCE = 0.6  # a detail makes an idea specific; on every idea it becomes a tic

TARGETS = ("txt2img", "img2img", "vault")
MODES = ("replace", "append")
TIPO_OUTPUTS = ("Tags", "Natural language", "Tags + natural language")
TIPO_LENGTHS = ("very short", "short", "long", "very long")

# NSFW ideas never carry these, whatever a pack says, and always send them as negatives.
MINOR = re.compile(r"\b(child|children|kid|kids|loli|lolicon|shota|shotacon|underage|minor|teen|teenager|"
                   r"preteen|toddler|infant|schoolgirl|schoolboy|cub|young girl|young boy|little girl|little boy)\b",
                   re.IGNORECASE)
GUARD_NEGATIVES = ["child", "loli", "shota", "underage", "childlike proportions"]

AVATAR_TYPES = {  # extension: leading bytes
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".webp": (b"RIFF",),
}
AVATAR_MAX = 4 * 1024 * 1024

DEFAULT_STATE = {
    "enabled": True,
    "paused": False,
    "interval_minutes": 15,
    "allow_nsfw": False,
    "packs": None,           # None (or empty): every SFW pack; a list: exactly those
    "target": "txt2img",
    "send_mode": "replace",
    "send_negative": True,
    "use_tipo": False,
    "tipo_output": "Tags + natural language",
    "tipo_length": "short",
    "blacklist": "",
}

_lock = threading.RLock()
_packs = {"sig": None, "list": []}


# ------------------------------------------------------------------ places


def muse_dir():
    path = os.path.join(settings.data_dir(), "muse")
    os.makedirs(path, exist_ok=True)
    return path


def user_pack_dir():
    return os.path.join(muse_dir(), "packs")


def _state_path():
    return os.path.join(muse_dir(), "state.json")


# ------------------------------------------------------------------ state


def _normalise(data):
    out = dict(DEFAULT_STATE)
    out.update({k: v for k, v in data.items() if k in DEFAULT_STATE})
    for key in ("enabled", "paused", "allow_nsfw", "send_negative", "use_tipo"):
        out[key] = bool(out[key])
    try:
        out["interval_minutes"] = max(5, min(30, int(out["interval_minutes"])))
    except (TypeError, ValueError):
        out["interval_minutes"] = DEFAULT_STATE["interval_minutes"]
    packs = out["packs"] if isinstance(out["packs"], list) else []
    out["packs"] = list(dict.fromkeys(str(p).strip() for p in packs if str(p).strip())) or None
    for key, allowed in (("target", TARGETS), ("send_mode", MODES),
                         ("tipo_output", TIPO_OUTPUTS), ("tipo_length", TIPO_LENGTHS)):
        if out[key] not in allowed:
            out[key] = DEFAULT_STATE[key]
    out["blacklist"] = str(out["blacklist"] or "")[:4000]
    return out


def state():
    with _lock:
        saved = store._read(_state_path(), {})
        return _normalise(saved if isinstance(saved, dict) else {})


def save_state(patch):
    if not isinstance(patch, dict):
        raise store.VaultError("bad Muse settings")
    with _lock:
        data = state()
        data.update({k: v for k, v in patch.items() if k in DEFAULT_STATE})
        data = _normalise(data)
        store.write_json(_state_path(), data)
        return data


# ------------------------------------------------------------------ packs


def _pack_files():
    shipped = sorted(glob.glob(os.path.join(PACK_DIR, "*.json")))
    mine = sorted(glob.glob(os.path.join(user_pack_dir(), "*.json")))
    return shipped + mine  # later wins: a pack of your own replaces a shipped one with its id


def _clean_list(items, nsfw):
    out = []
    for item in items if isinstance(items, list) else []:
        item = str(item).strip()
        if item and not (nsfw and MINOR.search(item)):
            out.append(item)
    return out


def _slots(data, nsfw):
    """The lists of a pack or a scene; 'twists' is the first format's name for 'details'."""
    data = dict(data)
    data.setdefault("details", data.get("twists"))
    return {slot: _clean_list(data.get(slot), nsfw) for slot in SLOTS}


def _read_pack(data, custom):
    nsfw = bool(data.get("nsfw"))
    pack = {"id": str(data["id"]).strip(), "name": str(data.get("name") or data["id"]), "nsfw": nsfw,
            "custom": custom, "negatives": _clean_list(data.get("negatives"), False)}
    pack.update(_slots(data, nsfw))
    scenes = []
    for raw in data.get("scenes") or [{}]:
        if not isinstance(raw, dict):
            continue
        scene = _slots(raw, nsfw)
        # what the scene leaves out, the pack gives
        for slot in SLOTS:
            scene[slot] = scene[slot] or pack[slot]
        scene["title"] = str(raw.get("title") or "").strip()
        if scene["subjects"] or scene["settings"]:
            scenes.append(scene)
    pack["scenes"] = scenes
    return pack if scenes else None


def load_packs():
    """Every pack, read again only when a file was added, removed or changed."""
    files = _pack_files()
    sig = tuple((f, os.path.getmtime(f)) for f in files if os.path.isfile(f))
    with _lock:
        if _packs["sig"] == sig:
            return _packs["list"]
        found = {}
        for path in files:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                print(f"{TAG} Muse pack {os.path.basename(path)} skipped: {exc}")
                continue
            if not isinstance(data, dict) or not str(data.get("id") or "").strip():
                continue
            pack = _read_pack(data, custom=not path.startswith(PACK_DIR))
            if pack:
                found[pack["id"]] = pack
        _packs.update(sig=sig, list=sorted(found.values(), key=lambda p: (p["nsfw"], p["name"].lower())))
        return _packs["list"]


def packs_public():
    return [{"id": p["id"], "name": p["name"], "nsfw": p["nsfw"], "custom": p["custom"],
             "size": len(p["scenes"])} for p in load_packs()]


def _active_packs(st):
    usable = [p for p in load_packs() if st["allow_nsfw"] or not p["nsfw"]]
    if st["packs"] is None:
        return [p for p in usable if not p["nsfw"]]
    wanted = set(st["packs"])
    return [p for p in usable if p["id"] in wanted]


# ------------------------------------------------------------------ blacklist


def parse_blacklist(value):
    return [w.strip().lower() for w in re.split(r"[,;\n]", str(value or "")) if w.strip()]


def _blacklist_test(rules):
    if not rules:
        return lambda s: False
    pattern = re.compile("|".join(r"(?<!\w)" + re.escape(r) + r"(?!\w)" for r in rules), re.IGNORECASE)
    return lambda s: bool(pattern.search(s or ""))


# ------------------------------------------------------------------ ideas


def compose(seed=None):
    st = state()
    packs = _active_packs(st)
    if not packs:
        raise store.VaultError("No pack is on. Pick at least one on the Muse settings page.")
    rules = parse_blacklist(st["blacklist"])
    blocked = _blacklist_test(rules)
    rng = random.Random(seed)

    for _ in range(24):
        pack = rng.choice(packs)
        scene = rng.choice(pack["scenes"])
        parts = {}
        for slot in SLOTS:
            pool = [x for x in scene[slot] if not blocked(x)]
            parts[slot] = rng.choice(pool) if pool else ""
        if scene["subjects"] and not parts["subjects"]:
            continue  # the blacklist took every subject: this scene is not a scene anymore
        if rng.random() >= DETAIL_CHANCE:
            parts["details"] = ""
        # subject first, then what they do, where, the light, the framing, the look
        order = ("subjects", "actions", "details", "settings", "lighting", "camera", "styles")
        seen, pieces = set(), []
        for slot in order:
            for piece in text.split(parts[slot]):
                if not blocked(piece) and text.key(piece) not in seen:
                    seen.add(text.key(piece))
                    pieces.append(piece)
        if not pieces:
            continue

        negatives = list(pack["negatives"]) + (GUARD_NEGATIVES if pack["nsfw"] else []) + rules
        seen, negative = set(), []
        for n in negatives:
            if text.key(n) not in seen:
                seen.add(text.key(n))
                negative.append(n)

        spark = scene["title"] or " · ".join(x for x in (parts["subjects"], parts["actions"], parts["settings"]) if x)
        return {
            "id": uuid.uuid4().hex[:12],
            "pack": pack["id"],
            "pack_name": pack["name"],
            "nsfw": pack["nsfw"],
            "spark": spark,
            "twist": parts["details"],
            "positive": text.join(pieces),
            "negative": text.join(negative),
        }
    raise store.VaultError("Every idea hit the blacklist: loosen it or turn more packs on.")


def expand_with_tipo(positive):
    from . import tipo

    st = state()
    result, note = tipo.expand(positive, output=st["tipo_output"], length=st["tipo_length"])
    if not result:
        raise store.VaultError(note or "TIPO returned nothing")
    return {"positive": result, "note": note}


# ------------------------------------------------------------------ avatar


def avatar_file():
    for ext in AVATAR_TYPES:
        path = os.path.join(muse_dir(), "avatar" + ext)
        if os.path.isfile(path):
            return path
    return None


def avatar_info():
    path = avatar_file()
    return {"url": f"/muse/avatar?v={int(os.path.getmtime(path))}" if path else ""}


def save_avatar(data):
    """data: a data: URL or bare base64 of a PNG, JPEG, WebP or GIF."""
    try:
        raw = base64.b64decode(str(data or "").split(",", 1)[-1], validate=False)
    except Exception:
        raw = b""
    if not raw:
        raise store.VaultError("That file could not be read.")
    if len(raw) > AVATAR_MAX:
        raise store.VaultError("The avatar must be under 4 MB.")
    ext = next((e for e, heads in AVATAR_TYPES.items() if raw.startswith(heads)), None)
    if ext == ".webp" and raw[8:12] != b"WEBP":
        ext = None
    if not ext:
        raise store.VaultError("The avatar must be a PNG, JPEG, WebP or GIF.")
    with _lock:
        clear_avatar()
        path = os.path.join(muse_dir(), "avatar" + ext)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(raw)
        os.replace(tmp, path)
    return avatar_info()


def clear_avatar():
    with _lock:
        for ext in AVATAR_TYPES:
            try:
                os.remove(os.path.join(muse_dir(), "avatar" + ext))
            except FileNotFoundError:
                pass
    return avatar_info()


def snapshot():
    return {"state": state(), "packs": packs_public(), "avatar": avatar_info()}
