"""Muse's vocabulary into the Vault's default library: one vocabulary for the whole extension."""
import json, os, sys
REPO = os.environ.get("REPO") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location("kinks", os.path.join(REPO, "lib_vault", "kinks.py"))
kinks = importlib.util.module_from_spec(spec); spec.loader.exec_module(kinks)
from lib import ANTHROS, SEX

path = os.path.join(REPO, "data", "default_library.json")
data = json.load(open(path, encoding="utf-8"))
lib = data["library"]


def cat(name):
    for c in lib:
        if c.split(". ", 1)[-1] == name.split(". ", 1)[-1]:
            return lib[c]
    lib[name] = {}
    return lib[name]


def put(category, group, tags):
    groups = cat(category)
    groups[group] = list(dict.fromkeys(t.strip() for t in tags if t.strip()))


# ---- poses, by sex and posture (Muse reads the posture and sex from the group's name)
P = "06. Pose & Gesture (SFW)"
put(P, "Female Standing", ["hand on hip, contrapposto", "hair flip", "twirling hair", "standing on tiptoes", "skirt hold, curtsey",
                           "self hug", "crossed legs, standing", "blowing kiss", "hands behind back, leaning forward",
                           "looking back, hand on hip", "arms up, stretching", "v over eye", "finger to chin", "walking, hip sway", "hand on headwear"])
put(P, "Female Seated", ["sitting, legs tucked", "sitting, crossed legs", "hugging own knee", "seiza, hands on lap",
                         "chin on hands, elbows on knees", "leaning back, arms support", "dangling legs", "sitting, crossed ankles"])
put(P, "Female Lying", ["on stomach, legs up", "on side, head rest", "on back, hair spread", "fetal position"])
put(P, "Male Standing", ["arms crossed", "hands in pockets", "thumbs in pockets", "leaning on shoulder", "hand in own hair",
                         "rolling up sleeves", "adjusting cuffs", "wide stance, arms crossed", "hand in pocket, looking away",
                         "hand on own neck", "jacket over shoulder", "clenched hands"])
put(P, "Male Seated", ["spread legs, elbows on knees", "ankle on knee", "slouching, arm over backrest", "leaning forward, hands clasped",
                       "sitting backwards, chair"])
put(P, "Male Lying", ["on back, hands behind head", "propped on elbow", "sprawled"])
N = "18. NSFW — Body, Pose & Act"
put(N, "Female Standing (NSFW)", ["covering breasts", "hands behind head, chest out", "arched back, hand on hip",
                                  "bent over, hanging breasts", "looking back, hands on own ass", "panty pull",
                                  "against wall, leg up", "spread pussy"])
put(N, "Female Lying (NSFW)", ["on back, spread legs", "on back, knees up, spread legs", "legs up, holding legs", "on side, leg up",
                               "on stomach, ass up", "m legs"])
put(N, "Female Kneeling (NSFW)", ["all fours, looking back", "kneeling, spread legs", "squatting, spread legs", "top-down bottom-up",
                                  "kneeling, hands on thighs, chest out"])
put(N, "Male Standing (NSFW)", ["flexing, nude", "penis grab", "erection, hands on hips", "against wall, erection",
                                "waistband pull"])
put(N, "Male Seated (NSFW)", ["sitting, spread legs, erection", "leaning back, erection", "male masturbation, sitting"])
put(N, "Male Lying (NSFW)", ["on back, erection", "on side, penis grab"])

# ---- styles
S = "13. Style & Medium"
put(S, "Pixel & Retro Games", ["pixel art", "8-bit", "16-bit", "32-bit sprite", "dithered pixel art", "isometric pixel art", "gameboy palette",
                               "low-res crt scanlines"])
put(S, "Graphic & Silhouette", ["silhouette", "backlit silhouette, sunset", "shadow silhouette", "stencil art", "flat vector illustration",
                                "minimalism", "negative space", "papercut silhouette", "propaganda poster"])
put(S, "Retro & Vapor", ["vaporwave", "synthwave", "outrun", "80s airbrush", "y2k aesthetic", "lo-fi aesthetic", "90s magazine scan", "retro pin-up"])
put(S, "Craft & Mixed Media", ["paper cutout", "stained glass", "mosaic", "embroidery", "collage", "origami", "linocut print", "cross-stitch"])
put(S, "Photo Experiments", ["double exposure", "infrared photography", "tilt-shift", "long exposure light trails", "cyanotype", "lomography",
                             "fisheye lens", "motion blur"])
put(S, "Anime Eras", ["1980s anime", "1990s anime cel", "2000s anime", "modern anime", "anime screencap", "retro anime ova"])
put(S, "Sketch & Line", ["lineart", "monochrome lineart", "rough sketch", "blueprint", "technical drawing", "ballpoint pen sketch"])
put(S, "Dark & Surreal", ["surrealism", "dark surrealism", "glitch art", "liminal space photography", "horror manga style", "eldritch art"])

