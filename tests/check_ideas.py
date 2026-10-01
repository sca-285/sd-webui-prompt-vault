"""Thousands of ideas: tags only, adults only, every body where it belongs."""
import os, sys, re, random, collections
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "tools", "muse_scenes"))
from lint import bad  # tags, never prose
from lib_vault import muse, kinks, when
N = int(os.environ.get("N", 4000))
MALE_ONLY = ("1boy", "2boys", "boys")
FEMALE_ONLY = ("1girl", "2girls", "girls")
problems = collections.Counter(); examples = {}
def bad_(kind, idea):
    problems[kind] += 1; examples.setdefault(kind, idea["positive"])
muse.save_state({"allow_nsfw": True, "ratings": list(muse.RATINGS), "casts": [], "themes": [], "kinks": [], "styles": [], "blacklist": ""})
allk = list(kinks.KINKS)
for i in range(N):
    r = random.Random(i)
    st = {"kinks": r.sample(allk, 1) if i % 3 == 0 else [], "acts": r.sample(["vaginal", "anal", "oral", "outer", "solo"], 1) if i % 4 == 1 else []}
    muse.save_state(st)
    try:
        idea = muse.compose(seed=i)
    except Exception as e:
        problems["error: " + str(e)[:50]] += 1; continue
    pos, c = idea["positive"], idea["cast"]
    low = pos.lower()
    for p in pos.split(","):
        p = p.strip()
        if p and bad(p):
            bad_("prose: " + p, idea)
    if idea["nsfw"] and c in ("animal", "none"): bad_("animals or no humans in NSFW", idea)
    if idea["nsfw"]:
        if muse.MINOR.search(pos): bad_("minor word", idea)
        if "mature" not in pos: bad_("no mature tag", idea)
    if c in MALE_ONLY and re.search(r"\b(pussy|breasts?|vagina|cleavage|futanari|paizuri|cunnilingus)\b", low): bad_(f"female body on {c}", idea)
    if c in FEMALE_ONLY and re.search(r"\b(penis|cock|erection|testicles|fellatio|precum|ejaculation|bulge)\b", low) and "strap-on" not in low and not re.search(r"orc|minotaur|demon|werewolf|alien|tentacle", low): bad_(f"male body on {c}", idea)
    if c == "human_furry" and not re.search(r"1girl, anthro male|1boy, anthro female", pos): bad_("human_furry subject", idea)
    if c in ("furry", "kemono") and not re.search(r"anthro (male|female)", pos): bad_("furry subject", idea)
    parts = {p["slot"]: p["value"] for p in idea["parts"]}
    if parts.get("time"):
        t, w = when.parse(parts["time"])
        if t is None: bad_("unparsed time", idea)
        for slot in muse.UNDER_SKY:
            if parts.get(slot) and not when.fits(parts[slot], t, w):
                bad_(f"sky clash in {slot}: {parts[slot]} / {parts['time']}", idea)
        problems["(with a time part)"] += 0; examples.setdefault("with time", "")
    else:
        sp = parts.get("setting", "")
        if "outdoors" in sp: bad_("outdoors without time", idea)
    from lib_vault import acts as A
    k, a = parts.get("kink", ""), parts.get("action", "")
    wanted = set(st["acts"]) if idea["rating"] == "explicit" else set()
    if idea["rating"] == "explicit" and a and k and not A.fits(k, a, c, wanted): bad_(f"kink/act clash: {a} / {k}", idea)
    if idea["rating"] == "explicit" and "own" in A.needs(k) and a: bad_("own kink with a doing", idea)
    from lib_vault import looks as LK
    if parts.get("job") and parts["job"] not in LK.jobs_for(idea["theme"]): bad_(f"job out of its theme: {parts['job']} in {idea['theme']}", idea)
    if "omegaverse" in pos: bad_("omegaverse", idea)
    if c == "human_furry" and idea["nsfw"]:
        if "anthro male" in pos and not re.search(r"pussy|vagina|pubic hair", low) and muse.state()["anatomy"] and idea["rating"] != "suggestive": bad_("hf body", idea)
real = sum(v for k, v in problems.items() if not k.startswith("error: Nothing matches"))  # a random kink and act can rule each other out
print(N, "ideas;", real, "problems")
for k, v in problems.most_common(40):
    print(f"  {v:5d}  {k}  ::  {examples.get(k, '')[:220]}")
sys.exit(1 if real else 0)
