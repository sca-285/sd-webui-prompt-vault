"""Every act x cast (x kink) the card offers: Muse makes an idea of it, of that family and kink."""
import os, sys
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from lib_vault import muse, acts, kinks
cat = muse.catalogue()
bad = n = 0
for f, casts in cat["act_casts"].items():
    for c in casts:
        muse.save_state({"allow_nsfw": True, "ratings": ["explicit"], "acts": [f], "casts": [c], "kinks": [], "themes": []})
        d = muse.compose(seed=n); n += 1
        a = {p["slot"]: p["value"] for p in d["parts"]}.get("action", "")
        if not acts.in_family(a.replace(", anal", ""), c, {f}) and not (f == "anal" and "anal" in a):
            bad += 1; print("act miss", f, c, a)
for k in kinks.KINKS:
    for f, casts in cat["kink_acts"][k].items():
        for c in casts:
            muse.save_state({"allow_nsfw": True, "ratings": ["explicit"], "acts": [f], "casts": [c], "kinks": [k], "themes": []})
            try:
                d = muse.compose(seed=n); n += 1
            except Exception as e:
                bad += 1; print("fail", k, f, c, e); continue
            p = {x["slot"]: x["value"] for x in d["parts"]}
            if not p.get("kink"): bad += 1; print("no kink", k, f, c)
            elif p.get("action") and not acts.fits(p["kink"], p["action"], c, {f}): bad += 1; print("clash", k, f, c, p)
print(n, "combinations,", bad, "problems")
sys.exit(1 if bad else 0)
