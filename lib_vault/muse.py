"""Muse: prompt ideas on a floating card, drawn over every tab by javascript/prompt_vault_muse.js.

Ideas come from scenes. A scene holds what belongs together: who can be there, what they
do, where, in what light and mood. An idea takes one scene, then one entry of each of its
lists, so every combination makes sense. Every part of an idea can be rolled again or
locked on the card; locked parts keep the scene.

Scenes ship in data/muse_scenes. Files of your own go in <data folder>/muse/scenes. Muse's
settings and the optional avatar live in <data folder>/muse, so updates never touch them.

A scene file:

  {"theme": "Film", "rating": "sfw",                 <- defaults for its scenes
   "styles": [...], "camera": [...], "negatives": [...],
   "scenes": [
     {"title": "Night diner", "mood": ["tense", "melancholy"],
      "subjects": {"1girl": ["trench coat, red lipstick"], "1boy": ["rumpled shirt"]},
      "gestures": [...], "actions": [...], "settings": [...], "lighting": [...],
      "details": [...]}]}

subjects is keyed by cast (see CASTS); the cast's own tags ("1girl, solo") are added by
Muse. rating is one of RATINGS. mood picks the expressions (see MOODS); a scene may list
its own "expressions" instead. A list a scene leaves out comes from its file.
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
SCENE_DIR = os.path.join(EXT_ROOT, "data", "muse_scenes")

# cast: (label on the card, tags in front of every idea, extra tags when the idea is NSFW)
CASTS = {
    "none": ("No humans", "no humans", ""),
    "1girl": ("1girl", "1girl, solo", ""),
    "1boy": ("1boy", "1boy, solo, male focus", ""),
    "1girl1boy": ("1girl 1boy", "1girl, 1boy", "hetero"),
    "2girls": ("2girls", "2girls", "yuri"),
    "2boys": ("2boys", "2boys, male focus", "yaoi"),
    "group": ("3+", "", ""),
    "furry": ("Furry", "anthro, furry", ""),
    "nonhuman": ("Non-human", "", ""),
    "any": ("Other", "", ""),
}
RATINGS = {"sfw": "SFW", "suggestive": "Suggestive", "nude": "Nude", "explicit": "Explicit"}

# the parts of an idea, in the order they go into the prompt
SLOTS = ("subject", "expression", "gesture", "action", "detail", "setting", "lighting", "camera", "style")
LISTS = {"subject": "subjects", "expression": "expressions", "gesture": "gestures", "action": "actions",
         "detail": "details", "setting": "settings", "lighting": "lighting", "camera": "camera", "style": "styles"}
CHANCE = {"gesture": 0.7, "detail": 0.6}  # on every idea they would become a tic

MOODS = {
    "calm": ["calm expression", "soft smile", "pensive", "relaxed expression", "faint smile"],
    "happy": ["smile", "laughing", "grin", "bright smile"],
    "serious": ["serious expression", "determined expression", "focused expression", "stern expression"],
    "tense": ["worried expression", "wide eyes", "nervous expression", "fearful expression", "holding breath"],
    "melancholy": ["sad expression", "tired eyes", "wistful expression", "downcast eyes"],
    "cool": ["smirk", "confident expression", "half-lidded eyes", "expressionless"],
    "playful": ["playful smile", "tongue out", "one eye closed, wink", "teasing smile"],
    "shy": ["blush", "shy smile", "embarrassed expression", "flustered"],
    "sultry": ["seductive smile", "biting lip", "half-lidded eyes, blush", "parted lips"],
    "passion": ["flushed face, heavy breathing", "moaning, open mouth", "half-closed eyes, blush", "biting lip, sweat",
                "tears of pleasure", "gasping"],
    "afterglow": ["satisfied smile", "sleepy eyes", "blush, relaxed", "content expression"],
}

TARGETS = ("txt2img", "img2img", "vault")
MODES = ("replace", "append")
TIPO_OUTPUTS = ("Tags", "Natural language", "Tags + natural language")
TIPO_LENGTHS = ("very short", "short", "long", "very long")

# NSFW ideas never carry these, whatever a file says, and always send them as negatives.
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
    "enabled": False,        # the timer: ideas by themselves
    "interval_minutes": 15,
    "allow_nsfw": False,
    "themes": [],            # empty: every theme
    "casts": [],             # empty: every cast
    "ratings": ["sfw"],
    "send_mode": "replace",
    "send_negative": True,
    "use_tipo": False,
    "tipo_output": "Tags + natural language",
    "tipo_length": "short",
    "blacklist": "",
}

_lock = threading.RLock()
_scenes = {"sig": None, "list": [], "by_id": {}}


# ------------------------------------------------------------------ places


def muse_dir():
    path = os.path.join(settings.data_dir(), "muse")
    os.makedirs(path, exist_ok=True)
    return path


def user_scene_dir():
    return os.path.join(muse_dir(), "scenes")


def _state_path():
    return os.path.join(muse_dir(), "state.json")


# ------------------------------------------------------------------ state


def _names(value, allowed=None):
    items = value if isinstance(value, list) else []
    out = list(dict.fromkeys(str(v).strip() for v in items if str(v).strip()))
    return [v for v in out if v in allowed] if allowed is not None else out


def _normalise(data):
    out = dict(DEFAULT_STATE)
    out.update({k: v for k, v in data.items() if k in DEFAULT_STATE})
    for key in ("enabled", "allow_nsfw", "send_negative", "use_tipo"):
        out[key] = bool(out[key])
    try:
        out["interval_minutes"] = max(5, min(30, int(out["interval_minutes"])))
    except (TypeError, ValueError):
        out["interval_minutes"] = DEFAULT_STATE["interval_minutes"]
    out["themes"] = _names(out["themes"])[:100]
    out["casts"] = _names(out["casts"], CASTS)
    out["ratings"] = _names(out["ratings"], RATINGS)
    for key, allowed in (("send_mode", MODES), ("tipo_output", TIPO_OUTPUTS), ("tipo_length", TIPO_LENGTHS)):
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


def _ratings_on(st):
    return [r for r in st["ratings"] if r == "sfw" or st["allow_nsfw"]]


# ------------------------------------------------------------------ scenes


def _scene_files():
    shipped = sorted(glob.glob(os.path.join(SCENE_DIR, "*.json")))
    mine = sorted(glob.glob(os.path.join(user_scene_dir(), "*.json")))
    mine += sorted(glob.glob(os.path.join(muse_dir(), "packs", "*.json")))  # where the first versions kept them
    return [(f, False) for f in shipped] + [(f, True) for f in mine]


def _clean(items, nsfw):
    out = []
    for item in items if isinstance(items, list) else []:
        item = str(item).strip()
        if item and not (nsfw and MINOR.search(item)):
            out.append(item)
    return out


def _read_file(path, custom):
    """The scenes of one file. Also takes the pack formats of the first versions."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return []
    stem = os.path.splitext(os.path.basename(path))[0]
    if "id" in data and "theme" not in data:  # a pack of the first versions
        data = dict(data, theme=data.get("name") or data["id"], rating="explicit" if data.get("nsfw") else "sfw")
        data.setdefault("details", data.get("twists"))
        raw_scenes = data.get("scenes") or [{}]
    else:
        raw_scenes = data.get("scenes") or []
    out = []
    for i, raw in enumerate(raw_scenes):
        if not isinstance(raw, dict):
            continue
        rating = raw.get("rating") or data.get("rating") or "sfw"
        if rating not in RATINGS:
            continue
        nsfw = rating != "sfw"
        lists = {}
        for slot, key in LISTS.items():
            if slot == "subject":
                continue
            lists[slot] = _clean(raw.get(key), nsfw) or _clean(data.get(key), nsfw)
        subjects = raw.get("subjects") if "subjects" in raw else data.get("subjects")
        if isinstance(subjects, list):
            subjects = {"any": subjects}
        casts = {}
        for cast, items in (subjects or {}).items():
            if cast not in CASTS:
                continue
            clean = _clean(items, nsfw)
            if clean or cast == "none":
                casts[cast] = clean or [""]
        if not casts:
            continue
        moods = raw.get("mood") or data.get("mood") or []
        moods = [moods] if isinstance(moods, str) else moods
        if not lists["expression"]:
            lists["expression"] = [e for m in moods for e in MOODS.get(m, [])]
        out.append({
            "id": f"{'my' if custom else 'x'}:{stem}:{raw.get('id') or i}",
            "title": str(raw.get("title") or data.get("theme") or stem),
            "theme": str(raw.get("theme") or data.get("theme") or stem),
            "rating": rating,
            "casts": casts,
            "lists": lists,
            "negatives": _clean(data.get("negatives"), False) + _clean(raw.get("negatives"), False),
            "custom": custom,
        })
    return out


