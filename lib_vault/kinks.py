"""Muse's NSFW layers: kinks and the body, added on top of a scene's own parts.

A kink is a category the card's Kink filter turns on. Its entries are by level (suggestive,
nude, explicit) and by cast, with the aliases of muse.ALIASES (solo, pair, groups, people)
standing for several casts. A cast a kink has no entry for does not take that kink: breeding
needs someone with a penis and someone with a pussy. A kink with themes only joins scenes of
those themes: tentacles belong to a wizard's tower, not to an office.

The body is a part of its own on NSFW ideas: breasts, pussy, penis, body hair, prosthetics,
and for anthros the anatomy of their kind. Everything here is for adults; muse.py still drops
minor-related words.
"""

from __future__ import annotations

import random
import re

FANTASY = ["Fantasy", "Creature", "Horror", "Myth"]

# x-rays where the act is: the throat when it is oral, the rectum when it is anal
THROAT_X = ["x-ray, cross-section, throat, deepthroat", "x-ray, throat, cum in mouth", "cross-section, deepthroat, throat bulge"]
ANAL_X = ["cross-section, anal, cum inside", "x-ray, anal, internal cumshot"]

KINKS = {
    "bdsm": {
        "label": "BDSM",
        "suggestive": {
            "solo": ["leather collar", "holding riding crop", "blindfold, collar", "handcuffs", "o-ring choker, leather cuffs"],
            "pair": ["blindfold, teasing", "wrists tied, silk scarf", "leash, collar", "riding crop, dominant pose"],
            "groups": ["blindfold, teasing", "matching collars", "leash, collar, kneeling"],
        },
        "nude": {
            "solo": ["shibari, red rope", "leather collar, leather cuffs", "blindfold, arms behind back, bound wrists", "nipple clamps",
                     "rope harness, kneeling", "spreader bar"],
            "pair": ["shibari, red rope", "collar, leash", "blindfold, silk ties", "bound wrists, kneeling", "nipple clamps, collar"],
            "groups": ["shibari, rope, kneeling", "matching collars", "leash, collar, kneeling"],
        },
        "explicit": {
            "solo": ["bound, rope, spread legs", "spreader bar, blindfold", "ball gag, cuffs", "suspension bondage", "shibari, vibrator",
                     "bound wrists, arms up"],
            "pair": ["bondage, tied to bed, sex", "spanking, handprint", "blindfold, bound wrists, sex", "collar, leash, sex from behind",
                     "wax play", "dominant, submissive, kneeling", "flogging", "orgasm denial, bound", "ball gag, doggystyle", "choker, leash pull"],
            "groups": ["bondage, gangbang", "dominatrix, riding crop, kneeling", "rope bondage, group sex", "bound wrists, spitroast",
                       "collar, leash, group sex"],
        },
    },
    "toys": {
        "label": "Toys",
        "suggestive": {"people": ["holding vibrator", "sex toy, on bed", "handcuffs, feather", "dildo, holding"]},
        "nude": {"people": ["holding dildo, smile", "vibrator", "sex toys, on bed", "magic wand"]},
        "explicit": {
            "1girl": ["dildo", "magic wand", "anal beads", "egg vibrator, remote control vibrator", "dildo riding, suction cup dildo",
                      "vibrator on clitoris", "double dildo"],
            "1boy": ["onahole", "prostate massager", "cock ring", "fleshlight"],
            "futa": ["onahole, dildo", "vibrator, onahole", "cock ring", "futanari masturbation, onahole"],
            "1girl1boy": ["vibrator on clitoris, sex", "remote control vibrator", "cock ring", "dildo, double penetration", "anal beads, sex"],
            "2girls": ["strap-on, sex", "double dildo", "magic wand", "vibrator, fingering"],
            "2boys": ["dildo", "anal beads", "cock ring", "prostate massager"],
            "groups": ["strap-on", "sex toys", "vibrators", "magic wand, group sex"],
            "pair": ["vibrator", "dildo", "anal beads"],
            "solo": ["dildo", "vibrator"],
        },
    },
    "fluids": {
        "label": "Fluids",
        "suggestive": {"people": ["wet lips, saliva", "sweat, shiny skin", "drooling"]},
        "nude": {"people": ["sweat", "body oil, shiny skin", "wet skin, oiled"]},
        "explicit": {
            "1girl": ["pussy juice", "squirting", "female ejaculation", "pussy juice trail"],
            "1boy": ["ejaculation", "cum on stomach", "precum"],
            "futa": ["futanari ejaculation", "cum on breasts", "precum, pussy juice"],
            "1girl1boy": ["cum on body", "creampie", "facial", "cum string", "squirting", "cum in mouth"],
            "2girls": ["squirting", "pussy juice", "saliva trail"],
            "2boys": ["cum on body", "cum on stomach", "cum in mouth"],
            "girls": ["squirting", "pussy juice"],
            "boys": ["cum on body", "bukkake"],
            "harem": ["cum on body, multiple girls", "creampie, cum drip"],
            "reverse": ["bukkake", "cum on body", "creampie", "cum on face"],
            "mixed": ["cum on body", "sweat, cum"],
            "pair": ["cum on body", "creampie", "cum string"],
            "solo": ["sweat", "pussy juice"],
        },
    },
    "breeding": {
        "label": "Breeding & x-ray",
        # by act: a womb for vaginal sex, the rectum for anal, the throat for oral (see acts.py)
        "explicit": {
            "1girl1boy": ["cross-section, penis inside, cum inside", "x-ray, creampie, sperm cell, ovum", "breeding, cum inside, impregnation",
                          "internal cumshot, cross-section, womb", "insemination, x-ray, womb", "mating press, breeding"] + ANAL_X + THROAT_X,
            "harem": ["cross-section, cum inside", "breeding, multiple girls", "x-ray, creampie, ovum"] + ANAL_X + THROAT_X,
            "reverse": ["cross-section, cum inside", "breeding, cum overflow", "x-ray, sperm cell, ovum"] + ANAL_X + THROAT_X,
            "mixed": ["breeding, creampie", "cross-section, cum inside", "x-ray, womb, cum inside"] + ANAL_X + THROAT_X,
            "futa_girl": ["futanari, creampie, cross-section", "x-ray, cum inside, ovum", "breeding, impregnation, womb"] + ANAL_X + THROAT_X,
            "futa_boy": ["cross-section, cum inside", "x-ray, creampie, sperm cell, ovum"] + ANAL_X + THROAT_X,
            "human_furry": ["cross-section, knot, cum inside", "x-ray, interspecies, breeding, ovum", "breeding, cum inside"] + ANAL_X + THROAT_X,
            # between men: male pregnancy; between women: a strap-on, or one of them with a knot
            "2boys": ["mpreg, anal, cum inside", "knotting, anal, breeding", "cross-section, anal, cum inside",
                      "x-ray, anal, sperm cell", "male pregnancy, anal, cum inside"] + THROAT_X,
            "boys": ["mpreg, anal, cum inside", "cross-section, anal, cum inside", "knotting, anal, breeding"] + THROAT_X,
            "2girls": ["strap-on, cum inside, womb", "impregnation, womb, strap-on", "cross-section, strap-on", "x-ray, strap-on, womb"],
            "girls": ["strap-on, cum inside, womb", "impregnation, womb, strap-on", "cross-section, strap-on"],
        },
    },
    "pregnancy": {
        "label": "Pregnancy & lactation",
        "suggestive": {"female": ["pregnant, hand on own stomach", "pregnant, tight dress", "lactation, wet shirt"]},
        "nude": {"female": ["pregnant", "lactation, milk drip", "pregnant, linea nigra"]},
        "explicit": {"female": ["pregnant, sex", "lactation, breast milk, milk spray", "pregnant, from side", "breast sucking, lactation"]},
    },
    "anal": {
        "label": "Anal",
        "nude": {"people": ["presenting, spread ass", "butt plug"]},
        "explicit": {
            "1girl": ["anal masturbation, dildo", "butt plug, fingering", "anal beads"],
            "1boy": ["prostate massager", "anal fingering"],
            "futa": ["anal dildo, futanari masturbation"],
            "1girl1boy": ["anal", "anal, from behind", "anilingus", "anal fingering", "anal, legs up"],
            "2girls": ["strap-on, anal", "anilingus", "anal fingering"],
            "2boys": ["anal", "anilingus", "anal fingering, kiss"],
            "futa_girl": ["futa with female, anal", "anilingus"], "futa_boy": ["futa with male, anal", "anilingus"],
            "groups": ["anal, group sex", "anal, gangbang"],
            "furry": ["anal, presenting", "raised tail, anal"], "kemono": ["anal, presenting", "raised tail, anal"],
            "solo": ["anal, presenting", "anal masturbation"],
        },
    },
    "oral": {
        "label": "Oral",
        "suggestive": {"people": ["licking lips", "finger in mouth", "popsicle, licking"]},
        "explicit": {
            "1girl1boy": ["deepthroat", "fellatio, looking up", "cunnilingus", "69", "face sitting", "irrumatio"],
            "2girls": ["cunnilingus", "face sitting", "69"], "2boys": ["fellatio", "deepthroat", "69"],
            "futa_girl": ["fellatio, futanari", "cunnilingus", "69"], "futa_boy": ["fellatio", "futa with male, fellatio"],
            "harem": ["cooperative fellatio", "double fellatio, multiple girls"], "reverse": ["double fellatio", "spitroast"],
            "girls": ["daisy chain, cunnilingus"], "boys": ["fellatio, group sex"], "mixed": ["fellatio, cunnilingus, orgy"],
            "solo": ["licking finger", "tongue out, drooling"],
        },
    },
    "femdom": {
        "label": "Femdom",
        "suggestive": {"1girl1boy": ["femdom, necktie grab", "femdom, foot on chest"], "reverse": ["femdom, throne, kneeling"],
                       "harem": ["femdom, pinned down"], "mixed": ["femdom"], "futa_boy": ["femdom, leash"]},
        "nude": {"1girl1boy": ["femdom, kneeling", "femdom, collar, leash"], "reverse": ["femdom, kneeling"],
                 "harem": ["femdom, bound, multiple girls"], "futa_boy": ["femdom, kneeling"]},
        "explicit": {"1girl1boy": ["pegging", "femdom, face sitting", "femdom, cowgirl position, pinned down", "femdom, foot worship"],
                     "reverse": ["femdom, cowgirl position, kneeling", "pegging"], "harem": ["femdom, cowgirl position, bound wrists"],
                     "mixed": ["femdom, girl on top"], "futa_boy": ["futa with male, femdom, pinned down"]},
    },
    "feet": {
        "label": "Feet",
        "suggestive": {"people": ["barefoot, soles", "curled toes, stockings", "foot focus"]},
        "nude": {"people": ["soles, foot focus", "feet up", "spread toes"]},
        "explicit": {"pair": ["footjob", "foot licking", "toe sucking"], "groups": ["footjob", "foot worship"],
                     "solo": ["soles, spread legs", "foot focus"]},
    },
    "petplay": {
        "label": "Pet play",
        "suggestive": {"people": ["fake animal ears, bell collar", "dog ears, leash", "kneeling, paw gloves"]},
        "nude": {"people": ["tail plug, collar", "all fours, leash", "pet bowl, kneeling"]},
        "explicit": {"people": ["tail plug, doggystyle", "leash pull, from behind", "collar, leash, all fours"]},
    },
    "costume": {
        "label": "Costume play",
        "suggestive": {"people": ["maid", "nurse", "playboy bunny", "police uniform", "fake animal ears, fishnets"]},
        "nude": {"people": ["maid headdress, apron, naked apron", "rabbit ears, wrist cuffs", "nurse cap"]},
        "explicit": {"people": ["maid, clothes aside", "playboy bunny, leotard pull", "nurse, open clothes", "cheerleader, skirt lift"]},
    },
    "exhibitionism": {
        "label": "Exhibitionism & voyeurism",
        "suggestive": {"people": ["flashing, window", "skirt lift, public", "see-through, public", "voyeurism, peeking"]},
        "nude": {"people": ["nude, open window", "public nudity", "nude, empty corridor", "voyeurism, peeping"]},
        "explicit": {"people": ["against glass, sex, cityscape", "public sex, audience", "public sex, quickie", "voyeurism, sex, audience"]},
    },
    "hypnosis": {
        "label": "Hypnosis & mind control",
        "suggestive": {"people": ["hypnosis, spiral eyes", "pendulum, empty eyes", "glowing eyes, entranced"]},
        "nude": {"people": ["mind control, empty eyes, standing", "hypnosis, expressionless", "heart-shaped pupils, entranced"]},
        "explicit": {"solo": ["hypnosis, empty eyes, masturbation", "mind control, heart-shaped pupils"],
                     "pair": ["hypnosis, empty eyes, sex", "mind control, glowing eyes", "hypnosis, kneeling, oral"],
                     "groups": ["hypnosis, group sex", "mind control, glowing eyes, group sex"]},
    },
    "watersports": {
        "label": "Watersports",
        "suggestive": {"people": ["have to pee, crossed legs", "have to pee, trembling", "wet panties"]},
        "nude": {"people": ["peeing", "peeing, shower", "squatting, peeing", "puddle, peeing"]},
        "explicit": {"solo": ["peeing, spread legs", "peeing, masturbation"], "pair": ["golden shower", "peeing on another", "peeing, sex"],
                     "groups": ["golden shower, group sex"]},
    },
    "scat": {
        "label": "Scat",
        "nude": {"people": ["defecating, squatting", "scat"]},
        "explicit": {"solo": ["scat, masturbation"], "pair": ["scat"], "groups": ["scat"]},
    },
    "latex": {
        "label": "Latex & fetish wear",
        "suggestive": {"people": ["black latex bodysuit", "pvc corset, thigh boots", "leather harness", "fishnet bodystocking"]},
        "nude": {"people": ["leather harness", "latex gloves, latex thighhighs", "fishnet bodystocking"]},
        "explicit": {"people": ["latex bodysuit, crotch zipper", "leather harness", "latex gloves, latex thighhighs", "pvc boots"]},
    },
    "marks": {
        "label": "Bites & marks",
        "suggestive": {"people": ["hickey, neck", "lipstick mark"]},
        "nude": {"people": ["hickey", "bite mark, shoulder", "scratches, back", "womb tattoo"]},
        "explicit": {"people": ["bite mark", "scratches, back", "handprint, hip", "hickey, multiple hickeys", "glowing womb tattoo"]},
    },
    "tentacles": {
        "label": "Tentacles",
        "themes": FANTASY + ["Sci-fi"],
        "suggestive": {"people": ["tentacles, ankle grab", "tentacles, clothes pull", "tentacles, floor"]},
        "nude": {"people": ["tentacles, wrapped", "tentacles, thigh wrap", "tentacles, suspended"]},
        "explicit": {"people": ["tentacle sex", "tentacles, restrained, tentacle penetration", "tentacles, suspended, sex",
                                "tentacles, multiple insertions", "ribbed tentacle, penetration"]},
    },
    "slime": {
        "label": "Slime",
        "themes": ["Fantasy", "Creature", "Horror", "Sci-fi"],
        "suggestive": {"people": ["slime, dripping, clothes", "slime, melting clothes"]},
        "nude": {"people": ["covered in slime", "slime, wet skin"]},
        "explicit": {"people": ["slime sex, engulfed", "slime monster, restrained", "slime, dripping, sex"]},
    },
    "monsters": {
        "label": "Monsters",
        "themes": FANTASY + ["Sci-fi", "Red light"],
        "suggestive": {"people": ["orc, hand on waist", "demon, whispering", "werewolf, shadow"]},
        "nude": {"people": ["orc, size difference, carrying", "demon, embrace", "minotaur, size difference"]},
        "explicit": {"people": ["orc, sex, size difference", "minotaur, huge penis, size difference", "demon, glowing eyes, sex",
                                "werewolf, monster, knot", "alien, ribbed penis"]},
    },
    "blood": {
        "label": "Blood & bites",
        "themes": ["Horror", "Fantasy", "Myth"],
        "suggestive": {"people": ["vampire bite, neck, blood drop", "blood on lips"]},
        "nude": {"people": ["bite mark, blood trickle", "blood on lips, pale skin"]},
        "explicit": {"people": ["vampire, neck biting, sex", "blood on lips, kiss", "bite mark, blood trickle"]},
    },
}

