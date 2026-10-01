"""The default library's prose entries as tags: what reads like a sentence becomes what a prompt says."""
import json, os
REPO = os.environ.get("REPO") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M = {
 "tying a shoe": "tying shoelaces", "looking up from the floor": "on floor, looking up", "glancing back while walking": "walking, looking back",
 "skidding to a stop": "skidding", "playing with a strand": "playing with own hair", "blowing a kiss": "blowing kiss",
 "hanging from a bar": "arms above head", "reaching up to a shelf": "reaching up", "turning at the waist": "twisted torso",
 "reading a book": "reading book", "holding a cup with both hands": "holding cup, both hands", "using a phone": "holding phone",
 "drawing a bow": "drawing bow", "holding a lantern": "holding lantern", "opening a door": "opening door",
 "facing each other": "facing another", "dancing as a pair": "dancing together", "crouched beside a dog": "squatting, dog",
 "hand on a wolf's neck": "petting wolf", "framed in a doorway": "in doorway", "sitting in a window niche": "sitting, window niche",
 "on a staircase landing": "stairs landing", "under an arch": "under arch", "against a column": "against pillar", "on a rooftop ledge": "rooftop ledge",
 "quiet after the storm": "after storm, calm", "peek around a corner": "peeking out, corner", "frame within a frame": "frame within frame",
 "against the light": "backlighting", "fluorescent supermarket aisle after hours": "empty supermarket, night, fluorescent light",
 "sitting so a hem rides up": "sitting, skirt rise", "standing so a shirt gaps": "shirt gap", "belt undone but pants on": "unbuckled belt",
 "strap slipping off one shoulder": "strap slip", "shirt riding up to ribs": "shirt lift, midriff", "jacket open with nothing aligned underneath": "open jacket, no shirt",
 "coat held closed with one hand": "holding coat closed", "slit to the thigh": "thigh slit", "slit to the hip": "high slit",
 "open flannel over bare chest": "open flannel, bare chest", "shirt used as a short dress": "shirt dress, oversized shirt",
 "sweater pulled off one arm": "sweater, off shoulder", "hoodie unzipped down the front": "unzipped hoodie",
 "pulling shirt off over head": "undressing, shirt lift", "stepping out of a skirt": "skirt down, undressing", "dress pooled at the waist": "dress pull, waist",
 "dress pooled at the feet": "dress on floor", "catching a falling strap": "strap slip, holding strap", "clothes in a pile": "pile of clothes",
 "clothes on a chair": "clothes on chair", "shirt on the floor": "shirt on floor", "only a necklace left": "nude, necklace",
 "only an open shirt left": "open shirt, nude", "using a shirt as cover": "covering with shirt", "sheet as the only cover": "nude cover, bed sheet",
 "bath towel knot at chest": "towel, towel knot", "bikini top undone at the back": "untied bikini top", "bikini top held in place by hands": "holding bikini top",
 "unbuttoned linen shirt over swimsuit": "open shirt, swimsuit", "open-crotch styling implied by cut": "crotchless", "zipper down the front": "front zipper, unzipped",
 "unbuttoned dress shirt no undershirt": "unbuttoned shirt, bare chest", "shirtless with belt still fastened": "shirtless, belt",
 "hands over groin over clothes": "covering crotch", "kneeling so a shirt becomes a dress": "kneeling, oversized shirt",
 "sitting on heels to keep a hem down": "seiza, skirt hold", "leaning so a neckline falls forward": "leaning forward, downblouse",
 "clothes just out of frame": "implied nudity", "stubble on jaw and chest": "stubble, chest hair",
 "sitting nude on the edge of the bed": "nude, sitting on bed", "sitting on a chair backwards": "sitting backwards, chair", "straddling a chair": "straddling chair",
 "perched on a windowsill nude": "nude, sitting on windowsill", "on side one leg forward": "on side, leg forward", "tangled in a sheet": "tangled sheets",
 "head at the foot of the bed": "lying upside down, bed", "on all fours looking forward": "all fours", "on all fours looking back": "all fours, looking back",
 "sitting on heels back arched": "seiza, arched back", "folded-forward stretch with hips high": "top-down bottom-up", "looking over shoulder from behind": "from behind, looking back",
 "one hand on a breast": "hand on own breast", "gripping the sheets": "grabbing sheets", "pinching a nipple": "nipple tweak", "rolling a nipple": "nipple tweak, nipple play",
 "stroking a shaft": "penis grab, stroking", "thumb on the head": "penis, glans rub", "reaching between legs from behind": "fingering from behind",
 "grinding on a pillow": "pillow humping", "grinding on a thigh": "thigh grinding", "sucking a finger": "finger sucking",
 "one body covering the other": "lying on person", "a hand on the other's jaw": "hand on another's chin", "a hand on the other's hip": "hand on another's hip",
 "kissing down the sternum": "kissing chest", "kiss at the hip": "kissing hip", "bite at the shoulder": "shoulder bite", "suck-mark on the neck": "hickey, neck",
 "fingers in hair pulling softly": "hair pull", "hand around throat rest (no violence)": "hand on another's neck", "guiding a hip": "hands on another's hips",
 "bent over a bed": "bent over, bed", "bent over a chair": "bent over, chair", "bent over a windowsill": "bent over, windowsill",
 "grinding on a lap clothed-unclothed mix": "lap grinding, partially clothed", "partner sitting on a chair being ridden": "sitting on lap, chair sex",
 "against a wall standing face to face": "standing sex, against wall", "against a wall from behind": "sex from behind, against wall",
 "from the edge of the bed": "oral, edge of bed", "licking along the shaft": "licking penis", "mouth on the head": "fellatio, glans",
 "sucking a nipple during other contact": "breast sucking, sex", "fingering while kissing": "fingering, kiss", "rubbing clit while entering": "clitoral stimulation, sex",
 "spreading for a partner": "spread pussy, presenting", "hard rhythm implied by motion blur": "motion blur, motion lines", "sheet pulled to the waist": "sheet, waist",
 "holding a vibrator": "holding vibrator", "riding a dildo": "dildo riding", "partner holding a wand": "magic wand, partner",
 "partner using a dildo": "dildo, partner", "restraint cuffs loose on wrists": "cuffs, wrist cuffs", "silk tie on the headboard": "silk ties, headboard",
 "blindfold pushed up on the forehead": "blindfold on forehead", "tentacle coil around a thigh": "tentacles, thigh wrap", "tentacle at the hip": "tentacles, hip",
 "glowing rune on bare skin": "glowing tattoo, runes", "incubus shadow over a bed": "incubus, shadow", "magical hands of light touching": "magic hands, glowing",
 "POV looking down a body": "pov, looking down", "over-the-shoulder of a partner's back": "over-the-shoulder shot", "tight crop at joined hips": "close-up, crotch",
 "face-only during the act": "face focus, sex", "pillows on the floor": "pillows, floor", "neon stripe across a torso": "neon light, torso",
 "moonlight on a back": "moonlight, back", "venetian blind stripes over hips": "blinds shadow, hips", "sweat in the small of the back": "sweat, lower back",
 "wet hair stuck to neck": "wet hair, neck", "lipstick on a collarbone": "lipstick mark, collarbone", "lipstick on a shaft": "lipstick mark, penis",
 "dripping down a thigh": "dripping, thigh", "puddle on a sheet": "wet sheets", "discarded condom wrapper at edge of frame": "condom wrapper",
 "water glass on the nightstand": "glass of water, nightstand", "lifted against a wall": "lifted, against wall", "carrying partner while inside": "suspended congress",
 "legs crossed at the ankles on a shoulder": "legs over shoulders", "hips lifted on a pillow": "pillow under hips", "sex on a chair": "chair sex",
 "edge of the bed with partner standing": "edge of bed, standing sex", "sex on a desk": "sex on desk", "sitting in partner's lap facing forward": "reverse upright straddle",
 "hands on partner's chest while riding": "cowgirl position, hands on chest", "slow roll of the hips on top": "girl on top, grinding",
 "bent over a desk": "bent over desk", "bent over the kitchen counter": "bent over, kitchen counter", "one knee on the bed from behind": "sex from behind, knee on bed",
 "standing doggy against a door": "standing doggystyle, against door", "lying face down legs together": "prone bone", "partner lying across the bed diagonally": "lying across bed",
 "head off the edge of the bed": "head off bed, upside-down", "kneeling at the side of the bed": "kneeling, bedside", "oral on the stairs": "oral, stairs",
}
path = os.path.join(REPO, "data", "default_library.json")
data = json.load(open(path, encoding="utf-8"))
n = 0
for cat, groups in data["library"].items():
    for g, tags in groups.items():
        new = []
        for t in tags:
            if t in M:
                n += 1
            new.append(M.get(t, t))
        groups[g] = list(dict.fromkeys(new))
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(path, "a").write("\n")
print(n, "tags rewritten")
