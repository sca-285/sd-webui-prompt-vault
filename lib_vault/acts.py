"""Sex acts by family, and which kinks go with which acts.

An explicit idea's Doing is an act of a family: vaginal, anal, oral, hands & body (handjob,
fingering, paizuri, tribadism...) or solo (masturbation). A position ("missionary",
"doggystyle", "cowgirl position") is penetration without saying where: vaginal when the cast
has a pussy to take it, anal between men; the card's Act filter can turn it anal.

A kink entry can need an act: "cross-section, throat" needs an oral one, "x-ray, womb" a
vaginal one, "cum inside" any penetration. Muse draws the kink first and keeps to the acts it
goes with, so an x-ray of a womb never comes with a blowjob. A kink entry that is an act of its
own ("footjob", "pegging", "golden shower") takes the Doing's place.
"""

from __future__ import annotations

import re
from functools import lru_cache

FAMILIES = {"vaginal": "Vaginal", "anal": "Anal", "oral": "Oral", "outer": "Hands & body", "solo": "Solo"}

# casts with a pussy to penetrate and someone to do it (2girls: a strap-on, or an alpha in omegaverse)
VAGINAL_CASTS = {"1girl1boy", "futa_girl", "futa_boy", "harem", "reverse", "mixed", "human_furry", "2girls", "girls"}
MALE_CASTS = {"1boy", "2boys", "boys"}
SOLO_CASTS = {"1girl", "1boy", "futa", "furry", "nonhuman"}

ORAL = re.compile(r"\b(fellatio|deepthroat|irrumatio|blowjob|cunnilingus|69|face sitting|cum in mouth|throat|oral|autofellatio|"
                  r"anilingus|rimjob|licking (?:penis|pussy)|cooperative fellatio|double fellatio|spitroast|toe sucking|foot licking)\b")
ANAL = re.compile(r"\b(anal|pegging|butt plug|anal beads|prostate|mpreg)\b")
VAGINAL = re.compile(r"\b(vaginal|womb|ovum|uterus|cervix|impregnation|insemination|pussy juice)\b")
POSITION = re.compile(r"\b(missionary|cowgirl position|reverse cowgirl position|doggystyle|mating press|amazon position|piledriver|"
                      r"prone bone|lotus position|full nelson|standing sex|sex from behind|suspended congress|spooning|upright straddle|"
                      r"girl on top|boy on top|sex(?! toys?)|double penetration|triple penetration|spitroast|gangbang|group sex|orgy|"
                      r"futa with (?:female|male)|strap-on|double dildo|dildo riding|tentacle sex|tentacle penetration|lineup|"
                      r"partner swap|sandwiched|taking turns|knot|knotting|cum inside|penis inside|internal cumshot|"
                      r"creampie|breeding|stomach bulge|cum inflation)\b")
OUTER = re.compile(r"\b(handjob|double handjob|fingering|footjob|paizuri|cooperative paizuri|thigh sex|frottage|grinding|tribadism|"
                   r"scissoring|breast sucking|licking nipple|breast press|mutual masturbation)\b")
SOLO = re.compile(r"\b(masturbation|presenting|spread pussy|grabbing own breast|penis grab|erection)\b")
# a penis in a mouth: the only oral act a throat x-ray can go with
THROAT = re.compile(r"\b(fellatio|deepthroat|irrumatio|blowjob|autofellatio|spitroast|throat|cum in mouth)\b")
PENIS_CASTS = {"1girl1boy", "2boys", "boys", "harem", "reverse", "mixed", "futa", "futa_girl", "futa_boy", "human_furry", "1boy"}
# kink entries that are an act of their own: the Doing gives way to them
OWN = re.compile(r"\b(footjob|foot licking|toe sucking|pegging|golden shower|peeing on another|face sitting|anilingus|scat)\b")


@lru_cache(maxsize=65536)
def _families(text, cast):
    """(families, a position that does not say where) of an act, for one cast."""
    low = str(text or "").lower()
    fam = set()
    if ORAL.search(low):
        fam.add("oral")
        if THROAT.search(low) or (re.search(r"\b69\b", low) and cast in PENIS_CASTS):
            fam.add("throat")
    if OUTER.search(low):
        fam.add("outer")
    if cast in SOLO_CASTS and (SOLO.search(low) or not fam and not POSITION.search(low)):
        fam.add("solo")
    if ANAL.search(low):
        fam.add("anal")
    if VAGINAL.search(low) and cast in VAGINAL_CASTS:
        fam.add("vaginal")
    generic = False
    if POSITION.search(low) and cast not in SOLO_CASTS:
        if cast in MALE_CASTS:
            fam.add("anal")
        elif not fam & {"anal", "vaginal"}:
            generic = True
    return frozenset(fam), generic


def families(text, cast):
    fam, generic = _families(str(text or ""), cast)
    return set(fam), generic


@lru_cache(maxsize=16384)
def _needs(kink):
    """What act a kink entry needs: a set of 'throat' (a penis in a mouth), 'oral', 'anal', 'vaginal', 'pen' (any
    penetration); 'own' when it is an act."""
    low = str(kink or "").lower()
    out = set()
    if OWN.search(low):
        return frozenset({"own"})
    if THROAT.search(low):
        out.add("throat")
    elif ORAL.search(low):
        out.add("oral")
    if ANAL.search(low):
        out.add("anal")
    if VAGINAL.search(low):
        out.add("vaginal")
    if POSITION.search(low) and not out:
        out.add("pen")
    return frozenset(out)


def needs(kink):
    return set(_needs(str(kink or "")))


def offers(fam, generic, cast):
    """The kinds of act an action (or a set of them) can serve."""
    out = set(fam)
    if generic:
        out.add("pen")
        out.add("anal")
        if cast in VAGINAL_CASTS:
            out.add("vaginal")
    if out & {"anal", "vaginal"}:
        out.add("pen")
    return out


def fits(kink, action, cast, wanted=None):
    """Whether a kink entry and a Doing make one act (of the wanted families, when some are)."""
    need = needs(kink)
    if not need or "own" in need:
        return True
    have = offers(*families(action, cast), cast)
    if wanted:
        have &= set(wanted) | ({"pen"} if wanted & {"anal", "vaginal"} else set()) | ({"throat"} if "oral" in wanted else set())
    return need <= have


def in_family(action, cast, wanted):
    """Whether an action is of one of the wanted families; a bare position counts as vaginal or anal."""
    fam, generic = families(action, cast)
    if fam & wanted:
        return True
    return generic and bool(wanted & ({"anal", "vaginal"} if cast in VAGINAL_CASTS else {"anal"}))


def as_family(action, cast, wanted, rng, kink=""):
    """A bare position made anal when that is what was asked for (and the kink does not want a pussy)."""
    fam, generic = families(action, cast)
    need = needs(kink)
    if not generic or "anal" not in wanted or "vaginal" in need or "anal" in need:
        return action
    if "vaginal" in wanted and cast in VAGINAL_CASTS and rng.random() < 0.5:
        return action
    return action + ", anal"
