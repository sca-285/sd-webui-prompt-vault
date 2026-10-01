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

Any list may also be given by cast, like subjects, so one place serves every cast with what
suits it: {"solo": [...], "pair": [...], "2girls": [...], "groups": [...]}. See ALIASES.
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

from . import TAG, kinks as kinklib, settings, store, text, vocab

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
    # groups of three and more: their count tags depend on how many, see _group_tags
    "girls": ("Girls 3+", None, "yuri"),
    "boys": ("Boys 3+", None, "yaoi"),
    "harem": ("1boy + girls", None, "hetero"),
    "reverse": ("1girl + boys", None, "hetero"),
    "mixed": ("Mixed group", None, "hetero"),
    # futanari: NSFW only
    "futa": ("Futa", "1girl, futanari, solo", ""),
    "futa_girl": ("Futa + girl", "2girls, futanari", "yuri"),
    "futa_boy": ("Futa + boy", "1girl, 1boy, futanari", "hetero"),
    # a human and an anthro together in the frame
    "human_furry": ("Human + furry", "furry with non-furry, interspecies", "hetero"),
    "group": ("3+, own tags", "", ""),  # scenes that write their own count tags
    "furry": ("Furry", "anthro, furry", ""),
    "nonhuman": ("Non-human", "", ""),
    "any": ("Other", "", ""),
}
RATINGS = {"sfw": "SFW", "suggestive": "Suggestive", "nude": "Nude", "explicit": "Explicit"}

# names that stand for several casts in a scene's lists: {"pair": [...]} serves 1girl 1boy,
# 2girls and 2boys alike; a cast named on its own wins over the names it is part of
ALIASES = {
    "solo": ("1girl", "1boy", "furry", "nonhuman", "futa"),
    "pair": ("1girl1boy", "2girls", "2boys", "futa_girl", "futa_boy", "human_furry"),
    "groups": ("girls", "boys", "harem", "reverse", "mixed"),
}
ALIASES["people"] = ALIASES["solo"] + ALIASES["pair"] + ALIASES["groups"]

# how many people a group can be; 6 stands for 6 and more
SIZES = (3, 4, 5, 6)
GROUP_SIZES = {"girls": SIZES, "boys": SIZES, "harem": SIZES, "reverse": SIZES, "mixed": (4, 5, 6)}


def _count(n, word):
    """3 'girl' -> '3girls'; 1 -> '1girl'; 6 and more -> '6+girls'."""
    return f"1{word}" if n == 1 else (f"6+{word}s" if n >= 6 else f"{n}{word}s")


def _plus(n):
    return "6+" if n >= 6 else str(n)


def _group_tags(kind, size, girls=None):
    """(count tags, label on the card, girls in a mixed group) for a group of size people."""
    if kind == "girls":
        return f"{_count(size, 'girl')}, multiple girls", f"{_plus(size)} girls", None
    if kind == "boys":
        return f"{_count(size, 'boy')}, multiple boys, male focus", f"{_plus(size)} boys", None
    if kind == "harem":
        n = size - 1 if size < 6 else 6
        return f"1boy, {_count(n, 'girl')}, multiple girls, harem", f"1boy + {_plus(n)} girls", None
    if kind == "reverse":
        n = size - 1 if size < 6 else 6
        return f"1girl, {_count(n, 'boy')}, multiple boys, reverse harem", f"1girl + {_plus(n)} boys", None
    # mixed: as many girls as given, the rest boys
    total = min(size, 6)
    girls = girls if girls and 2 <= girls <= total - 2 else total // 2
    boys = total - girls
    plus = " (6+)" if size >= 6 else ""
    return (f"{_count(girls, 'girl')}, {_count(boys, 'boy')}, multiple girls, multiple boys",
            f"{girls} girls + {boys} boys{plus}", girls)

