"""What Muse takes from the Vault's library: poses and styles.

The library is the one vocabulary of the extension: Muse reads its pose and style categories
(the default library's, with your own additions) instead of keeping lists of its own, so a
tag added in the Vault tab can turn up on Muse's card. A group's name says what its tags
are: "Seated" poses are for someone sitting, "Female" ones for a woman, "Hands" ones need
free hands; a style group is a style family on the card's Style filter.
"""

from __future__ import annotations

import re

from . import store

_cache = {"key": None}

POSTURES = (  # first match wins
    ("lying", r"recline|lying|floor|bed"),
    ("kneeling", r"kneel|crouch|all fours"),
    ("sitting", r"seated|sitting"),
    ("standing", r"standing|leaning|walk|run|jump|dance|stretch"),
)
HANDS = r"hands|arms|point|signal|touch|toys|face & hair"
FEMALE_WORDS = r"breast|pussy|clit|labia|panties|skirt|bra\b|nipple|curtsy"
MALE_WORDS = r"penis|shaft|erect|balls|waistband|flexing"
SKIP = r"object use|mouth|pacing|afterglow|camera|framing|kiss|oral|manual|family|toys|fantasy adult|body notes"
# a pose with furniture in it would fight the scene's own place ("sitting backwards, chair" on a beach)
PROPS = r"\b(chair|bed|bar|shelf|windowsill|desk|counter|door|wall|stairs|table|sofa|couch|pillow|sheets?)\b"
# what belongs to explicit ideas, not nude ones
ACTS = r"pussy|penis|erection|masturbat|fingering|labia|dildo|vibrator|grab|stroking|spread"


def _merged():
    """{category: {group: [tags]}}: the default library, with what your library adds to it."""
    lib = store.default_library()
    for cat, groups in store.library().items():
        mine = lib.setdefault(cat, {})
        for group, tags in groups.items():
            mine[group] = list(dict.fromkeys(mine.get(group, []) + tags))
    return lib


def _build():
    lib = _merged()
    poses, styles = [], {}
    for cat, groups in lib.items():
        low = cat.lower()
        if "style" in low and "medium" in low or re.search(r"\bstyles?\b", low):
            for group, tags in groups.items():
                if tags:
                    styles.setdefault(group, list(tags))
        if "pose" not in low:
            continue
        nsfw = "nsfw" in low
        for group, tags in groups.items():
            g = group.lower()
            if re.search(SKIP, g):
                continue
            posture = next((p for p, rx in POSTURES if re.search(rx, g)), "any")
            gender = "f" if re.search(r"\bfemale|\bwoman|\bwomen|\bher\b", g) else "m" if re.search(r"\bmale|\bman\b|\bmen\b", g) else ""
            who = "pair" if re.search(r"pair|partner|couple|with another", g) else "solo"
            for tag in tags:
                if re.search(PROPS, tag):
                    continue
                # a tag can say whose body it is even in a group that does not
                own = "f" if re.search(FEMALE_WORDS, tag) else "m" if re.search(MALE_WORDS, tag) else gender
                poses.append({"tag": tag, "posture": posture, "hands": bool(re.search(HANDS, g)), "gender": own,
                              "nsfw": nsfw, "who": who, "act": bool(re.search(ACTS, tag))})
    return {"poses": poses, "styles": styles}


def data():
    key = (store.revision(),)
    if _cache["key"] != key:
        _cache.update(key=key, **_build())
    return _cache


def styles():
    return data()["styles"]


# what an action says about the body: sitting, lying, kneeling, standing; and busy hands
ACTION_POSTURE = (  # first match wins: "kneeling on bed" kneels, "sitting on bed" sits, "lying on sofa" lies
    ("lying", r"\blying\b|\bon (?:back|side|stomach)\b|sleeping|napping"),
    ("kneeling", r"kneel|all fours|crouch|squat|crawl|doggystyle|presenting|seiza"),
    ("sitting", r"\bsit|seated|straddl|riding|cowgirl|\blap\b|lotus|on (?:chair|bench|stool|ledge|sofa|couch|swing|armchair|throne|steps)\b"),
    ("lying", r"propped|reclin|sprawl|sleeping|napping|floating|missionary|mating press|"
              r"prone bone|spooning|piledriver|\b69\b|legs up|on (?:bed|mattress|futon|sheets|rug|grass|sand|blanket)\b"),
    ("standing", r"stand|walk|run|lean|danc|crossing|waiting|stretch|posing|jump|against\b"),
)
BUSY_HANDS = r"holding|reading|writing|playing|carrying|cooking|pouring|drinking|eating|using|painting|typing|brushing|fixing|" \
             r"repairing|kneading|picking|sketching|stirring|hands on|gripping|fingering|stroking|masturbat|with both hands|sharpening|" \
             r"lighting|counting|polishing|singing into|taping|wiping|watering|smelling|shaping|throwing|carving|developing"


def action_posture(action):
    low = (action or "").lower()
    return next((p for p, rx in ACTION_POSTURE if re.search(rx, low)), ""), bool(re.search(BUSY_HANDS, low))


def poses_for(level, who, gender, action):
    """Poses of the library that go with an idea: its level, one or two people, a woman or a man,
    and the body its action already gives (no 'lying on back' for someone riding)."""
    posture, busy = action_posture(action)
    nsfw = level != "sfw"
    out = []
    for p in data()["poses"]:
        if p["who"] != who or (p["nsfw"] and not nsfw):
            continue
        if level == "suggestive" and p["nsfw"]:
            continue  # the NSFW pose groups are for nude and explicit ideas
        if level in ("nude", "explicit") and not p["nsfw"]:
            continue  # and those get nothing else: no parade rest on a nude
        if level == "nude" and p["act"]:
            continue
        if p["gender"] and gender and p["gender"] != gender:
            continue
        if p["gender"] and not gender:
            continue
        if busy and p["hands"]:
            continue
        if p["posture"] != "any" and posture and p["posture"] != posture:
            continue
        if p["posture"] != "any" and not posture and p["posture"] != "standing":
            continue
        out.append(p["tag"])
    return out