# ---- after Danbooru's tag groups: size, power, bodies that change
KINKS.update({
    "size": {
        "label": "Size difference",
        "suggestive": {"pair": ["size difference", "height difference", "size difference, lifting another", "size difference, princess carry"],
                       "groups": ["size difference", "height difference"]},
        "nude": {"pair": ["size difference, hug", "height difference, standing", "size difference, carrying"], "groups": ["size difference"]},
        "explicit": {"pair": ["size difference, sex", "size difference, full nelson", "size difference, suspended congress",
                              "size difference, carrying, sex", "height difference, standing sex"],
                     "penis": ["size difference, stomach bulge", "size difference, full nelson", "size difference, carrying, sex"],
                     "groups": ["size difference, group sex", "size difference, sandwiched"]},
    },
    "smalldom": {
        "label": "Small dom, big sub",
        "suggestive": {"pair": ["small dom big sub, size difference", "small dom big sub, leash", "small dom big sub, necktie grab"],
                       "groups": ["small dom big sub, size difference"]},
        "nude": {"pair": ["small dom big sub, kneeling", "small dom big sub, collar, leash", "small dom big sub, foot on chest"],
                 "groups": ["small dom big sub, kneeling"]},
        "explicit": {"pair": ["small dom big sub, pinned down, sex", "small dom big sub, size difference, sex", "small dom big sub, bound wrists",
                              "small dom big sub, leash pull"], "groups": ["small dom big sub, group sex"]},
    },
    "bigdom": {
        "label": "Big dom, small sub",
        "suggestive": {"pair": ["big dom small sub, size difference", "big dom small sub, pinned against wall", "big dom small sub, chin grab"],
                       "groups": ["big dom small sub, size difference"]},
        "nude": {"pair": ["big dom small sub, carrying", "big dom small sub, lap sitting", "big dom small sub, head pat"],
                 "groups": ["big dom small sub, size difference"]},
        "explicit": {"pair": ["big dom small sub, full nelson", "big dom small sub, pinned down, sex",
                              "big dom small sub, suspended congress", "big dom small sub, mating press"],
                     "penis": ["big dom small sub, stomach bulge", "big dom small sub, full nelson", "big dom small sub, mating press"],
                     "groups": ["big dom small sub, gangbang"]},
    },
    "bondage": {
        "label": "Bondage",
        "suggestive": {"people": ["bound wrists", "rope, crossed arms", "handcuffs, bound wrists", "bound ankles"]},
        "nude": {"solo": ["shibari", "hogtie", "frogtie", "armbinder", "crotch rope", "bound to chair", "rope harness, suspension"],
                 "pair": ["shibari", "bound wrists, bound ankles", "rope, leash", "bound together"], "groups": ["shibari", "bound wrists"]},
        "explicit": {"solo": ["frogtie, spread legs", "shibari, crotch rope", "hogtie, gag", "suspension bondage, spread legs", "bound to bed, spreader bar"],
                     "pair": ["shibari, sex", "frogtie, sex", "bound wrists, sex", "armbinder, sex", "bound to bed, sex", "rope, suspension, sex"],
                     "groups": ["shibari, group sex", "bound wrists, gangbang"]},
    },
    "muscle": {
        "label": "Muscle growth",
        "suggestive": {"people": ["muscle growth, torn clothes", "muscle growth, bursting clothes", "muscle growth, flexing, veins"]},
        "nude": {"people": ["muscle growth, abs, veins", "muscle growth, flexing", "muscular, muscle growth, steam"]},
        "explicit": {"people": ["muscle growth, sex", "muscle growth, veins, sweat", "muscle growth, flexing, sex"]},
    },
    "transform": {
        "label": "Transformation",
        "suggestive": {"female": ["mid-transformation, animal ears, tail", "transformation, sparkles", "genderswap, transformation",
                                  "breast expansion, bursting clothes", "corruption, mid-transformation"],
                       "people": ["mid-transformation, animal ears, tail", "transformation, sparkles", "genderswap, transformation",
                                  "corruption, mid-transformation"]},
        "nude": {"female": ["mid-transformation, fur, claws", "slime transformation", "petrification", "breast expansion",
                            "animal transformation, tail, ears"],
                 "people": ["mid-transformation, fur, claws", "slime transformation", "petrification", "animal transformation, tail, ears"]},
        "explicit": {"female": ["mid-transformation, sex", "transformation, corruption, glowing womb tattoo", "breast expansion, sex",
                                "furry transformation, sex"],
                     "people": ["mid-transformation, sex", "furry transformation, sex", "transformation, corruption, sex"]},
    },
    "inflation": {
        "label": "Inflation & bulge",
        "suggestive": {"female": ["breast expansion", "belly inflation, tight clothes"], "people": ["belly inflation, tight clothes"]},
        "nude": {"female": ["belly inflation", "breast expansion, large breasts"], "people": ["belly inflation"]},
        "explicit": {"penis": ["stomach bulge", "cum inflation", "stomach bulge, deep penetration", "cum inflation, cum overflow"],
                     "rough": ["stomach bulge, gangbang", "cum inflation, group sex"]},
    },
    "chastity": {
        "label": "Chastity",
        "suggestive": {"1boy": ["chastity cage"], "2boys": ["chastity cage"], "boys": ["chastity cage"], "1girl": ["chastity belt"],
                       "2girls": ["chastity belt"], "girls": ["chastity belt"], "1girl1boy": ["chastity cage, key", "chastity belt, key"],
                       "harem": ["chastity cage, key"], "reverse": ["chastity belt, key"], "futa": ["chastity cage"]},
        "nude": {"1boy": ["chastity cage", "chastity cage, orgasm denial"], "2boys": ["chastity cage, key"], "boys": ["chastity cage"],
                 "1girl": ["chastity belt"], "2girls": ["chastity belt, key"], "girls": ["chastity belt"],
                 "1girl1boy": ["chastity cage, holding key", "chastity belt, holding key"], "harem": ["chastity cage, key"], "reverse": ["chastity belt"],
                 "futa": ["chastity cage, orgasm denial"], "futa_girl": ["chastity cage, key"], "futa_boy": ["chastity cage, key"]},
        "explicit": {"1boy": ["chastity cage, precum"], "2boys": ["chastity cage, anal"], "boys": ["chastity cage, anal"],
                     "1girl1boy": ["chastity cage, pegging", "chastity cage, handjob"], "harem": ["chastity cage, femdom"],
                     "futa_boy": ["chastity cage, anal"], "futa": ["chastity cage, precum"]},
    },
    "corruption": {
        "label": "Corruption",
        "themes": FANTASY + ["Sci-fi", "Red light"],
        "suggestive": {"people": ["corruption, dark aura", "corruption, glowing eyes", "corruption, black sclera"]},
        "nude": {"people": ["corruption, glowing womb tattoo", "corruption, dark veins", "corruption, demon horns"]},
        "explicit": {"people": ["corruption, mind break", "corruption, glowing womb tattoo, sex", "corruption, heart-shaped pupils, sex"]},
    },
    "belly": {
        "label": "Belly inflation",
        "suggestive": {"people": ["belly inflation, tight clothes", "round belly, clothes pull", "belly inflation, hand on own stomach"]},
        "nude": {"people": ["belly inflation", "belly inflation, round belly", "big belly, hand on own stomach"]},
        "explicit": {"penis": ["belly inflation, cum inflation", "cum inflation, stomach bulge", "belly inflation, cum inside"],
                     "solo": ["belly inflation, round belly", "big belly, hand on own stomach"],
                     "people": ["belly inflation, round belly"]},
    },
    "mpreg": {
        "label": "Male pregnancy",
        "suggestive": {"male": ["male pregnancy, hand on own stomach", "male pregnancy, tight shirt", "male pregnancy, round belly"]},
        "nude": {"male": ["male pregnancy", "male pregnancy, round belly", "male pregnancy, lactation"]},
        "explicit": {"1boy": ["male pregnancy, erection", "male pregnancy, round belly"],
                     "2boys": ["male pregnancy, anal, sex", "male pregnancy, knotting, anal", "male pregnancy, anal, from side"],
                     "boys": ["male pregnancy, anal, group sex", "male pregnancy, anal, cum inside"],
                     "1girl1boy": ["male pregnancy, pegging", "male pregnancy, femdom, cowgirl position"],
                     "futa_boy": ["male pregnancy, futa with male, anal", "male pregnancy, anal"],
                     "male": ["male pregnancy, round belly"]},
    },
})