def load_scenes():
    """Every scene, read again only when a file was added, removed or changed."""
    files = _scene_files()
    sig = tuple((f, os.path.getmtime(f)) for f, _ in files if os.path.isfile(f))
    with _lock:
        if _scenes["sig"] != sig:
            found = []
            for path, custom in files:
                try:
                    found.extend(_read_file(path, custom))
                except Exception as exc:
                    print(f"{TAG} Muse: {os.path.basename(path)} skipped: {exc}")
            _scenes.update(sig=sig, list=found, by_id={s["id"]: s for s in found})
        return _scenes["list"]


def catalogue():
    """What the filters on the card need: every theme, cast and rating, and which go together."""
    scenes = load_scenes()
    themes = list(dict.fromkeys(s["theme"] for s in scenes))
    return {
        "themes": themes,
        "casts": [[k, v[0]] for k, v in CASTS.items() if any(k in s["casts"] for s in scenes)],
        "ratings": [[k, v] for k, v in RATINGS.items()],
        # one row per scene: [theme index, [casts], rating]
        "index": [[themes.index(s["theme"]), list(s["casts"]), s["rating"]] for s in scenes],
    }


def _matching(st):
    ratings = set(_ratings_on(st))
    themes, casts = set(st["themes"]), set(st["casts"])
    out = []
    for s in load_scenes():
        if s["rating"] not in ratings or (themes and s["theme"] not in themes):
            continue
        usable = [c for c in s["casts"] if not casts or c in casts]
        if usable:
            out.append((s, usable))
    return out


