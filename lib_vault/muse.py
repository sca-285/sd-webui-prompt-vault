"""Muse: prompt ideas on a floating card, drawn over every tab by javascript/prompt_vault_muse.js.

Ideas come from scenes. A scene holds what belongs together: who can be there, what they
do, where, in what light and mood. An idea takes one scene, then one entry of each of its
lists, so every combination makes sense. Every part of an idea can be rolled again or
locked on the card; locked parts keep the scene.

Scenes ship in data/muse_scenes. Files of your own go in <data folder>/muse/scenes. Muse's
settings and the optional avatar live in <data folder>/muse, so updates never touch them.

A scene file:

  {"theme": "Film", "rating": "sfw",                 <- defaults for its scenes
   "styles": [...], "camera": [...],
   "scenes": [
     {"title": "Night diner", "mood": ["tense", "melancholy"],
      "subjects": {"1girl": ["trench coat, red lipstick"], "1boy": ["rumpled shirt"]},
      "gestures": [...], "actions": [...], "settings": [...], "lighting": [...],
      "details": [...]}]}

subjects is keyed by cast (see CASTS); the cast's own tags ("1girl, solo") are added by
Muse. rating is one of RATINGS. mood picks the expressions (see MOODS); a scene may list
its own "expressions" instead. A list a scene leaves out comes from its file.

Any list may also be given by cast, like subjects, so one place serves every cast with what
suits it: {"solo": [...], "pair": [...], "2girls": [...], "groups": [...]}. A cast gets the
entries under its own name and under the names it is part of (see ALIASES); "*" serves the
casts nothing names.

"templates": {"name": {...}} holds what several scenes share; a scene with "use": "name"
(or a list of names) starts from it, and its own lists add to the template's.

Entries are tags, the way a prompt is written: "sitting on bed, crossed legs", never
"she sits on the edge of the bed".
"""

from __future__ import annotations

import base64
import functools
import glob
import json
import os
import random
import re
import threading
import uuid

from . import TAG, acts as actlib, kinks as kinklib, looks, settings, store, text, vocab, when

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
    "human_furry": ("Human + furry", "1furry, interspecies", "hetero"),
    "group": ("3+, own tags", "", ""),  # scenes that write their own count tags
    "furry": ("Furry", "1furry, solo", ""),
    "kemono": ("Kemono", "1furry, solo, kemono", ""),
    # beings that are not human: their subject says who (1girl, vampire...)
    "mythic": ("Myth & fantasy", "", ""),
    "monster": ("Monsters", "", ""),
    "synth": ("Sci-fi beings", "", ""),
    "animal": ("Animals", "no humans, animal focus", ""),  # real creatures, SFW only
    "nonhuman": ("Non-human", "", ""),
    "any": ("Other", "", ""),
}
RATINGS = {"sfw": "SFW", "suggestive": "Suggestive", "nude": "Nude", "explicit": "Explicit"}