FEMALE = ("1girl", "1girl1boy", "2girls", "girls", "harem", "reverse", "mixed", "futa", "futa_girl", "futa_boy", "human_furry")
MALE = ("1boy", "1girl1boy", "2boys", "boys", "harem", "reverse", "mixed", "futa_boy", "human_furry")

FUTA = ("futa", "futa_girl", "futa_boy")
# pairs and groups with a penis in them (stomach bulge, cum inflation), and groups that can be a gangbang
PENIS_PAIRS = ("1girl1boy", "2boys", "futa_girl", "futa_boy", "human_furry", "harem", "reverse", "boys", "mixed")
EXTRA_ALIASES = {"female": FEMALE, "male": MALE, "penis": PENIS_PAIRS, "rough": ("reverse", "boys", "mixed")}

# ------------------------------------------------------------------ the body

BREASTS = ["small breasts", "medium breasts", "large breasts", "huge breasts", "perky breasts", "sagging breasts"]
NIPPLES = ["pink nipples", "dark nipples", "puffy nipples", "large areolae", "inverted nipples"]
PUSSY = ["pussy", "shaved pussy", "pubic hair", "hairy pussy", "trimmed pubic hair", "puffy pussy", "vagina"]
CHEST = ["pectorals", "muscular pectorals", "chest hair", "hairy chest", "abs", "smooth chest",
         "happy trail", "defined Adonis belt", "soft stomach", "veined forearms"]
