"""Muse's NSFW layers: kinks and the body, added on top of a scene's own parts.

A kink is a category the card's Kink filter turns on. Its entries are by level (suggestive,
nude, explicit) and by cast, with the aliases of muse.ALIASES (solo, pair, groups, people)
standing for several casts. A cast a kink has no entry for does not take that kink: breeding
needs someone with a penis and someone with a pussy. A kink with themes only joins scenes of
those themes: tentacles belong to a wizard's tower, not to an office.

The body is a part of its own on NSFW ideas: breasts, pussy, penis, body hair, prosthetics,
and for anthros the anatomy of their kind. Everything here is for adults; muse.py still drops
minor-related words and sends its guard negatives.
"""

from __future__ import annotations

import random

FANTASY = ["Fantasy", "Creature", "Horror", "Myth"]

KINKS = {
    "bdsm": {
        "label": "BDSM",
        "suggestive": {
            "solo": ["leather collar", "holding a riding crop", "blindfold pushed up on the forehead", "handcuffs dangling from a finger"],
            "pair": ["one blindfolded, the other teasing", "wrists loosely tied with a silk scarf", "holding the other by a leash"],
            "groups": ["one blindfolded, the others teasing", "everyone in leather collars"],
        },
        "nude": {
            "solo": ["shibari, red rope harness", "leather collar and cuffs", "blindfolded, wrists tied behind the back", "nipple clamps"],
            "pair": ["one tied in red rope, the other admiring the knots", "collar and leash", "blindfold and silk ties"],
            "groups": ["one tied in rope, the others watching", "matching leather collars"],
        },
        "explicit": {
            "solo": ["bound with rope, spread legs", "spreader bar, blindfolded", "ball gag, wrists cuffed", "suspended in rope bondage"],
            "pair": ["bondage, tied to the bed, sex", "spanking, red handprint", "blindfolded, wrists tied, sex", "collar and leash, from behind",
                     "hot wax dripping on the skin", "dominant and submissive, kneeling", "flogging", "orgasm denial, tied up"],
            "groups": ["one tied up, the others taking turns", "dominatrix with a riding crop, the others kneeling", "rope bondage, group sex"],
        },
    },
    "toys": {
        "label": "Toys",
        "suggestive": {"people": ["holding a vibrator, teasing", "sex toy on the bed", "handcuffs and a feather on the sheets"]},
        "nude": {"people": ["holding a dildo, smiling", "vibrator in hand", "toys laid out on the bed"]},
        "explicit": {
            "1girl": ["dildo", "magic wand vibrator", "anal beads", "remote egg vibrator", "suction cup dildo on the floor"],
            "1boy": ["onahole", "prostate massager", "cock ring", "fleshlight"],
            "futa": ["onahole on her penis, dildo in her pussy", "vibrator and onahole", "cock ring"],
            "1girl1boy": ["vibrator on her clit during sex", "remote vibrator, he holds the remote", "cock ring", "double penetration with a dildo"],
            "2girls": ["strap-on sex", "double-ended dildo", "magic wand vibrator"],
            "2boys": ["dildo", "anal beads", "cock ring"],
            "groups": ["strap-on", "toys everywhere", "vibrators"],
            "pair": ["vibrator", "dildo", "anal beads"],
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
            "futa": ["futanari ejaculation", "cum on her own breasts", "precum, pussy juice"],
            "1girl1boy": ["cum on body", "creampie", "cum on face", "cum string", "squirting"],
            "2girls": ["squirting", "pussy juice", "saliva trail"],
            "2boys": ["cum on body", "cum on stomach", "cum in mouth"],
            "girls": ["squirting", "pussy juice everywhere"],
            "boys": ["cum on body", "bukkake"],
            "harem": ["cum on the girls", "creampie, cum dripping"],
            "reverse": ["bukkake", "cum on body", "creampie"],
            "mixed": ["cum everywhere", "sweat and cum"],
            "pair": ["cum on body", "creampie", "cum string"],
            "solo": ["sweat", "dripping wet"],
        },
    },
    "breeding": {
        "label": "Breeding & x-ray",
        "explicit": {
            "1girl1boy": ["cross-section, penis inside, cum inside", "x-ray, creampie, sperm cell reaching the ovum", "breeding, cum inside, impregnation",
                          "internal cumshot, cross-section, womb", "insemination, x-ray view of the womb", "mating press, breeding"],
            "harem": ["cross-section, cum inside", "breeding the girls one after another", "x-ray, creampie, ovum"],
            "reverse": ["cross-section, cum inside", "breeding, cum overflowing", "x-ray, sperm cells, ovum"],
            "mixed": ["breeding, creampies", "cross-section, cum inside"],
            "futa_girl": ["futanari creampie, cross-section", "x-ray, futanari cum inside, ovum", "breeding, impregnation"],
            "futa_boy": ["cross-section, cum inside her", "x-ray, creampie, sperm cell, ovum"],
        },
    },
    "pregnancy": {
        "label": "Pregnancy & lactation",
        "suggestive": {"female": ["pregnant, hand on the belly", "pregnant belly, tight dress", "milk stains on the shirt"]},
        "nude": {"female": ["pregnant", "lactation, milk dripping", "pregnant belly, linea nigra"]},
        "explicit": {"female": ["pregnant, sex", "lactation, breast milk spraying", "pregnant, from the side", "breast sucking, lactation"]},
    },
    "anal": {
        "label": "Anal",
        "nude": {"people": ["presenting, spread ass", "butt plug"]},
        "explicit": {
            "1girl": ["anal masturbation, dildo", "butt plug, fingering"],
            "1boy": ["prostate massager, anal", "anal fingering"],
            "futa": ["anal dildo while stroking"],
            "1girl1boy": ["anal sex", "anal sex, from behind", "rimjob", "anal fingering"],
            "2girls": ["strap-on anal", "rimjob", "anal fingering"],
            "2boys": ["anal sex", "rimjob", "anal fingering, kissing"],
            "futa_girl": ["futanari anal sex", "rimjob"], "futa_boy": ["futanari on male, anal sex", "rimjob"],
            "groups": ["anal sex, the others watching", "anal train"],
            "furry": ["anal, presenting", "tail lifted, anal"], "nonhuman": ["anal, presenting"],
        },
    },
    "oral": {
        "label": "Oral",
        "suggestive": {"people": ["licking lips", "finger in the mouth", "licking a popsicle suggestively"]},
        "explicit": {
            "1girl1boy": ["deepthroat", "fellatio, looking up", "cunnilingus", "69", "face sitting"],
            "2girls": ["cunnilingus", "face sitting", "69"], "2boys": ["fellatio", "deepthroat", "69"],
            "futa_girl": ["fellatio on the futanari", "cunnilingus", "69"], "futa_boy": ["fellatio", "he sucks the futanari"],
            "harem": ["cooperative fellatio", "the girls taking turns on him"], "reverse": ["double fellatio", "spitroast"],
            "girls": ["daisy chain cunnilingus"], "boys": ["fellatio in a circle"], "mixed": ["oral everywhere"],
            "solo": ["licking own fingers", "tongue out, drooling"],
        },
    },
    "femdom": {
        "label": "Femdom",
        "suggestive": {"1girl1boy": ["she holds his tie like a leash", "her heel on his chest"], "reverse": ["she sits on a throne, the boys kneeling"],
                       "harem": ["the girls pin him down"], "mixed": ["the women in charge"], "futa_boy": ["she holds his leash"]},
        "nude": {"1girl1boy": ["he kneels at her feet", "collared man, standing woman"], "reverse": ["the boys kneeling around her"],
                 "harem": ["him tied up, the girls around him"], "futa_boy": ["he kneels before the futanari"]},
        "explicit": {"1girl1boy": ["pegging", "face sitting", "cowgirl, pinning his wrists", "foot worship, she looks down"],
                     "reverse": ["she rides one, the others kneel", "pegging"], "harem": ["the girls take turns riding him, wrists tied"],
                     "mixed": ["women on top"], "futa_boy": ["futanari on male, pinning him down"]},
    },
    "feet": {
        "label": "Feet",
        "suggestive": {"people": ["bare feet, soles", "toes curled, stockings", "foot focus"]},
        "nude": {"people": ["soles, foot focus", "feet up", "toes spread"]},
        "explicit": {"pair": ["footjob", "foot licking", "toe sucking"], "groups": ["footjob", "foot worship"],
                     "solo": ["soles, spread legs", "foot focus"]},
    },
    "petplay": {
        "label": "Pet play",
        "suggestive": {"people": ["cat ears headband, collar with a bell", "dog ears, leash", "kneeling, paw gloves"]},
        "nude": {"people": ["tail plug, collar", "crawling on all fours, leash", "pet bowl, kneeling"]},
        "explicit": {"people": ["tail plug, doggystyle", "leash pulled, from behind", "collar and leash, on all fours"]},
    },
    "costume": {
        "label": "Costume play",
        "suggestive": {"people": ["maid outfit", "nurse outfit", "playboy bunny suit", "police costume", "bunny ears, fishnets"]},
        "nude": {"people": ["only a maid headband and apron", "only bunny ears and cuffs", "only a nurse cap"]},
        "explicit": {"people": ["maid outfit pulled aside", "bunny suit pulled down", "nurse outfit, unbuttoned", "cheerleader uniform, skirt lifted"]},
    },
    "exhibitionism": {
        "label": "Exhibitionism",
        "suggestive": {"people": ["flashing at the window", "skirt lifted, nobody looking", "see-through clothes in public"]},
        "nude": {"people": ["nude at the open window", "nude, risk of being seen", "naked in an empty corridor"]},
        "explicit": {"people": ["sex against the window, city below", "being watched, sex", "quickie, risk of being caught"]},
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
        "nude": {"people": ["hickeys", "bite marks on the shoulder", "scratch marks on the back", "womb tattoo"]},
        "explicit": {"people": ["bite marks", "scratch marks on the back", "red handprint on the hip", "hickeys everywhere", "glowing womb tattoo"]},
    },
    "tentacles": {
        "label": "Tentacles",
        "themes": FANTASY + ["Sci-fi"],
        "suggestive": {"people": ["tentacles curling around the ankles", "tentacles tugging at the clothes", "tentacles rising from the floor"]},
        "nude": {"people": ["tentacles wrapped around the body", "tentacles coiling around the thighs", "suspended by tentacles"]},
        "explicit": {"people": ["tentacle sex", "tentacles wrapped around the limbs, tentacle penetration", "suspended in the air by tentacles",
                                "tentacles in every hole", "tentacle with ribbed texture, penetration"]},
    },
    "slime": {
        "label": "Slime",
        "themes": ["Fantasy", "Creature", "Horror", "Sci-fi"],
        "suggestive": {"people": ["translucent slime dripping on the clothes", "slime melting the clothes"]},
        "nude": {"people": ["covered in translucent slime", "slime pooling on the skin"]},
        "explicit": {"people": ["slime sex, engulfed in slime", "slime creature wrapped around the body", "dripping with slime"]},
    },
    "monsters": {
        "label": "Monsters",
        "themes": FANTASY + ["Sci-fi", "Red light"],
        "suggestive": {"people": ["an orc's hand on the waist", "a demon whispering in the ear", "a werewolf's shadow behind"]},
        "nude": {"people": ["held by a huge orc", "in the arms of a demon", "a minotaur towering behind"]},
        "explicit": {"people": ["sex with an orc, size difference", "minotaur, huge penis, size difference", "demon lover, glowing eyes",
                                "werewolf, knot", "alien, ribbed penis"]},
    },
    "blood": {
        "label": "Blood & bites",
        "themes": ["Horror", "Fantasy", "Myth"],
        "suggestive": {"people": ["vampire bite on the neck, a drop of blood", "blood on the lips"]},
        "nude": {"people": ["vampire bite marks, a trickle of blood", "blood on the lips, pale skin"]},
        "explicit": {"people": ["vampire biting the neck during sex", "blood on the lips, kissing", "bite marks, a trickle of blood"]},
    },
}