# names that stand for several casts in a scene's lists: {"pair": [...]} serves 1girl 1boy,
# 2girls and 2boys alike; a cast gets its own entries and those of the names it is part of
ALIASES = {
    "solo": ("1girl", "1boy", "furry", "kemono", "mythic", "monster", "synth", "nonhuman", "futa"),
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
SLOTS = ("subject", "job", "outfit", "build", "skin", "body", "hair", "eyes", "face", "makeup", "accessory",
         "expression", "mouth", "gaze", "gesture", "action", "kink", "fx", "detail", "setting", "time",
         "lighting", "natural", "light_quality", "light_mood", "light_support", "light_volume",
         "camera", "angle", "view", "framing", "color", "style")
NSFW_ONLY = ("futa", "futa_girl", "futa_boy")
SFW_ONLY = ("none", "animal")
LISTS = {"subject": "subjects", "job": "jobs", "build": "builds", "skin": "skins", "body": "bodies", "hair": "hair", "eyes": "eyes",
         "face": "faces", "makeup": "makeup", "accessory": "accessories", "expression": "expressions", "mouth": "mouths", "gaze": "gazes",
         "gesture": "gestures", "action": "actions", "kink": "kinks", "fx": "fx", "detail": "details", "setting": "settings",
         "time": "times", "lighting": "lighting", "natural": "natural_light", "light_quality": "light_quality", "light_mood": "light_mood",
         "light_support": "light_support", "light_volume": "light_volume", "camera": "camera", "angle": "angles", "view": "views",
         "framing": "framing", "color": "colors", "style": "styles"}
# on every idea they would become a tic: some parts come now and then
CHANCE = {"gesture": 0.7, "detail": 0.6, "job": 0.4, "build": 0.8, "skin": 0.6, "hair": 0.9, "eyes": 0.8, "face": 0.3, "makeup": 0.3,
          "accessory": 0.45, "mouth": 0.35, "gaze": 0.7, "natural": 0.6, "light_quality": 0.5, "light_mood": 0.5, "light_support": 0.4,
          "light_volume": 0.3, "angle": 0.6, "view": 0.5, "framing": 0.4, "color": 0.5}
# the parts by group, for the card and for the switches that turn a group off
GROUPS = {"looks": ("build", "skin", "hair", "eyes", "face", "makeup", "accessory", "mouth", "gaze"), "job": ("job", "fx"),
          "light": ("natural", "light_quality", "light_mood", "light_support", "light_volume"), "camera": ("angle", "view", "framing"),
          "color": ("color",)}
PEOPLE_PARTS = GROUPS["looks"] + ("job", "fx", "outfit")
SUBJECT_CASTS = ("furry", "kemono", "mythic", "monster", "synth", "nonhuman")  # their subject says if they are a woman or a man

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

# NSFW ideas never carry these, whatever a file says.
MINOR = re.compile(r"\b(child|children|kid|kids|loli|lolicon|shota|shotacon|underage|minor|teen|teenager|"
                   r"preteen|toddler|infant|schoolgirl|schoolboy|cub|young girl|young boy|little girl|little boy|chibi)\b",
                   re.IGNORECASE)

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
    "kinks": [],             # NSFW layers on top of the scene, see kinks.py; empty: none
    "acts": [],              # families of explicit acts, see acts.py; empty: any
    "hide": [],              # groups of parts left out of ideas, see GROUPS
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
    for key in ("enabled", "allow_nsfw", "use_tipo", "anatomy"):
        out[key] = bool(out[key])
    try:
        out["interval_minutes"] = max(5, min(30, int(out["interval_minutes"])))
    except (TypeError, ValueError):
        out["interval_minutes"] = DEFAULT_STATE["interval_minutes"]
    out["themes"] = _names(out["themes"])[:100]
    out["casts"] = _names(out["casts"], CASTS)
    out["ratings"] = _names(out["ratings"], RATINGS)
    out["kinks"] = _names(out["kinks"], kinklib.KINKS)
    out["acts"] = _names(out["acts"], actlib.FAMILIES)
    out["hide"] = _names(out["hide"], GROUPS)
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


@functools.lru_cache(maxsize=None)
def _minor(item):
    return bool(MINOR.search(item))


def _clean(items, nsfw):
    """The entries of a list, trimmed; NSFW ones without a minor-related word."""
    if not isinstance(items, list):
        return []
    out = [item.strip() if isinstance(item, str) else str(item).strip() for item in items]
    return [item for item in out if item and not (nsfw and _minor(item))]


def _keyed(value, nsfw):
    """A list, or lists by cast or alias, as {cast or alias or "*": [entries]}; {} when empty."""
    if isinstance(value, dict):
        out = {str(k): _clean(v, nsfw) for k, v in value.items()}
        return {k: v for k, v in out.items() if v}
    clean = _clean(value, nsfw)
    return {"*": clean} if clean else {}


def _for_cast(lists, cast):
    """The entries a cast gets: its own and those of the aliases it is part of; everyone's when
    nothing names it."""
    out = list(lists.get(cast, []))
    for alias in ("pair", "groups", "solo", "people"):
        if alias in lists and cast in ALIASES[alias]:
            out += lists[alias]
    return list(dict.fromkeys(out)) if out else lists.get("*", [])


def _with_template(template, raw):
    """A scene on top of its template: the scene's lists add to the template's."""
    out = dict(template)
    for key, value in raw.items():
        shared = out.get(key)
        if key in LISTS.values() or key == "subjects":
            if isinstance(shared, list) and isinstance(value, list):
                value = shared + value
            elif isinstance(shared, dict) or isinstance(value, dict):
                a = shared if isinstance(shared, dict) else ({"*": shared} if shared else {})
                b = value if isinstance(value, dict) else {"*": value}
                value = {k: list(a.get(k, [])) + list(b.get(k, [])) for k in dict.fromkeys([*a, *b])}
        out[key] = value
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
    templates = data.get("templates") if isinstance(data.get("templates"), dict) else {}
    out = []
    for i, raw in enumerate(raw_scenes):
        if not isinstance(raw, dict):
            continue
        uses = raw.get("use") if isinstance(raw.get("use"), list) else [raw.get("use")]
        shared = {}
        for name in uses:  # what several scenes share, written once
            if isinstance(name, str) and isinstance(templates.get(name), dict):
                shared = _with_template(shared, templates[name])
        raw = _with_template(shared, raw) if shared else raw
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
                if cast not in CASTS or (name in ALIASES and cast in subjects) or (cast in NSFW_ONLY and not nsfw) \
                        or (cast in SFW_ONLY and nsfw):
                    continue
                clean = _clean(items, nsfw)
                # an empty subject is a cast that needs no words of its own (the cast tags say it all)
                if clean or cast == "none" or (isinstance(items, list) and all(not str(x).strip() for x in items)):
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
            "wear": _wear(raw.get("wear") or data.get("wear"), nsfw),
            "custom": custom,
        })
    return out


