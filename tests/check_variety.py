"""Every part of a card has enough to roll through: rolled again and again (each roll avoiding what the
part has already been, as the card does), it gives ten different values or more."""
import collections, os, sys
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from lib_vault import muse
N, ROLLS, WANT = int(os.environ.get("N", 30)), 12, 10
# parts that are only as wide as their world: a theme's jobs, the skies a place can have, the subject of a being
NARROW = {"job", "time", "subject", "body", "fx", "kink", "pet"}
muse.save_state({"allow_nsfw": True, "ratings": list(muse.RATINGS), "themes": [], "casts": [], "kinks": [], "acts": []})
low, cells = collections.Counter(), collections.Counter()
for i in range(min(N, 60)):
    d = muse.compose(seed=i)
    parts = {p["slot"]: p["value"] for p in d["parts"]}
    for slot, value in parts.items():
        if not value or slot in NARROW:
            continue
        seen, cur = {value}, dict(parts)
        for k in range(ROLLS):
            j = muse.compose(scene_id=d["scene"], cast=d["cast"], size=d["size"], girls=d["girls"], keep=cur, roll=slot,
                             seed=1000 * i + k, avoid=list(seen))
            cur = {p["slot"]: p["value"] for p in j["parts"]}
            if cur.get(slot):
                seen.add(cur[slot])
        cells[slot] += 1
        if len(seen) < WANT:
            low[slot] += 1
            print(f"  {slot}: {len(seen)} in {d['title']} ({d['cast']}, {d['rating']})")
bad = {s: n for s, n in low.items() if n > cells[s] * 0.1}  # one part in ten may sit in a narrow place
print(sum(cells.values()), "parts rolled;", "too few for: " + ", ".join(sorted(bad)) if bad else "every part has enough")
sys.exit(1 if bad else 0)