FEMALE = ("1girl", "1girl1boy", "2girls", "girls", "harem", "reverse", "mixed", "futa", "futa_girl", "futa_boy")
MALE = ("1boy", "1girl1boy", "2boys", "boys", "harem", "reverse", "mixed", "futa_boy")
FUTA = ("futa", "futa_girl", "futa_boy")
EXTRA_ALIASES = {"female": FEMALE}

# ------------------------------------------------------------------ the body

BREASTS = ["small breasts", "medium breasts", "large breasts", "huge breasts", "perky breasts", "sagging breasts"]
NIPPLES = ["pink nipples", "dark nipples", "puffy nipples", "large areolae", "inverted nipples"]
PUSSY = ["pussy", "shaved pussy", "pubic hair", "hairy pussy", "trimmed pubic hair", "puffy pussy", "vagina"]
CHEST = ["pectorals", "muscular pectorals", "chest hair", "hairy chest", "abs", "smooth chest"]
PENIS = ["penis", "large penis", "veiny penis", "uncut penis, foreskin", "circumcised penis", "thick penis", "huge penis"]
BODY_HAIR = ["armpit hair", "pubic hair", "happy trail"]
PROSTHETIC = ["prosthetic arm", "mechanical arm", "cybernetic leg", "robot joints", "mechanical parts showing through the skin",
              "glowing cybernetic implants"]