PENIS = ["penis", "large penis", "veiny penis", "uncut penis, foreskin", "circumcised penis", "thick penis", "huge penis",
         "soft penis", "erect penis", "heavy balls"]
BODY_HAIR = ["armpit hair", "pubic hair", "happy trail"]
PROSTHETIC = ["prosthetic arm", "mechanical arm", "cybernetic leg", "robot joints", "exposed mechanical parts",
              "glowing cybernetic implants"]

# anthros: which kind, from the subject, and its anatomy
KINDS = {
    "canine": ("wolf", "fox", "husky", "dog", "jackal", "coyote", "hyena", "german shepherd"),
    "equine": ("horse", "zebra", "unicorn", "donkey"),
    "feline": ("cat", "tiger", "lion", "leopard", "lynx", "cheetah", "panther", "jaguar"),
    "shark": ("shark",),
    "cetacean": ("orca", "dolphin"),
    "avian": ("eagle", "hawk", "owl", "raven", "parrot", "bird", "crow", "gryphon"),
    "dragon": ("dragon", "wyvern"),
    "reptile": ("lizard", "crocodile", "alligator", "gecko", "snake"),
    "bovine": ("bull", "cow", "bison", "ox"),
    "cervine": ("deer", "reindeer", "elk", "moose", "stag"),
    "ursine": ("bear", "panda"),
    "mustelid": ("otter", "ferret", "weasel"),
    "rodent": ("mouse", "rat", "squirrel"),
    "lagomorph": ("rabbit", "bunny", "hare"),
    "caprine": ("goat", "sheep", "ram"),
}
ANTHRO_PENIS = {
    "canine": ["canine penis, knot", "canine penis, sheath", "knotted penis, veiny", "red canine penis, knot"],
    "equine": ["equine penis, flared", "horsecock, mottled penis", "equine penis, medial ring", "flared penis, sheath"],
    "feline": ["feline penis, spiked", "barbed penis", "tapering penis, nubbed"],
    "shark": ["claspers, diphallia", "two penises, genital slit"],
    "cetacean": ["genital slit, prehensile penis", "tapering penis, genital slit"],
    "avian": ["genital slit", "tapering penis, cloaca", "corkscrew penis"],
    "dragon": ["genital slit, ribbed penis", "scaled penis, knot", "hemipenes, diphallia", "tapering penis, ribbed"],
    "reptile": ["hemipenes, diphallia", "genital slit, ribbed penis", "two penises", "scaled penis"],
    "bovine": ["bovine penis, tapering", "sheath, tapering penis"],
    "cervine": ["tapering penis, sheath", "pointed penis"],
    "ursine": ["humanoid penis, sheath", "thick penis, sheath"],
    "mustelid": ["tapering penis, sheath", "humanoid penis"],
    "rodent": ["humanoid penis, sheath", "pink penis"],
    "lagomorph": ["humanoid penis, sheath", "pink penis"],
    "caprine": ["tapering penis, sheath", "humanoid penis"],
    "other": ["humanoid penis", "animal penis, sheath", "knotted penis", "ribbed penis", "nubbed penis"],
}
ANTHRO_PUSSY = {
    "canine": ["canine pussy", "animal pussy", "multiple breasts"],
    "equine": ["equine pussy", "puffy animal pussy"],
    "feline": ["animal pussy", "multiple breasts", "feline pussy"],
    "shark": ["genital slit", "cloaca"], "cetacean": ["genital slit"], "avian": ["cloaca"],
    "dragon": ["genital slit", "cloaca"], "reptile": ["cloaca", "genital slit"],
    "bovine": ["animal pussy", "udders"], "cervine": ["animal pussy"],
    "ursine": ["animal pussy", "multiple breasts"], "mustelid": ["animal pussy", "multiple breasts"],
    "rodent": ["animal pussy", "multiple breasts"], "lagomorph": ["animal pussy", "multiple breasts"],
    "caprine": ["animal pussy", "udders"],
    "other": ["animal pussy", "multiple breasts"],
}
# breasts make no sense on some kinds the way they do on mammals
NO_BREASTS = ("avian", "reptile", "shark")


