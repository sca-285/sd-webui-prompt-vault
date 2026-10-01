"""Every kink x level x cast it serves x theme it belongs to: how many scenes take it."""
import os, sys, collections
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from lib_vault import muse, kinks
MIN = int(os.environ.get("MIN", 25))
scenes = muse.load_scenes()
themes = list(dict.fromkeys(s["theme"] for s in scenes))
low, cells = [], 0
_cc = [c for c, _ in muse.catalogue()["casts"]]
for k in kinks.KINKS:
    for lvl in ("suggestive", "nude", "explicit"):
        for c in [c for c, _ in muse.catalogue()["casts"]] if not globals().get("_cc") else _cc:
            if not kinks.entries(k, lvl, c, muse.ALIASES):
                continue
            for t in themes:
                if not kinks.themed(k, t) or not any(s["theme"] == t and s["rating"] == lvl for s in scenes):
                    continue
                n = sum(1 for s in scenes if s["theme"] == t and s["rating"] == lvl and c in s["casts"])
                if t == "Red light" or n or True:
                    cells += 1
                    if n < MIN:
                        low.append((k, lvl, c, t, n))
print(cells, "kink cells,", len(low), "under", MIN)
for x in low[:20]: print("  ", x)
sys.exit(1 if low else 0)
