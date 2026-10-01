import os, re, sys, collections
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from lib_vault import muse
muse.save_state({"allow_nsfw": True, "ratings": list(muse.RATINGS), "themes": [], "casts": [], "sizes": []})
want = {
    "girls": {3: "3girls", 4: "4girls", 5: "5girls", 6: "6+girls"},
    "boys": {3: "3boys", 4: "4boys", 5: "5boys", 6: "6+boys"},
    "harem": {3: "1boy, 2girls", 4: "1boy, 3girls", 5: "1boy, 4girls", 6: "1boy, 6+girls"},
    "reverse": {3: "1girl, 2boys", 4: "1girl, 3boys", 5: "1girl, 4boys", 6: "1girl, 6+boys"},
}
table = collections.Counter()
for kind in muse.GROUP_SIZES:
    for n in muse.SIZES:
        muse.save_state({"casts": [kind], "sizes": [n]})
        try:
            ideas = [muse.compose(seed=i) for i in range(60)]
        except muse.store.VaultError as e:
            assert kind == "mixed" and n == 3, (kind, n, e); print(f"{kind} {n}: none (as it should be)"); continue
        for idea in ideas:
            p = idea["positive"]
            assert idea["cast"] == kind and idea["size"] == n, idea
            if kind in want: assert p.startswith(want[kind][n]), (kind, n, p)
            if kind == "mixed":
                g, b = re.match(r"(\d)girls, (\d)boys", p).groups(); assert int(g) + int(b) == min(n, 6) and int(g) >= 2 and int(b) >= 2, p
            if idea["nsfw"]: assert "mature" in p and not muse.MINOR.search(p), p
            if idea["title"] in ("Threesome, ffm", "Threesome, mmf"): assert n == 3, (idea["title"], n)
            if idea["title"] in ("Gangbang", "Harem bed"): assert n >= 4
            if idea["title"] == "Orgy": assert n >= 5
            table[(kind, n, idea["rating"])] += 1
print("kind     size" + "".join(f"{r:>12}" for r in muse.RATINGS))
for kind in muse.GROUP_SIZES:
    for n in muse.SIZES:
        print(f"{kind:8} {('6+' if n == 6 else n)!s:4}" + "".join(f"{('x' if table[(kind, n, r)] else '-'):>12}" for r in muse.RATINGS))
# lock and roll keep the group as it was
muse.save_state({"casts": ["mixed"], "sizes": [5]})
i = muse.compose(seed=1)
parts = {p["slot"]: p["value"] for p in i["parts"]}
for k in range(15):
    j = muse.compose(scene_id=i["scene"], cast=i["cast"], size=i["size"], girls=i["girls"], keep=dict(parts), roll="action", seed=k)
    assert j["positive"].split(", multiple")[0] == i["positive"].split(", multiple")[0] and j["cast_label"] == i["cast_label"], (i["cast_label"], j["cast_label"])
print("lock/roll keeps", i["cast_label"])
print("GROUPS OK")