# ---- body
put("03. Character Body", "Prosthetics & Implants", kinks.PROSTHETIC)
A = "24. NSFW — Anatomy"
put(A, "Breasts", kinks.BREASTS + ["cleavage"])
put(A, "Nipples", kinks.NIPPLES)
put(A, "Pussy", kinks.PUSSY)
put(A, "Penis", kinks.PENIS + ["testicles", "erection", "bulge"])
put(A, "Male Chest", kinks.CHEST)
put(A, "Body Hair", kinks.BODY_HAIR + ["hairy pussy", "chest hair"])
put(A, "Futanari", ["futanari", "futanari, testicles", "futanari, no testicles", "penis and pussy", "futanari masturbation"])
put(A, "Anthro Male", sorted({t for v in kinks.ANTHRO_PENIS.values() for x in v for t in x.split(", ")}))
put(A, "Anthro Female", sorted({t for v in kinks.ANTHRO_PUSSY.values() for x in v for t in x.split(", ")}))

# ---- sex positions
X = "21. NSFW — Sex Positions"
put(X, "Oral & Manual", ["cunnilingus", "69", "breast sucking", "nipple licking", "fingering", "handjob", "rimjob", "anal rimming", "deepthroat",
                         "face sitting", "mutual handjob", "scissoring", "tribadism"])
put(X, "Futanari Acts", sorted({a for k in ("futa", "futa_girl", "futa_boy") for v in SEX[k].values() for a in v if "{" not in a}))
put(X, "Interspecies", ["knotting", "human with furry", "human on furry", "furry on human", "interspecies", "mating press", "size difference"])

# ---- anthros
F = "22. Furry & Anthro"
groups = {"Canines": ("wolf", "fox", "husky", "german shepherd", "hyena"), "Felines": ("cat", "tiger", "lion", "leopard", "cheetah", "lynx", "panther"),
          "Hooved": ("deer", "horse", "zebra", "cow", "bull", "goat"), "Small Mammals": ("rabbit", "otter", "mouse", "rat", "squirrel"),
          "Bears": ("bear", "panda"), "Birds": ("eagle", "owl", "raven"), "Sea": ("shark", "orca", "dolphin"),
          "Reptiles & Dragons": ("lizard", "crocodile", "dragon")}
for g, kinds_ in groups.items():
    put(F, g, list(kinds_))
feats = sorted({t for _, both, f, m in ANTHROS for x in both + f + m for t in x.split(", ")})
put(F, "Fur, Scales & Feathers", [t for t in feats if any(w in t for w in ("fur", "scale", "feather", "skin", "stripe", "spot", "print", "marking"))])
put(F, "Horns, Wings & Tails", [t for t in feats if any(w in t for w in ("horn", "antler", "wing", "tail", "mane", "fin", "hoove", "ear", "beak", "talon", "whisker", "gill", "teeth", "snout", "paw"))])
put(F, "Anthro Basics", ["1furry", "anthro", "anthro female", "anthro male", "furry", "human with furry", "human on furry", "furry on human",
                         "digitigrade", "paw pads", "muzzle", "snout", "kemono"])

# ---- kinks
K = "23. NSFW — Kinks & Fetish"
for k, v in kinks.KINKS.items():
    tags = []
    for lvl in ("suggestive", "nude", "explicit"):
        for items in (v.get(lvl) or {}).values():
            tags += items
    put(K, v["label"], tags)

# ---- the looks, camera, light and colour Muse draws from (lib_vault/looks.py): one vocabulary
spec = importlib.util.spec_from_file_location("looks", os.path.join(REPO, "lib_vault", "looks.py"))
looks = importlib.util.module_from_spec(spec); spec.loader.exec_module(looks)


def merge(category, group, tags):
    groups = cat(category)
    groups[group] = list(dict.fromkeys(groups.get(group, []) + [t.strip() for t in tags if t.strip()]))


