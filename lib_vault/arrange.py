"""Arrange a prompt: every tag in its place, the usual order of a Danbooru-style prompt.

What a tag is comes from the library first (its category says it: hair, lighting, camera...)
and from the Danbooru vocabulary of the WD14 model (character, artist...). A tag neither
knows stays next to the tag it followed. No model runs: it is instant, and Qwen's
"Arrange tags" is there for what this cannot know.

BREAK splits the prompt into parts that are arranged one by one; LoRAs, embeddings and
wildcards go to the end of their part; sentences after the tags.
"""

from __future__ import annotations

import re

from . import store, text

# the order of a prompt
ORDER = ["quality", "subject", "who", "body", "face", "expression", "attire", "accessories", "pose",
         "place", "time", "light", "colour", "camera", "style", "other"]
RANK = {name: i for i, name in enumerate(ORDER)}

# a library category's name -> where its tags go; the first rule that matches wins
CATEGORY_RULES = [
    (r"negative", None),
    (r"anatomy", "body"),
    (r"furry|anthro", "who"),
    (r"kink|fetish", "pose"),
    (r"\bpositions?\b|\bsex\b|\bact\b", "pose"),
    (r"tease|lingerie|cloth|attire|outfit|wear", "attire"),
    (r"pose|gesture|interaction|staging", "pose"),
    (r"quality|technical", "quality"),
    (r"subject|focus", "subject"),
    (r"body|skin|build", "body"),
    (r"face|hair|feature", "face"),
    (r"expression|mood|emotion", "expression"),
    (r"accessor|prop", "accessories"),
    (r"beings|roles?\b|creature|profession|character", "who"),
    (r"environment|setting|location|background|place", "place"),
    (r"time|weather|atmosphere|season", "time"),
    (r"light", "light"),
    (r"colou?r|grade|palette", "colour"),
    (r"camera|composition|shot|framing|lens", "camera"),
    (r"style|medium|\bart\b", "style"),
]
# groups that do not belong where their category does (body notes among the poses...)
GROUP_RULES = [(r"body notes|skin state|marks|wetness", "body"), (r"light for", "light")]

# for tags no library knows: words that give them away
GUESS = [
    ("subject", r"^(\d\+?(girl|boy|other)s?|solo|no humans|multiple (girls|boys)|male focus|female focus|hetero|yuri|yaoi)$"),
    ("quality", r"masterpiece|best quality|high quality|absurdres|highres|score_\d|very aesthetic|newest|^(amazing|great|good) quality"),
    ("face", r"\b(hair|eyes|bangs|ponytail|braid|twintails|ahoge|lips|eyelashes|freckles|beard|stubble)\b"),
    ("expression", r"\b(smile|smiling|grin|blush|expression|crying|tears|frown|smirk|pout|laughing|open mouth|closed eyes)\b"),
    ("attire", r"\b(dress|gown|shirt|blouse|skirt|jacket|coat|blazer|suit|tie|trousers|pants|jeans|shorts|uniform|kimono|yukata|bikini|swimsuit|lingerie|bra|panties|thighhighs|stockings|boots|shoes|heels|sneakers|gloves|hoodie|sweater|cardigan|apron|robe|towel|nude|naked)\b"),
    ("accessories", r"\b(earrings|necklace|glasses|hat|ribbon|bow|choker|bracelet|ring|holding)\b"),
    ("pose", r"\b(standing|sitting|lying|kneeling|walking|running|squatting|leaning|stride|crossing|reading|holding|arms|hand|hands|legs|looking|pose|sex|missionary|cowgirl|doggystyle|kiss|kissing|hug)\b"),
    ("place", r"\b(indoors|outdoors|room|street|city|forest|beach|sky|background|backdrop|studio|cyclorama|interior|bedroom|bathroom|kitchen|office|cafe|bar|alley|park|field|lake|ocean|mountain|rooftop|station|library|hallway|corridor)\b"),
    ("time", r"\b(night|day|sunset|sunrise|dusk|dawn|rain|snow|fog|mist|cloudy|winter|summer|autumn|spring)\b"),
    ("light", r"\b(light|lighting|lit|shadow|shadows|glow|backlight|bokeh|lens flare|sunbeam)\b"),
    ("camera", r"\b(shot|angle|view|close-up|closeup|full body|upper body|cowboy shot|from (above|below|side|behind)|pov|perspective|depth of field|wide shot|wide angle|telephoto|\d+mm)\b"),
    ("style", r"\b(style|illustration|photo|photograph|photography|photorealistic|painting|anime|realistic|sketch|render|art|film|cinematic|lineart)\b"),
]
DANBOORU = {"character": "who", "copyright": "who", "artist": "style", "meta": "other"}
# the parts of a Muse idea -> where their tags go, for tags neither the library nor a guess knows
MUSE_PARTS = {"body": "body", "expression": "expression", "gesture": "pose", "action": "pose", "kink": "pose", "detail": "place", "setting": "place",
              "lighting": "light", "camera": "camera", "style": "style"}