def _kind(subject):
    low = subject.lower()
    for kind, words in KINDS.items():
        if any(re.search(rf"\b{w}\b", low) for w in words):
            return kind
    return "other"


# casts whose subject says who they are: a female fox, a male android
ANTHROS = ("furry", "kemono")
BEINGS = ANTHROS + ("mythic", "monster", "synth", "nonhuman")


def _sexes(cast, subject):
    """(female, male) present in the idea; anthros and non-humans say it in their subject."""
    low = f" {subject.lower()} "
    if cast in BEINGS:
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
    machine = cast == "synth" or theme == "Sci-fi" or any(w in subject.lower() for w in ("android", "cyborg", "gynoid", "mechanical"))
    out = []
    for _ in range(8):
        bits = []
        if level == "suggestive":
            if female:
                bits += [rng.choice(BREASTS), "cleavage"]
            if male or futa:
                bits += [rng.choice(["pectorals", "abs", "chest hair"])] if male else []
                bits += ["bulge"]
        elif cast in ANTHROS or (cast in BEINGS and "werewolf" in subject.lower()):
            kind = _kind(subject) if cast in ANTHROS else "canine"
            if female:
                bits += ([] if kind in NO_BREASTS else [rng.choice(BREASTS)]) + [rng.choice(ANTHRO_PUSSY[kind])]
            if male:
                bits += [rng.choice(ANTHRO_PENIS[kind])] + ([] if kind in ("shark", "cetacean", "avian", "reptile", "dragon") else ["balls"])
        elif cast == "human_furry":
            # one human, one anthro of the other sex; the subject says which is which
            kind = _kind(subject)
            low = subject.lower()
            if "anthro male" in low:  # a woman, a male anthro
                bits += [rng.choice(BREASTS), rng.choice(PUSSY), rng.choice(ANTHRO_PENIS[kind])]
            else:                     # a man, a female anthro
                bits += [rng.choice(PENIS)] + ([] if kind in NO_BREASTS else [rng.choice(BREASTS)]) + [rng.choice(ANTHRO_PUSSY[kind])]
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
    """What a kink gives a cast at a level: its own entries, else those of an alias it is in.

    1boy gets an extra male-solo list on top. Phrases already in the cast list are not added again.
    """
    lists = KINKS[kink].get(level) or {}
    if cast in lists:
        base = list(lists[cast])
    else:
        base = []
        for alias in ("penis", "rough", "pair", "groups", "solo", "female", "male", "people"):
            if alias in lists and cast in (EXTRA_ALIASES.get(alias) or aliases.get(alias, ())):
                base = list(lists[alias])
                break
    extra = MALE_SOLO.get(kink, {}).get(level, []) if cast == "1boy" else []
    if not extra:
        return base
    seen = {_phrase_key(x) for x in base}
    return base + [x for x in extra if _phrase_key(x) not in seen]