B, F2, A2 = "03. Character Body", "04. Face, Hair & Features", "15. Accessories & Props"
put(B, "Female Build", looks.BUILD["f"] + looks.BUILD_DETAIL["f"])
put(B, "Male Build", looks.BUILD["m"] + looks.BUILD_DETAIL["m"])
merge(B, "Skin Tone", looks.SKIN_TONE["f"] + looks.SKIN_TONE["m"])
merge(B, "Skin Texture", looks.SKIN_TEXTURE)
put(B, "Skin Details", looks.SKIN_DETAIL)
merge(F2, "Hair Color", looks.HAIR_COLOR)
put(F2, "Hairstyles (women)", looks.HAIR_STYLE["f"])
put(F2, "Hairstyles (men)", looks.HAIR_STYLE["m"])
put(F2, "Hairstyles (anyone)", looks.HAIR_STYLE["u"])
put(F2, "Facial Hair", looks.FACIAL_HAIR)
merge(F2, "Eye Color", looks.EYE_COLOR)
put(F2, "Eye Details", looks.EYE_DETAIL)
merge(F2, "Brows & Lashes", looks.EYEBROWS)
merge(F2, "Nose & Lips", looks.NOSE + looks.LIPS)
merge(F2, "Makeup", looks.MAKEUP["f"] + looks.MAKEUP["m"])
merge(F2, "Gaze", looks.GAZE["solo"] + looks.GAZE["people"])
merge(F2, "Mouth Action", looks.MOUTH)
put(A2, "Women's Accessories", looks.ACCESSORIES["f"])
put(A2, "Men's Accessories", looks.ACCESSORIES["m"])
C8, L9, C10 = "08. Camera & Composition", "09. Lighting", "10. Color & Grade"
merge(C8, "Shot Size", looks.SHOT)
merge(C8, "Angle Height", looks.ANGLE)
merge(C8, "Viewpoint", looks.VIEW)
merge(C8, "Framing Rules", looks.FRAMING)
merge(L9, "Quality", looks.LIGHT_QUALITY)
merge(L9, "Mood Lighting", looks.LIGHT_MOOD)
merge(L9, "Edge & Separation", looks.LIGHT_SUPPORT)
merge(L9, "Volume & Air", looks.LIGHT_VOLUME)
merge(L9, "Daylight Natural", [t for v in looks.NATURAL.values() for t in v] + [t for v in looks.NATURAL_SKY.values() for t in v])
merge(C10, "Looks", looks.COLOR)
R16 = "16. Beings, Roles & FX"
# fiction: a job that lives only in fantasy, science-fiction, steampunk or after-the-end themes
FICTION_THEMES = {"Fantasy", "Myth", "Sci-fi", "Steampunk", "Post-apocalypse"}
fantasy = {j for j, v in looks.JOBS.items() if set(v[0]) <= FICTION_THEMES}
merge(R16, "Professions", [j for j in looks.JOBS if j not in fantasy])
merge(R16, "Fantasy Roles", [j for j in looks.JOBS if j in fantasy])
merge(R16, "VFX", [v[4] for v in looks.JOBS.values() if v[4]])
spec2 = importlib.util.spec_from_file_location("genlib", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib.py"))
merge(R16, "Creatures", sorted({p.split(", ")[2] for kind in ("mythic", "monster", "synth") for p in __import__("lib").BEINGS[kind]}))
merge("22. Furry & Anthro", "Anthro Basics", ["kemono"])
merge("14. Attire", "Uniforms", sorted({t for v in looks.JOBS.values() for w in (v[1], v[2]) for t in w.split(", ")}))

# ---- Muse's wider vocabulary (lib_vault/banks.py): wardrobes, light sources, styles, doings
spec3 = importlib.util.spec_from_file_location("banks", os.path.join(REPO, "lib_vault", "banks.py"))
banks = importlib.util.module_from_spec(spec3); spec3.loader.exec_module(banks)
pieces = lambda items: sorted({t for x in items for t in x.split(", ") if t})
for key, label in (("casual", "Casual"), ("cozy", "Loungewear & Sleepwear"), ("formal", "Formal & Evening"), ("business", "Business"),
                   ("sporty", "Sportswear"), ("beach", "Swimwear"), ("outdoor", "Outdoor"), ("winter", "Winter"), ("street", "Streetwear"),
                   ("party", "Party & Club"), ("rustic", "Rustic"), ("fantasy", "Fantasy Wear"), ("historical", "Historical Wear"),
                   ("scifi", "Sci-fi Wear"), ("steampunk", "Steampunk Wear"), ("wasteland", "Wasteland Wear"), ("nautical", "Nautical"),
                   ("stage", "Stage & Costume"), ("retro", "Retro"), ("festive", "Festive & Costumes")):
    merge("14. Attire", label, pieces(banks.WARDROBE[key]["f"] + banks.WARDROBE[key]["m"]))
merge("17. NSFW — Clothing & Tease", "Lingerie", pieces(banks.WARDROBE["lingerie"]["f"] + banks.WARDROBE["lingerie"]["m"]))
merge(L9, "Light Sources", pieces(x for v in banks.LIGHT_SOURCE.values() for x in v))
merge("13. Style & Medium", "Everyday Styles", pieces(banks.STYLE_ANY))
merge("07. Interaction & Staging (SFW)", "Doings", pieces(banks.ACT_ANY["solo"] + banks.ACT_MODERN["solo"]))  # not a Pose category: Muse would take them for poses
merge("07. Interaction & Staging (SFW)", "Together", pieces(banks.ACT_ANY["pair"] + banks.ACT_ANY["groups"] + banks.ACT_MODERN["pair"]
                                                               + banks.GESTURE_MORE["pair"] + banks.GESTURE_MORE["groups"]))
merge("08. Camera & Composition", "Shot Size", pieces(banks.SHOT_PEOPLE + banks.SHOT_PLACE))
merge(R16, "VFX", banks.FX_ANY)

# keep the categories in their numbered order
data["library"] = {k: lib[k] for k in sorted(lib, key=lambda c: int(c.split(".")[0]) if c.split(".")[0].isdigit() else 99)}
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(path, "a").write("\n")
n = sum(len(t) for g in data["library"].values() for t in g.values())
print("default library:", len(data["library"]), "categories,", n, "tags")