def _wear(value, nsfw):
    """What people wear in a scene: {"f": [...], "m": [...]} for one woman and one man."""
    value = value if isinstance(value, dict) else {}
    return {k: _clean(value.get(k), nsfw) for k in ("f", "m")}


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
        "acts": [[k, v] for k, v in actlib.FAMILIES.items()],
        **_act_tables(scenes),
        "styles": [[family, len(tags)] for family, tags in vocab.styles().items()],
        **_index(scenes, themes),
    }


def _index(scenes, themes):
    """What the card counts with, small: scenes alike in theme, casts, level and group sizes share a row.
    index: [theme index, cast set index, level, size set index, how many scenes]."""
    castsets, sizesets, rows = {}, {}, {}
    for s in scenes:
        cs = castsets.setdefault(tuple(s["casts"]), len(castsets))
        ss = sizesets.setdefault(tuple(s["sizes"]), len(sizesets))
        key = (themes.index(s["theme"]), cs, s["rating"], ss)
        rows[key] = rows.get(key, 0) + 1
    return {"castsets": [list(c) for c in castsets], "sizesets": [list(z) for z in sizesets],
            "index": [[*k, n] for k, n in rows.items()]}


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


def _act_families(scene, cast):
    """The act families a scene has for a cast, a bare position counting as vaginal or anal."""
    cache = scene.setdefault("_acts", {})
    if cast not in cache:
        fams = set()
        for a in _for_cast(scene["lists"]["action"], cast):
            fam, generic = actlib.families(a, cast)
            fams |= fam
            if generic:
                fams |= {"anal", "vaginal"} if cast in actlib.VAGINAL_CASTS else {"anal"}
        cache[cast] = fams
    return cache[cast]


def _kink_goes(entry, fams, cast):
    """Whether a kink entry has an act to go with among these families."""
    need = actlib._needs(entry)
    if not need or "own" in need:
        return True
    have = set(fams) | ({"pen"} if fams & {"anal", "vaginal"} else set())
    return need <= have