# anthros: which kind, from the subject, and its anatomy
KINDS = {
    "canine": ("wolf", "fox", "husky", "dog", "jackal"),
    "equine": ("horse", "zebra", "unicorn"),
    "feline": ("cat", "tiger", "lion", "leopard", "lynx"),
    "reptile": ("dragon", "lizard", "kobold", "snake"),
    "cervine": ("deer", "reindeer"),
    "lagomorph": ("rabbit", "bunny", "hare"),
}
ANTHRO_PENIS = {
    "canine": ["canine penis, knot", "canine penis, sheath", "knotted penis, veiny", "red canine penis"],
    "equine": ["equine penis, flared", "horsecock, mottled penis", "equine penis, medial ring", "flared penis, sheath"],
    "feline": ["feline penis, spiked", "barbed penis", "tapering penis, nubbed"],
    "reptile": ["genital slit, ribbed penis", "hemipenes, diphallia", "scaled penis", "tapering penis, ribbed", "prehensile penis", "two penises"],
    "cervine": ["tapering penis, sheath", "pointed penis"],
    "lagomorph": ["humanoid penis, sheath", "pink penis"],
    "other": ["humanoid penis", "animal penis, sheath", "knotted penis", "ribbed penis", "nubbed penis"],
}
ANTHRO_PUSSY = {
    "canine": ["canine pussy", "animal pussy", "multiple breasts"],
    "equine": ["equine pussy", "puffy animal pussy"],
    "feline": ["animal pussy", "multiple breasts", "feline pussy"],
    "reptile": ["genital slit", "cloaca"],
    "cervine": ["animal pussy"], "lagomorph": ["animal pussy", "multiple breasts"],
    "other": ["animal pussy", "multiple breasts"],
}