# ------------------------------------------------------------------ blacklist


def parse_blacklist(value):
    return [w.strip().lower() for w in re.split(r"[,;\n]", str(value or "")) if w.strip()]


def _blacklist_test(rules):
    if not rules:
        return lambda s: False
    pattern = re.compile("|".join(r"(?<!\w)" + re.escape(r) + r"(?!\w)" for r in rules), re.IGNORECASE)
    return lambda s: bool(pattern.search(s or ""))


# ------------------------------------------------------------------ ideas


def _pools(scene, cast):
    pools = dict(scene["lists"])
    pools["subject"] = scene["casts"][cast]
    if cast == "none":  # nobody to have a face or hands
        pools["expression"], pools["gesture"] = [], []
    return pools


def compose(scene_id=None, cast=None, keep=None, roll=None, seed=None):
    """A new idea. With scene_id, the same scene again: the parts in keep stay as they are
    (the locked ones), the rest is drawn afresh. roll names a part of keep that must change."""
    st = state()
    rules = parse_blacklist(st["blacklist"])
    blocked = _blacklist_test(rules)
    rng = random.Random(seed)
    keep = {k: str(v) for k, v in (keep or {}).items() if k in SLOTS and isinstance(v, str)}
    current = keep.pop(roll, None) if roll else None  # the part being rolled: anything but this

    load_scenes()
    if scene_id:
        scene = _scenes["by_id"].get(scene_id)
        if not scene:
            raise store.VaultError("That scene is gone (its file changed). Take a new idea.")
        if scene["rating"] != "sfw" and not st["allow_nsfw"]:
            raise store.VaultError("NSFW is off.")
        choices = [(scene, [cast] if cast in scene["casts"] else list(scene["casts"]))]
    else:
        choices = _matching(st)
        if not choices:
            raise store.VaultError("Nothing matches these filters. Loosen them a little.")

    for _ in range(24):
        scene, casts = rng.choice(choices)
        who = rng.choice(casts)
        pools = _pools(scene, who)
        parts = {}
        for slot in SLOTS:
            if slot in keep:
                parts[slot] = keep[slot]
                continue
            pool = [x for x in pools[slot] if not blocked(x)]
            if slot == roll and len(pool) > 1:
                pool = [x for x in pool if x != current]
            if slot != roll and slot in CHANCE and rng.random() >= CHANCE[slot]:
                pool = []
            parts[slot] = rng.choice(pool) if pool else ""
        if pools["subject"] != [""] and not parts["subject"]:
            continue  # the blacklist took every subject of this scene

        nsfw = scene["rating"] != "sfw"
        label, cast_tags, nsfw_tags = CASTS[who]
        front = [cast_tags] + ([nsfw_tags, "adult"] if nsfw and who != "none" else [])
        seen, pieces = set(), []
        for chunk in front + [parts[s] for s in SLOTS]:
            for piece in text.split(chunk):
                if not blocked(piece) and text.key(piece) not in seen:
                    seen.add(text.key(piece))
                    pieces.append(piece)

        seen, negative = set(), []
        for n in scene["negatives"] + (GUARD_NEGATIVES if nsfw else []) + rules:
            if text.key(n) not in seen:
                seen.add(text.key(n))
                negative.append(n)

        return {
            "id": uuid.uuid4().hex[:12],
            "scene": scene["id"],
            "title": scene["title"],
            "theme": scene["theme"],
            "cast": who,
            "cast_label": label,
            "rating": scene["rating"],
            "nsfw": nsfw,
            "parts": [{"slot": s, "value": parts[s], "choices": len(pools[s])} for s in SLOTS if any(pools[s]) or parts[s]],
            "positive": text.join(pieces),
            "negative": text.join(negative),
        }
    raise store.VaultError("Every idea hit the Never use list: loosen it or the filters.")


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
    return {"state": state(), "catalogue": catalogue(), "avatar": avatar_info()}