# the parts of an idea, in the order they go into the prompt
SLOTS = ("subject", "body", "expression", "gesture", "action", "kink", "detail", "setting", "lighting", "camera", "style")
NSFW_ONLY = ("futa", "futa_girl", "futa_boy")
LISTS = {"subject": "subjects", "body": "bodies", "expression": "expressions", "gesture": "gestures", "action": "actions", "kink": "kinks",
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
                   r"preteen|toddler|infant|schoolgirl|schoolboy|cub|young girl|young boy|little girl|little boy|chibi)\b",
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
    "sizes": [],             # groups: empty, any size; else some of SIZES
    "send_mode": "replace",
    "send_negative": True,
    "kinks": [],             # NSFW layers on top of the scene, see kinks.py; empty: none
    "styles": [],            # style families of the library (vocab.py); empty: the scene's own styles
    "anatomy": True,         # the Body part of NSFW ideas: breasts, pussy, penis, body hair...
    "arrange_with": "library",  # or "qwen"
    "describe_as": "both",      # "paragraph": Qwen's paragraph alone; "both": the tags, then the paragraph
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
    for key in ("enabled", "allow_nsfw", "send_negative", "use_tipo", "anatomy"):
        out[key] = bool(out[key])
    try:
        out["interval_minutes"] = max(5, min(30, int(out["interval_minutes"])))
    except (TypeError, ValueError):
        out["interval_minutes"] = DEFAULT_STATE["interval_minutes"]
    out["themes"] = _names(out["themes"])[:100]
    out["casts"] = _names(out["casts"], CASTS)
    out["ratings"] = _names(out["ratings"], RATINGS)
    out["kinks"] = _names(out["kinks"], kinklib.KINKS)
    out["styles"] = _names(out["styles"])[:40]
    sizes = out["sizes"] if isinstance(out["sizes"], list) else []
    out["sizes"] = sorted({int(n) for n in sizes if str(n).isdigit() and int(n) in SIZES})
    for key, allowed in (("send_mode", MODES), ("tipo_output", TIPO_OUTPUTS), ("tipo_length", TIPO_LENGTHS),
                         ("arrange_with", ("library", "qwen")), ("describe_as", ("paragraph", "both"))):
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


def _keyed(value, nsfw):
    """A list, or lists by cast or alias, as {cast or alias or "*": [entries]}; {} when empty."""
    if isinstance(value, dict):
        out = {str(k): _clean(v, nsfw) for k, v in value.items()}
        return {k: v for k, v in out.items() if v}
    clean = _clean(value, nsfw)
    return {"*": clean} if clean else {}


def _for_cast(lists, cast):
    """The entries a cast gets: its own, else those of an alias it is part of, else everyone's."""
    if cast in lists:
        return lists[cast]
    for alias in ("pair", "groups", "solo", "people"):
        if alias in lists and cast in ALIASES[alias]:
            return lists[alias]
    return lists.get("*", [])


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
            lists[slot] = _keyed(raw.get(key), nsfw) or _keyed(data.get(key), nsfw)
        subjects = raw.get("subjects") if "subjects" in raw else data.get("subjects")
        if isinstance(subjects, list):
            subjects = {"any": subjects}
        casts = {}
        for name, items in (subjects or {}).items():
            # an alias gives its casts what they were not given by name
            for cast in ALIASES.get(name, (name,)):
                if cast not in CASTS or (name in ALIASES and cast in subjects) or (cast in NSFW_ONLY and not nsfw):
                    continue
                clean = _clean(items, nsfw)
                if clean or cast == "none":
                    casts[cast] = clean or [""]
        if not casts:
            continue
        moods = raw.get("mood") or data.get("mood") or []
        moods = [moods] if isinstance(moods, str) else moods
        if not lists["expression"]:
            lists["expression"] = {"*": [e for m in moods for e in MOODS.get(m, [])]}
        out.append({
            "id": f"{'my' if custom else 'x'}:{stem}:{raw.get('id') or i}",
            "title": str(raw.get("title") or data.get("theme") or stem),
            "theme": str(raw.get("theme") or data.get("theme") or stem),
            "rating": rating,
            "casts": casts,
            "sizes": sorted({int(n) for n in (raw.get("sizes") or data.get("sizes") or SIZES)
                             if str(n).isdigit() and int(n) in SIZES}) or list(SIZES),
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
        "sizes": [[n, _plus(n)] for n in SIZES],
        "group_sizes": {k: list(v) for k, v in GROUP_SIZES.items()},
        "kinks": [[k, v["label"], v.get("themes")] for k, v in kinklib.KINKS.items()],
        "kink_casts": kinklib.casts_by_level(ALIASES, list(CASTS)),
        "styles": [[family, len(tags)] for family, tags in vocab.styles().items()],
        # one row per scene: [theme index, [casts], rating, [group sizes]]
        "index": [[themes.index(s["theme"]), list(s["casts"]), s["rating"], s["sizes"]] for s in scenes],
    }


def _sizes(scene, cast, wanted=()):
    """The group sizes a scene allows its cast, within the ones wanted (none wanted: any)."""
    if cast not in GROUP_SIZES:
        return [0]
    sizes = [n for n in scene["sizes"] if n in GROUP_SIZES[cast]]
    return [n for n in sizes if n in wanted] if wanted else sizes


def _kinks_for(scene, st):
    """The chosen kinks that can join a scene: NSFW scenes only, of a theme the kink belongs to."""
    if scene["rating"] == "sfw" or not st["allow_nsfw"]:
        return []
    return [k for k in st["kinks"] if kinklib.themed(k, scene["theme"])]


def _matching(st):
    ratings = set(_ratings_on(st))
    themes, casts = set(st["themes"]), set(st["casts"])
    out = []
    for s in load_scenes():
        if s["rating"] not in ratings or (themes and s["theme"] not in themes):
            continue
        chosen = _kinks_for(s, st)
        if st["kinks"] and not chosen:
            continue  # with a kink chosen, every idea carries one
        usable = [c for c in s["casts"] if (not casts or c in casts) and _sizes(s, c, st["sizes"])
                  and (not st["kinks"] or any(kinklib.entries(k, s["rating"], c, ALIASES) for k in chosen))]
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


def _pools(scene, cast, st=None):
    pools = {slot: _for_cast(lists, cast) for slot, lists in scene["lists"].items()}
    pools["subject"] = scene["casts"][cast]
    chosen = _kinks_for(scene, st) if st else []
    if chosen:
        pools["kink"] = list(dict.fromkeys(e for k in chosen for e in kinklib.entries(k, scene["rating"], cast, ALIASES)))
    if cast == "none":  # nobody to have a face or hands
        pools["expression"], pools["gesture"] = [], []
    return pools


ORDER_DRAWN = ("subject", "body", "action", "kink", "gesture", "expression", "detail", "setting", "lighting", "camera", "style")


def _library_poses(scene, who, parts):
    """Poses of the library for one person, or two close at a nude level; group and explicit pairs keep the scene's."""
    level = scene["rating"]
    if who in ("none", "group", "any") or who in ALIASES["groups"] or (who in ALIASES["pair"] and level != "nude"):
        return []
    female, male = kinklib._sexes(who, parts["subject"]) if who in ALIASES["solo"] else (False, False)
    gender = "f" if female and not male else "m" if male and not female else ""
    return vocab.poses_for(level, "solo" if who in ALIASES["solo"] else "pair", gender, parts["action"])


def compose(scene_id=None, cast=None, keep=None, roll=None, seed=None, size=None, girls=None):
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
        pools = _pools(scene, who, st)
        if who in GROUP_SIZES:
            allowed = _sizes(scene, who, [] if scene_id else st["sizes"])
            people = int(size) if str(size).isdigit() and int(size) in allowed else rng.choice(allowed)
            mix = int(girls) if scene_id and str(girls).isdigit() else (rng.randint(2, min(people, 6) - 2) if who == "mixed" else None)
            cast_tags, label, mix = _group_tags(who, people, mix)
        else:
            people, mix = 0, None
            label, cast_tags = CASTS[who][0], CASTS[who][1]
        if st["styles"]:  # style families chosen on the card win over the scene's own
            fams = vocab.styles()
            pools["style"] = list(dict.fromkeys(t for f in st["styles"] for t in fams.get(f, [])))
        if scene["rating"] != "sfw":
            pools["style"] = [x for x in pools["style"] if not MINOR.search(x)]
        parts = {}
        # drawn in this order: the body follows the subject (a male wolf, a female android), the pose
        # follows the action (no "lying on back" for someone riding); the prompt keeps the order of SLOTS
        for slot in ORDER_DRAWN:
            if slot == "body":
                pools["body"] = kinklib.body(scene["rating"], who, parts["subject"], scene["theme"], rng) if st["anatomy"] else []
            if slot == "gesture":
                pools["gesture"] = list(dict.fromkeys(pools["gesture"] + _library_poses(scene, who, parts)))
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
        nsfw_tags = CASTS[who][2]
        front = [cast_tags] + ([nsfw_tags, "adults" if who in GROUP_SIZES else "adult"] if nsfw and who != "none" else [])

        seen, pieces = set(), []
        for chunk in front + [parts[s] for s in SLOTS]:
            for piece in text.split(chunk):
                if not blocked(piece) and text.key(piece) not in seen:
                    seen.add(text.key(piece))
                    pieces.append(piece)

        extra = [n for word, negs in kinklib.SUBJECT_NEGATIVES.items()
                 if word in (parts["subject"] + " " + parts["kink"]).lower() for n in negs]
        seen, negative = set(), []
        for n in scene["negatives"] + (GUARD_NEGATIVES if nsfw else []) + extra + rules:
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
            "size": people,
            "girls": mix,
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