def _phrase_key(piece):
    return re.sub(r"\s+", " ", str(piece or "").replace("_", " ")).strip().lower()


# Doing phrases added only when the cast is 1boy and the scene is not SFW. Keys already in the scene are skipped.
MALE_SOLO_ACTIONS = {
    "suggestive": ["adjusting bulge", "shirt lift, abs", "hand in pants", "loosened belt, bulge"],
    "nude": ["nude, male focus", "penis grab", "erection, looking at viewer", "masturbation, hand on penis",
             "standing nude, male focus", "sitting nude, legs apart"],
    "explicit": ["masturbation, male focus", "penis grab, ejaculation", "autofellatio", "spread legs, erection",
                 "onahole, masturbation", "anal fingering, male focus"],
}


# 1boy only. Never copied onto 2boys or hetero. phrases already in that kink's 1boy list are skipped.
MALE_SOLO = {
    "toys": {
        "nude": ["onahole, holding", "cock ring", "prostate massager, holding"],
        "explicit": ["onahole, thrusting", "fleshlight, precum", "prostate massager, erection", "cock ring, masturbation",
                     "vibrator against perineum"],
    },
    "fluids": {
        "nude": ["precum, erection", "sweat, male focus"],
        "explicit": ["precum string", "cum on own stomach", "cum on own chest", "cum on own face", "ejaculation, male focus",
                     "cum drip, penis"],
    },
    "anal": {
        "nude": ["butt plug, male", "spreading own ass"],
        "explicit": ["anal fingering, male focus", "butt plug, prostate", "dildo, anal, male", "anal beads, male focus"],
    },
    "oral": {
        "explicit": ["autofellatio", "licking own penis", "penis in own mouth"],
    },
    "exhibitionism": {
        "suggestive": ["bulge, open window", "shirt lift, public, male"],
        "nude": ["nude, male focus, open window", "public nudity, male"],
        "explicit": ["masturbation, open window", "public masturbation, male"],
    },
    "hypnosis": {
        "explicit": ["hypnosis, empty eyes, male masturbation", "mind control, erection"],
    },
    "watersports": {
        "explicit": ["peeing, male focus, erection", "peeing, masturbation, male"],
    },
    "latex": {
        "suggestive": ["latex shorts, bulge", "open latex shirt, male"],
        "explicit": ["latex bodysuit, crotch zipper, male", "leather harness, erection"],
    },
    "marks": {
        "nude": ["bite mark, pectoral", "scratches, male chest"],
        "explicit": ["handprint, male hip", "bite mark, shoulder, male"],
    },
    "muscle": {
        "explicit": ["muscle growth, masturbation", "muscle growth, flexing, erection"],
    },
    "chastity": {
        "explicit": ["chastity cage, leaking", "chastity cage, hands behind back"],
    },
    "bondage": {
        "explicit": ["shibari, male, erection", "bound wrists, male masturbation", "spreader bar, male"],
    },
    "bdsm": {
        "explicit": ["ball gag, male, erection", "blindfold, male masturbation", "collar, male, kneeling"],
    },
}


def casts_by_level(aliases, casts):
    """{kink: {level: [casts it has entries for]}}, for the card to count with."""
    return {k: {lvl: [c for c in casts if entries(k, lvl, c, aliases)] for lvl in ("suggestive", "nude", "explicit")}
            for k in KINKS}