_cache = {"key": None, "map": {}}


def _rank(rules, name):
    for pattern, slot in rules:
        if re.search(pattern, name.lower()):
            return slot
    return None


def _known():
    """key(tag) -> rank, from the library and the Danbooru vocabulary."""
    from . import wd14

    try:
        vocab = wd14.vocabulary()
    except Exception:
        vocab = []
    cache_key = (store.revision(), id(vocab))
    if _cache["key"] != cache_key:
        found = {}
        for tag, cat, _count in vocab:
            if cat in DANBOORU:
                found.setdefault(text.key(tag), RANK[DANBOORU[cat]])
        lib = {}
        for cat, groups in store.library().items():
            slot = _rank(CATEGORY_RULES, cat)
            if slot is None:
                continue
            for group, tags in groups.items():
                rank = RANK[_rank(GROUP_RULES, group) or slot]
                for tag in tags:
                    lib.setdefault(text.key(tag), rank)
        found.update(lib)  # the library knows best
        _cache.update(key=cache_key, map=found)
    return _cache["map"]


def _guess(k):
    for slot, pattern in GUESS:
        if re.search(pattern, k):
            return RANK[slot]
    return None


def _is_sentence(piece):
    """Prose, not a tag. Tags of a few words ("eating alone at a long table") are tags."""
    return not text._WEIGHT.match(piece) and (piece.rstrip().endswith(".") or len(piece.split()) > 9)


def _arrange_part(pieces, known, hints):
    tags, specials, sentences = [], [], []
    for p in pieces:
        if p.startswith("<") or p.startswith("__"):
            specials.append(p)
        elif _is_sentence(p):
            sentences.append(p)
        else:
            tags.append(p)
    # duplicates: the first one stays, unless a later one carries a weight
    best = {}
    for p in tags:
        k = text.key(p)
        if k not in best or ("(" in p and "(" not in best[k]):
            best[k] = p
    order, seen = [], set()
    for p in tags:
        k = text.key(p)
        if k not in seen:
            seen.add(k)
            order.append(best[k])
    ranks, last = [], RANK["subject"]
    for p in order:
        k = text.key(p)
        r = known.get(k)
        if r is None:
            r = hints.get(k)
        if r is None:
            r = _guess(k)
        if r is None:
            r = last  # unknown: stays with the tag it followed
        ranks.append(r)
        last = r
    arranged = [p for _, _, p in sorted(zip(ranks, range(len(order)), order))]
    return arranged + sentences + specials, len(tags) - len(order)


def arrange(prompt, parts=None):
    """(arranged prompt, note). parts: the parts of a Muse idea, [{"slot", "value"}], which say
    what their tags are when nothing else does."""
    prompt = (prompt or "").strip()
    if not prompt:
        return "", "The prompt is empty."
    known = _known()
    hints = {}
    for part in parts or []:
        slot = MUSE_PARTS.get(str(part.get("slot") or "")) if isinstance(part, dict) else None
        if slot:
            for piece in text.split(str(part.get("value") or "")):
                hints.setdefault(text.key(piece), RANK[slot])
    parts, current = [], []
    for p in text.split(prompt):
        if p == "BREAK":
            parts.append(current)
            current = []
        else:
            current.append(p)
    parts.append(current)
    out, dropped = [], 0
    for part in parts:
        arranged, d = _arrange_part(part, known, hints)
        dropped += d
        out.append(text.join(arranged))
    result = ", BREAK, ".join(o for o in out if o) if len(parts) > 1 else out[0]
    note = "Arranged" + (f", {dropped} duplicate{'s' if dropped > 1 else ''} removed" if dropped else "")
    return result, note
