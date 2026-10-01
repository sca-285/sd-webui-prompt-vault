"""Every chip of every tray, in every state of the other filters (one choice or all), as the card counts it."""
import os, sys, itertools
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from lib_vault import muse
MIN = int(os.environ.get("MIN", 25))
cat = muse.catalogue()
groups = cat["group_sizes"]
themes, casts = cat["themes"], [c for c, _ in cat["casts"]]
ratings, sizes = [r for r, _ in cat["ratings"]], [n for n, _ in cat["sizes"]]
index = [(cat["themes"][t], set(cat["castsets"][c]), r, cat["sizesets"][z], n) for t, c, r, z, n in cat["index"]]

def count(T, C, R, N):
    n = 0
    for t, sc, r, ss, many in index:
        if r not in R or (T and t not in T):
            continue
        ok = lambda c: (not C or c in C) and (c not in groups or any(x in groups[c] and (not N or x in N) for x in ss))
        if any(ok(c) for c in sc):
            n += many
    return n

LEVELS = {}
for t, c, r, z, n in cat["index"]: LEVELS.setdefault(cat["themes"][t], set()).add(r)

def impossible(T, C, R, N):
    if C in ({"none"}, {"animal"}) and "sfw" not in R: return True
    if C and all(c in muse.NSFW_ONLY for c in C) and R <= {"sfw"}: return True
    lv = set().union(*(LEVELS[t] for t in T)) if T else set(ratings)
    if not (lv & R): return True
    if C and all(c in ("none", "animal") for c in C) and "sfw" not in lv: return True
    if C and all(c in muse.NSFW_ONLY for c in C) and lv <= {"sfw"}: return True
    if C == {"mixed"} and N == {3}: return True
    return False

bad, states, checked = [], 0, 0
for T, C, R, N in itertools.product([set()] + [{t} for t in themes], [set()] + [{c} for c in casts],
                                    [set(ratings)] + [{r} for r in ratings], [set()] + [{n} for n in sizes]):
    states += 1
    for key, opts in (("themes", themes), ("casts", casts), ("ratings", ratings), ("sizes", sizes)):
        for o in opts:
            st = {"themes": T, "casts": C, "ratings": R, "sizes": N}
            st[key] = {o}
            n = count(st["themes"], st["casts"], st["ratings"], st["sizes"])
            checked += 1
            if n < MIN and not (n == 0 and impossible(st["themes"], st["casts"], st["ratings"], st["sizes"])):
                bad.append((key, o, {k: sorted(v) for k, v in st.items() if v and k != key}, n))
print(f"{states} filter states, {checked} chips: {len(bad)} under {MIN} (impossible ones aside)")
for b in bad[:25]:
    print("  ", b)
sys.exit(1 if bad else 0)