def _wanted(have, acts):
    """The families of `have` the chosen acts let through; oral brings its throat along."""
    out = have & set(acts)
    if "oral" in out and "throat" in have:
        out.add("throat")
    return out


def _act_tables(scenes):
    """For the card: which casts have acts of each family, and which kinks go with which family."""
    act_casts = {f: set() for f in actlib.FAMILIES}
    have = {}
    for s in scenes:
        if s["rating"] == "explicit":
            for c in s["casts"]:
                fams = _act_families(s, c)
                have.setdefault(c, set()).update(fams)
                for f in fams & set(actlib.FAMILIES):
                    act_casts[f].add(c)
    kink_acts = {k: {f: [c for c in act_casts[f] if any(_kink_goes(e, _wanted(have[c], {f}), c)
                                                         for e in kinklib.entries(k, "explicit", c, ALIASES))]
                     for f in actlib.FAMILIES} for k in kinklib.KINKS}
    return {"act_casts": {f: sorted(v) for f, v in act_casts.items()}, "kink_acts": kink_acts}


def _cast_fits(s, c, st, chosen):
    """A cast of a scene, with the chosen kinks and acts."""
    acts = set(st["acts"]) if st["allow_nsfw"] else set()
    fams = _wanted(_act_families(s, c), acts) if acts else None
    if acts and not fams:
        return False
    if not st["kinks"]:
        return True
    for k in chosen:
        for e in kinklib.entries(k, s["rating"], c, ALIASES):
            if fams is None or _kink_goes(e, fams, c):
                return True
    return False


def _matching(st):
    ratings = set(_ratings_on(st))
    themes, casts = set(st["themes"]), set(st["casts"])
    acts = st["acts"] and st["allow_nsfw"]
    out = []
    for s in load_scenes():
        if s["rating"] not in ratings or (themes and s["theme"] not in themes):
            continue
        if acts and s["rating"] != "explicit":
            continue  # an act is an explicit idea
        chosen = _kinks_for(s, st)
        if st["kinks"] and not chosen:
            continue  # with a kink chosen, every idea carries one
        usable = [c for c in s["casts"] if (not casts or c in casts) and _sizes(s, c, st["sizes"]) and _cast_fits(s, c, st, chosen)]
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


ORDER_DRAWN = ("subject", "time", "job", "outfit", "build", "skin", "body", "hair", "eyes", "face", "makeup", "accessory", "fx", "kink",
               "action", "gesture", "expression", "mouth", "gaze", "detail", "setting", "lighting", "natural", "light_quality", "light_mood",
               "light_support", "light_volume", "camera", "angle", "view", "framing", "color", "style")
# rolling a part draws again what follows from it
DEPENDS = {"job": ("outfit", "accessory", "fx"), "time": ("natural",),
           "subject": ("outfit", "build", "skin", "body", "hair", "eyes", "face", "makeup", "accessory")}
# what the hour and the sky can contradict (see when.py)
UNDER_SKY = ("action", "kink", "gesture", "detail", "setting", "lighting", "light_volume", "light_mood", "accessory", "outfit")


LOOK_FILLED = ("job", "outfit", "build", "skin", "hair", "eyes", "face", "makeup", "accessory", "fx", "mouth", "gaze", "natural",
               "light_quality", "light_mood", "light_support", "light_volume", "camera", "angle", "view", "framing", "color")