def _kind(subject):
    low = subject.lower()
    for kind, words in KINDS.items():
        if any(w in low for w in words):
            return kind
    return "other"


def _sexes(cast, subject):
    """(female, male) present in the idea; anthros and non-humans say it in their subject."""
    low = f" {subject.lower()} "
    if cast in ("furry", "nonhuman"):
        return (any(w in low for w in (" female", "1girl", " girl", " woman")),
                any(w in low for w in (" male", "1boy", " man,", " man ")))
    return cast in FEMALE, cast in MALE


def body(level, cast, subject, theme, rng=None):
    """A few ways the body of an idea can be, for the Body part of the card."""
    if level not in ("suggestive", "nude", "explicit") or cast == "none":
        return []
    rng = rng or random.Random()
    female, male = _sexes(cast, subject)
    futa = cast in FUTA
    machine = theme == "Sci-fi" or any(w in subject.lower() for w in ("android", "cyborg", "gynoid", "mechanical"))
    out = []
    for _ in range(8):
        bits = []
        if level == "suggestive":
            if female:
                bits += [rng.choice(BREASTS), "cleavage"]
            if male or futa:
                bits += [rng.choice(["pectorals", "abs", "chest hair"])] if male else []
                bits += ["bulge"]
        elif cast == "furry":
            kind = _kind(subject)
            if female:
                bits += [rng.choice(BREASTS), rng.choice(ANTHRO_PUSSY[kind])]
            if male:
                bits += [rng.choice(ANTHRO_PENIS[kind]), "balls"]
        else:
            if female:
                bits += [rng.choice(BREASTS), rng.choice(NIPPLES)]
                if not futa or rng.random() < 0.5:
                    bits.append(rng.choice(PUSSY))
            if futa:
                bits += ["futanari", rng.choice(PENIS), rng.choice(["testicles", "no testicles", "penis and pussy"])]
            if male:
                bits += [rng.choice(CHEST), rng.choice(PENIS)] + (["testicles"] if rng.random() < 0.5 else [])
            if rng.random() < 0.35:
                bits.append(rng.choice(BODY_HAIR))
        if machine and rng.random() < 0.7:
            bits.append(rng.choice(PROSTHETIC))
        out.append(", ".join(dict.fromkeys(bits)))
    return list(dict.fromkeys(b for b in out if b))


# ------------------------------------------------------------------ kinks


def themed(kink, theme):
    themes = KINKS[kink].get("themes")
    return themes is None or theme in themes


def entries(kink, level, cast, aliases):
    """What a kink gives a cast at a level: its own entries, else those of an alias it is in."""
    lists = KINKS[kink].get(level) or {}
    if cast in lists:
        return lists[cast]
    for alias in ("pair", "groups", "solo", "female", "people"):
        if alias in lists and cast in (EXTRA_ALIASES.get(alias) or aliases.get(alias, ())):
            return lists[alias]
    return []


def casts_by_level(aliases, casts):
    """{kink: {level: [casts it has entries for]}}, for the card to count with."""
    return {k: {lvl: [c for c in casts if entries(k, lvl, c, aliases)] for lvl in ("suggestive", "nude", "explicit")}
            for k in KINKS}
