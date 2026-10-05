import base64, json, os, re, sys
sys.path.insert(0, os.environ["STUB"]); sys.path.insert(0, os.getcwd())
from lib_vault import muse, api
from fastapi import FastAPI
from fastapi.testclient import TestClient
app = FastAPI(); api.register(app); c = TestClient(app); B = "/prompt-vault/api"
nx = lambda **b: c.post(B + "/muse/next", json=b)

snap = c.get(B + "/muse").json()
cat = snap["catalogue"]
print("themes", len(cat["themes"]), "casts", [x[0] for x in cat["casts"]], "scenes", sum(r[4] for r in cat["index"]))
assert snap["state"]["enabled"] is False and snap["state"]["ratings"] == ["sfw"]

for _ in range(300):
    i = nx().json()["idea"]; assert not i["nsfw"]
print("sample:", i["title"], "|", i["positive"])

# explicit + 2girls only
c.post(B + "/muse/state", json={"allow_nsfw": True, "ratings": ["explicit"], "casts": ["2girls"]})
for n in range(300):
    i = nx().json()["idea"]
    assert i["rating"] == "explicit" and i["cast"] == "2girls", i
    assert i["positive"].startswith("2girls, yuri, mature"), i["positive"]
    assert not re.search(r"\b(penis|fellatio|his|him)\b", i["positive"]), i["positive"]
    assert "negative" not in i and not muse.MINOR.search(i["positive"])
print("2girls explicit:", i["positive"])

# nsfw off blocks explicit
c.post(B + "/muse/state", json={"allow_nsfw": False})
r = nx(); assert r.status_code == 400, r.json(); print("nsfw off:", r.json()["error"])

# lock and roll keep the scene
c.post(B + "/muse/state", json={"ratings": ["sfw"], "casts": ["1girl"], "themes": ["Portrait"]})
i = nx().json()["idea"]
parts = {p["slot"]: p["value"] for p in i["parts"]}
j = nx(scene=i["scene"], cast=i["cast"], keep={"outfit": parts["outfit"], "setting": parts["setting"]}).json()["idea"]
pj = {p["slot"]: p["value"] for p in j["parts"]}
assert j["scene"] == i["scene"] and pj["outfit"] == parts["outfit"] and pj["setting"] == parts["setting"]
keep = {k: v for k, v in parts.items() if k != "action"}
full = dict(parts)
changed = 0
for _ in range(20):
    k = nx(scene=i["scene"], cast=i["cast"], keep=full, roll="action").json()["idea"]
    pk = {p["slot"]: p["value"] for p in k["parts"]}
    assert all(pk[s] == v for s, v in keep.items()), (pk, keep)
    changed += pk["action"] != parts["action"]
assert changed == 20, changed
print("lock/roll ok:", k["positive"])

# a scene id that does not exist
r = nx(scene="x:nope:0"); assert r.status_code == 400

# every combination of one cast x one rating that the catalogue claims works
c.post(B + "/muse/state", json={"allow_nsfw": True, "themes": []})
for cast, _ in cat["casts"]:
    for rating in muse.RATINGS:
        has = any(cast in cat["castsets"][row[1]] and row[2] == rating for row in cat["index"])
        c.post(B + "/muse/state", json={"casts": [cast], "ratings": [rating]})
        r = nx()
        assert (r.status_code == 200) == has, (cast, rating, r.json())
        if has: assert r.json()["idea"]["cast"] == cast
print("every cast x rating ok")

# old state file and old pack format still load
c.post(B + "/muse/state", json={"packs": ["x"], "target": "img2img"})
os.makedirs(muse.user_scene_dir(), exist_ok=True)
json.dump({"id": "mine", "name": "Mine", "subjects": ["cat"], "styles": ["oil"]}, open(os.path.join(muse.user_scene_dir(), "old.json"), "w"))
cat2 = c.get(B + "/muse").json()["catalogue"]
assert "Mine" in cat2["themes"]
c.post(B + "/muse/state", json={"themes": ["Mine"], "casts": [], "ratings": ["sfw"]})
print("old pack:", nx().json()["idea"]["positive"])

# blacklist
c.post(B + "/muse/state", json={"themes": ["Portrait"], "blacklist": "1girl, rain", "casts": []})
for _ in range(100):
    i = nx().json()["idea"]
    assert not re.search(r"(?<!\w)(1girl|rain)(?!\w)", i["positive"], re.I), i["positive"]

# Build around: your tags read into parts, a scene that has them, the rest drawn around
plan = muse.seed_plan("masterpiece, 1girl, red hair, bikini, beach, sunset, smile, <lora:x:0.7>")
assert plan["cast"] == "1girl" and plan["parts"]["hair"] == ["red hair"] and plan["parts"]["outfit"] == ["bikini"], plan
assert plan["parts"]["setting"] == ["beach"] and plan["parts"]["time"] == ["sunset"], plan
assert "masterpiece" in plan["front"] and "<lora:x:0.7>" in plan["front"], plan
c.post(B + "/muse/state", json={"themes": [], "casts": [], "blacklist": "", "ratings": ["sfw"], "allow_nsfw": False,
                                "fixed_prompt": "1girl, red hair, bikini, beach, sunset", "prompt_mode": "around"})
for _ in range(20):
    i = nx().json()["idea"]
    low = i["positive"].lower()
    assert i["cast"] == "1girl" and all(t in low for t in ("red hair", "bikini", "beach", "sunset")), i["positive"]
    assert "beach" in json.dumps(i["parts"]).lower() and {"hair", "outfit", "setting", "time"} <= set(i["seeded"]), i
    assert not any(p["slot"] == "job" and p["value"] for p in i["parts"]), i  # your wear, not a job's
# rolling a part of yours gives it back to Muse
parts = {p["slot"]: p["value"] for p in i["parts"]}
j = nx(scene=i["scene"], cast=i["cast"], keep=parts, roll="hair").json()["idea"]
new_hair = {p["slot"]: p["value"] for p in j["parts"]}["hair"]
assert new_hair != parts["hair"], new_hair  # Muse drew another; it may be red again by chance ("red hair, ponytail")
assert ("hair" in j["seeded"]) == ("red hair" in [t.strip() for t in new_hair.split(",")]), (new_hair, j["seeded"])
# Keep in front: the idea itself does not carry it (the card puts it in front)
c.post(B + "/muse/state", json={"prompt_mode": "front"})
assert "seeded" in nx().json()["idea"] and not nx().json()["idea"]["seeded"]
c.post(B + "/muse/state", json={"fixed_prompt": ""})
print("ALL OK")