def _outfits(scene, who, f, m, job, rng):
    """What the people of an idea wear: the scene's clothes (or a job's), put together for the cast."""
    level = scene["rating"]
    wf, wm = scene["wear"]["f"], scene["wear"]["m"]
    if job in looks.JOBS and level in ("sfw", "suggestive"):
        _t, jf, jm, _p, _fx = looks.JOBS[job]
        wf, wm = [jf], [jm]
        if level == "suggestive":
            wf = [f"{jf}, {t}" for t in rng.sample(looks.TEASE, 3)]
            wm = [f"{jm}, {t}" for t in rng.sample(looks.TEASE, 3)]
    if level == "nude":
        return ["nude"]
    if not wf and not wm:
        return []
    if level == "explicit":
        tease = (wf if f else []) + (wm if m else []) or wf + wm
        return ["completely nude", "completely nude"] + [f"partially undressed, {t}" for t in tease[:3]] + [f"clothes pull, {t}" for t in tease[3:5]]
    pattern = {"1girl": "f", "futa": "f", "1boy": "m", "1girl1boy": "fm", "futa_boy": "fm", "human_furry": "fm", "2girls": "ff",
               "futa_girl": "ff", "2boys": "mm", "girls": "f", "boys": "m", "harem": "mf", "reverse": "fm", "mixed": "fm"}.get(who)
    if pattern is None:  # a being: by what its subject says
        pattern = "f" if f and not m else "m" if m and not f else "f" if rng.random() < 0.5 else "m"
    lists = {"f": wf or wm, "m": wm or wf}
    out = []
    for _ in range(8):
        picked = []
        for sex in pattern:
            choices = [x for x in lists[sex] if x not in picked] or lists[sex]
            picked.append(rng.choice(choices))
        out.append(", ".join(dict.fromkeys(", ".join(picked).split(", "))))
    return list(dict.fromkeys(out))


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
    for part in DEPENDS.get(roll, ()):
        keep.pop(part, None)

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
        if who == "human_furry":  # who does what to whom, when it comes to that
            how = rng.choice(["human on furry", "furry on human"]) if scene["rating"] == "explicit" else "human with furry"
            cast_tags = f"{cast_tags}, {how}"
        if st["styles"]:  # style families chosen on the card win over the scene's own
            fams = vocab.styles()
            pools["style"] = list(dict.fromkeys(t for f in st["styles"] for t in fams.get(f, [])))
        if scene["rating"] != "sfw":
            pools["style"] = [x for x in pools["style"] if not MINOR.search(x)]
        parts, sky = {}, (None, None)
        explicit = scene["rating"] == "explicit"
        wanted = set(st["acts"]) if st["allow_nsfw"] else set()

        hidden = {p for g in st["hide"] for p in GROUPS[g]}
        level = scene["rating"]

        def sexes():
            """(women, men) in the idea, from the cast or, for beings, from their subject."""
            if who in SUBJECT_CASTS:
                return kinklib._sexes(who, parts.get("subject", ""))
            return who in kinklib.FEMALE, who in kinklib.MALE

        def fill(slot):
            """The entries of a part the scene leaves to Muse: looks, job, wear, light, camera, colour."""
            own = pools.get(slot) or []
            if slot in hidden or (slot in PEOPLE_PARTS and (who in SFW_ONLY or who == "any")):  # "any": a scene's own subject, maybe not a person
                return []
            f, m = sexes()
            if slot == "job":
                return own or (looks.jobs_for(scene["theme"]) if level in ("sfw", "suggestive") else [])
            if slot == "outfit":
                return _outfits(scene, who, f, m, parts.get("job", ""), rng)
            if slot in GROUPS["looks"]:
                if own:
                    return own
                subject = parts.get("subject", "").lower()
                if slot in ("hair", "eyes", "skin") and slot.rstrip("s") in subject:
                    return []  # the subject says it already (red eyes, grey skin)
                if slot == "skin" and who in kinklib.ANTHROS:
                    return []  # fur, scales or feathers: in the subject
                if slot == "makeup" and not f:
                    return looks.MAKEUP["m"] if rng.random() < 0.3 else []
                return looks.pools(f, m, people or (2 if who in ALIASES["pair"] else 1), rng)[slot]
            if slot == "accessory" and parts.get("job"):
                return [looks.JOBS[parts["job"]][3]] if parts["job"] in looks.JOBS and looks.JOBS[parts["job"]][3] else own
            if slot == "fx":
                job = looks.JOBS.get(parts.get("job", ""))
                return [job[4]] if job and job[4] else own
            if slot == "natural":
                if own or sky == (None, None):
                    return own
                out = list(looks.NATURAL.get(sky[0], [])) + (list(looks.NATURAL_SKY.get(sky[1], [])) if sky[0] != "night" else [])
                if "window" in parts.get("setting", "") or "indoors" in parts.get("setting", ""):
                    out.append("window light")
                return out
            defaults = {"light_quality": looks.LIGHT_QUALITY, "light_mood": looks.LIGHT_MOOD, "light_support": looks.LIGHT_SUPPORT,
                        "light_volume": looks.LIGHT_VOLUME, "angle": looks.ANGLE, "framing": looks.FRAMING, "color": looks.COLOR,
                        "view": looks.VIEW if who not in SFW_ONLY else [v for v in looks.VIEW if v not in ("pov", "selfie", "over-the-shoulder shot")]}
            if slot in defaults:
                return own or defaults[slot]
            if slot == "camera":
                return own or looks.SHOT
            return own

        def acts_pool():
            pool = [a for a in pools["action"] if not blocked(a)]
            return [a for a in pool if actlib.in_family(a, who, wanted)] if wanted else pool
        # drawn in this order: the body follows the subject (a male wolf, a female android), the pose
        # follows the action (no "lying on back" for someone riding); the prompt keeps the order of SLOTS
        for slot in ORDER_DRAWN:
            if slot in LOOK_FILLED:
                pools[slot] = fill(slot)
            if slot == "body":
                pools["body"] = kinklib.body(scene["rating"], who, parts["subject"], scene["theme"], rng) if st["anatomy"] else []
            if slot == "gesture":
                pools["gesture"] = list(dict.fromkeys(pools["gesture"] + _library_poses(scene, who, parts)))
            if slot in keep:
                parts[slot] = keep[slot]
                if slot == "time":
                    sky = when.parse(keep[slot])
                continue
            pool = [x for x in pools[slot] if not blocked(x)]
            if slot == "time":  # an hour and a sky the locked parts can live with
                fit = [x for x in pool if all(when.fits(v, *when.parse(x)) for k, v in keep.items() if k in UNDER_SKY)]
                pool = fit or pool
            elif slot in UNDER_SKY and sky != (None, None):
                fit = [x for x in pool if when.fits(x, *sky)]
                pool = fit if fit or slot != "setting" else pool
            if explicit and slot == "kink" and pool:  # a kink with an act to go with
                doing = [keep["action"]] if "action" in keep else acts_pool()
                fit = [k for k in pool if "own" in actlib.needs(k) or any(actlib.fits(k, a, who, wanted) for a in doing)]
                pool = fit or pool
            if explicit and slot == "action":
                if wanted:
                    pool = [a for a in pool if actlib.in_family(a, who, wanted)]
                if parts.get("kink"):
                    pool = [] if "own" in actlib.needs(parts["kink"]) else [a for a in pool if actlib.fits(parts["kink"], a, who, wanted)]
            if slot == roll and len(pool) > 1:
                pool = [x for x in pool if x != current]
            if slot != roll and slot in CHANCE and rng.random() >= CHANCE[slot]:
                pool = []
            parts[slot] = rng.choice(pool) if pool else ""
            if explicit and slot == "action" and wanted and parts["action"]:
                parts["action"] = actlib.as_family(parts["action"], who, wanted, rng, parts.get("kink", ""))
            if slot == "time":
                sky = when.parse(parts["time"])
        if pools["subject"] != [""] and not parts["subject"]:
            continue  # the blacklist took every subject of this scene

        nsfw = scene["rating"] != "sfw"
        nsfw_tags = CASTS[who][2]
        front = [cast_tags] + ([nsfw_tags, "mature"] if nsfw and who not in SFW_ONLY else [])

        seen, pieces = set(), []
        for chunk in front + [parts[s] for s in SLOTS]:
            for piece in text.split(chunk):
                if not blocked(piece) and text.key(piece) not in seen:
                    seen.add(text.key(piece))
                    pieces.append(piece)

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
