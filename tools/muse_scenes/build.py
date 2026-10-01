"""Muse's scenes, written again: python3 tools/muse_scenes/build.py

Every t_*.py is a theme or a few (places, their spots, what people do and wear there); lib.py
turns them into data/muse_scenes/*.json. lint.py checks that every entry is tags, not prose.
library_add.py puts Muse's vocabulary in data/default_library.json. SKIES=1 lists each spot's
kind of space (outdoors, a window on the sky, a closed room) for review; skies.py corrects it."""
import glob, os, runpy, sys, collections
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import lib
for f in sorted(glob.glob(os.path.join(here, "t_*.py"))):
    runpy.run_path(f)
if os.environ.get("SKIES"):
    by = collections.defaultdict(list)
    for stem, place, zone, exp in lib.SKIES:
        by[(stem, place)].append(f"{zone}={exp}")
    for (stem, place), zs in by.items():
        if len(zs) >= 3:
            print(f"{stem:12s} {place:22s} " + " | ".join(dict.fromkeys(zs)))
