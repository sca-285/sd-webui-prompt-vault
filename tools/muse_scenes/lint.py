"""Tags, never prose: every piece of every Muse list is a short tag."""
import glob, json, os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
os.chdir(REPO)
BAD = {"the", "a", "an", "she", "he", "her", "his", "him", "hers", "they", "them", "their", "herself", "himself", "themselves", "others", "everyone", "while", "who", "is", "are", "was", "being", "each", "its", "it"}
MAXW = int(os.environ.get("MAXW", 4))
def pieces(v):
    if isinstance(v, dict):
        for x in v.values(): yield from pieces(x)
    elif isinstance(v, list):
        for x in v: yield from pieces(x)
    elif isinstance(v, str):
        for p in v.split(","):
            p = p.strip()
            if p: yield p
DANBOORU_OK = {"looking to the side", "looking at the viewer"}  # real tags that read like words


def bad(p):
    if p.lower() in DANBOORU_OK:
        return False
    words = re.findall(r"[a-z']+(?:-[a-z']+)*", p.lower())
    return any(w in BAD for w in words) or len(p.split()) > MAXW
hits = {}
SKIP = {"title", "theme", "rating", "mood", "id", "use", "sizes"}
def walk(d, where):
    if isinstance(d, dict):
        for k, v in d.items():
            if k in SKIP: continue
            walk(v, where)
    elif isinstance(d, list):
        for x in d: walk(x, where)
    elif isinstance(d, str):
        for p in pieces(d):
            if bad(p): hits.setdefault(p, where)
for f in sorted(glob.glob("data/muse_scenes/*.json")):
    walk(json.load(open(f)), os.path.basename(f))
from lib_vault import kinks
walk({k: v.get("levels", v) for k, v in kinks.KINKS.items()}, "kinks.py")
from lib_vault import looks
walk({k: v for k, v in vars(looks).items() if k.isupper() and k != "JOBS"}, "looks.py")
walk({k: list(v[1:]) for k, v in looks.JOBS.items()}, "looks.py jobs")
print(len(hits), "prose pieces")
for p, w in list(hits.items())[:int(os.environ.get("SHOW", 40))]:
    print(f"  {w}: {p}")
