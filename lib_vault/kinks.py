"""Muse's NSFW layers: anatomy tags and kinks, added on top of a scene's own parts.

A kink is a category the card's Kink filter turns on. Its entries are by level (suggestive,
nude, explicit) and by cast, with the aliases of muse.ALIASES (solo, pair, groups, people)
standing for several casts. A kink with themes only joins scenes of those themes: tentacles
belong to a wizard's tower, not to an office. Everything here is for adults; muse.py still
drops minor-related words and sends its guard negatives.
"""

from __future__ import annotations

KINKS = {
    "bdsm": {
        "label": "BDSM",
        "suggestive": {
            "solo": ["leather collar", "holding a riding crop", "blindfold pushed up on the forehead", "handcuffs dangling from a finger"],
            "pair": ["one blindfolded, the other teasing", "wrists loosely tied with a silk scarf", "holding the other by a leash"],
            "groups": ["one blindfolded, the others teasing", "everyone in leather collars"],
        },
        "nude": {
            "solo": ["shibari, red rope harness", "leather collar and cuffs", "blindfolded, wrists tied behind the back"],
            "pair": ["one tied in red rope, the other admiring the knots", "collar and leash", "blindfold and silk ties"],
            "groups": ["one tied in rope, the others watching", "matching leather collars"],
        },
        "explicit": {
            "solo": ["bound with rope, spread legs", "spreader bar, blindfolded", "ball gag, wrists cuffed"],
            "pair": ["bondage, tied to the bed, sex", "spanking, red handprint", "blindfolded, wrists tied, sex", "collar and leash, from behind",
                     "hot wax dripping on the skin", "dominant and submissive, kneeling"],
            "groups": ["one tied up, the others taking turns", "dominatrix with a riding crop, the others kneeling", "rope bondage, group sex"],
        },
    },
    "toys": {
        "label": "Toys",
        "suggestive": {"people": ["holding a vibrator, teasing", "sex toy on the bed", "handcuffs and a feather on the sheets"]},
        "nude": {"people": ["holding a dildo, smiling", "vibrator in hand", "toys laid out on the bed"]},
        "explicit": {
            "1girl": ["dildo", "magic wand vibrator", "anal beads", "remote egg vibrator"],
            "1boy": ["onahole", "prostate massager", "cock ring"],
            "1girl1boy": ["vibrator on her clit during sex", "remote vibrator, he holds the remote", "cock ring"],
            "2girls": ["strap-on sex", "double-ended dildo", "magic wand vibrator"],
            "2boys": ["dildo", "anal beads", "cock ring"],
            "groups": ["strap-on", "toys everywhere", "vibrators"],
            "solo": ["dildo", "vibrator"],
        },
    },
    "fluids": {
        "label": "Fluids",
        "suggestive": {"people": ["wet lips, saliva", "sweat glistening", "drool"]},
        "nude": {"people": ["sweat", "body oil glistening", "wet skin, oiled"]},
        "explicit": {
            "1girl": ["pussy juice", "squirting", "dripping wet"],
            "1boy": ["ejaculation", "cum on stomach", "precum"],
            "1girl1boy": ["cum on body", "creampie", "cum on face", "cum string", "squirting"],
            "2girls": ["squirting", "pussy juice", "saliva trail"],
            "2boys": ["cum on body", "cum on stomach", "cum in mouth"],
            "girls": ["squirting", "pussy juice everywhere"],
            "boys": ["cum on body", "bukkake"],
            "harem": ["cum on the girls", "creampie, cum dripping"],
            "reverse": ["bukkake", "cum on body", "creampie"],
            "mixed": ["cum everywhere", "sweat and cum"],
            "solo": ["sweat", "dripping wet"],
        },
    },
    "latex": {
        "label": "Latex & fetish wear",
        "suggestive": {"people": ["black latex catsuit", "pvc corset, thigh-high boots", "leather harness", "fishnet bodystocking"]},
        "nude": {"people": ["leather harness only", "latex gloves and stockings only", "fishnet bodystocking"]},
        "explicit": {"people": ["latex catsuit, crotch zipper open", "leather harness", "latex gloves and stockings", "pvc boots"]},
    },
    "marks": {
        "label": "Bites & marks",
        "suggestive": {"people": ["hickeys on the neck", "lipstick marks on the skin"]},
        "nude": {"people": ["hickeys", "bite marks on the shoulder", "scratch marks on the back"]},
        "explicit": {"people": ["bite marks", "scratch marks on the back", "red handprint on the hip", "hickeys everywhere"]},
    },
    "tentacles": {
        "label": "Tentacles",
        "themes": ["Fantasy", "Creature", "Horror", "Sci-fi", "Myth"],
        "suggestive": {"people": ["tentacles curling around the ankles", "tentacles tugging at the clothes", "tentacles rising from the floor"]},
        "nude": {"people": ["tentacles wrapped around the body", "tentacles coiling around the thighs", "suspended by tentacles"]},
        "explicit": {"people": ["tentacle sex", "tentacles wrapped around the limbs, tentacle penetration", "suspended in the air by tentacles",
                                "tentacles in every hand"]},
    },
    "slime": {
        "label": "Slime",
        "themes": ["Fantasy", "Creature", "Horror", "Sci-fi"],
        "suggestive": {"people": ["translucent slime dripping on the clothes", "slime melting the clothes"]},
        "nude": {"people": ["covered in translucent slime", "slime pooling on the skin"]},
        "explicit": {"people": ["slime sex, engulfed in slime", "slime creature wrapped around the body", "dripping with slime"]},
    },
    "blood": {
        "label": "Blood & bites",
        "themes": ["Horror", "Fantasy", "Myth"],
        "suggestive": {"people": ["vampire bite on the neck, a drop of blood", "blood on the lips"]},
        "nude": {"people": ["vampire bite marks, a trickle of blood", "blood on the lips, pale skin"]},
        "explicit": {"people": ["vampire biting the neck during sex", "blood on the lips, kissing", "bite marks, a trickle of blood"]},
    },
}

FEMALE = ("1girl", "1girl1boy", "2girls", "girls", "harem", "reverse", "mixed")
MALE = ("1boy", "1girl1boy", "2boys", "boys", "harem", "reverse", "mixed")
ANATOMY = {
    "suggestive": {"f": ["cleavage"], "m": ["bulge"]},
    "nude": {"f": ["nipples", "pussy"], "m": ["penis"]},
    "explicit": {"f": ["nipples", "pussy"], "m": ["penis", "erection"]},
}


def themed(kink, theme):
    themes = KINKS[kink].get("themes")
    return themes is None or theme in themes


def entries(kink, level, cast, aliases):
    """What a kink gives a cast at a level: its own entries, else those of an alias it is in."""
    lists = KINKS[kink].get(level) or {}
    if cast in lists:
        return lists[cast]
    for alias in ("pair", "groups", "solo", "people"):
        if alias in lists and cast in aliases[alias]:
            return lists[alias]
    return []


def anatomy(level, cast, subject):
    """The anatomy tags of an idea, from who is in it. Furry and non-human ones say it in their subject."""
    tags = ANATOMY.get(level)
    if not tags:
        return []
    low = f" {subject.lower()} "
    female = cast in FEMALE or (cast in ("furry", "nonhuman") and any(w in low for w in (" female", "1girl", " girl", " woman")))
    male = cast in MALE or (cast in ("furry", "nonhuman") and any(w in low for w in (" male", "1boy", " man,", " man ")))
    return (tags["f"] if female else []) + (tags["m"] if male else [])
