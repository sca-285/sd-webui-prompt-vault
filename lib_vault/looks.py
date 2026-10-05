"""What Muse adds to every idea around its scene: how the people look, their job, the camera,
the light and the colours. Plain tags, by sex where it matters (f, m, and "u" for anyone).

A scene can give any of these lists itself; these are what it gets when it does not.
"""

from __future__ import annotations

import random

# ------------------------------------------------------------------ the body
BUILD = {
    "f": ["slim", "slender", "skinny", "curvy", "voluptuous", "plump", "chubby", "fat", "thick thighs", "wide hips",
          "hourglass figure", "athletic", "toned", "muscular female", "tall female", "long legs", "narrow waist", "soft body"],
    "m": ["slim", "skinny", "lean", "toned", "athletic", "muscular male", "bara", "broad shoulders", "tall male", "chubby", "fat",
          "stocky", "thick arms", "lanky", "beefy", "dad bod"],
    "u": ["tall", "plump", "slim", "muscular", "toned", "chubby"],
}
BUILD_DETAIL = {
    "f": ["collarbone", "toned stomach", "abs", "soft belly", "navel", "hip bones", "defined arms", "thigh gap", "love handles", "stretch marks"],
    "m": ["collarbone", "abs", "veins", "veiny arms", "defined chest", "biceps", "soft belly", "love handles", "hairy arms", "obliques"],
    "u": ["collarbone", "navel", "veins"],
}
SKIN_TONE = {"f": ["pale skin", "fair skin", "tan", "tanned skin", "olive skin", "brown skin", "dark skin", "dark-skinned female", "tanlines"],
             "m": ["pale skin", "fair skin", "tan", "tanned skin", "olive skin", "brown skin", "dark skin", "dark-skinned male", "tanlines"],
             "u": ["pale skin", "fair skin", "tan", "olive skin", "brown skin", "dark skin"]}
SKIN_TEXTURE = ["detailed skin", "skin texture", "skin pores", "glossy skin", "shiny skin", "matte skin", "soft skin", "oily skin", "dewy skin"]
SKIN_DETAIL = ["freckles", "body freckles", "mole", "mole under eye", "mole under mouth", "beauty mark", "birthmark", "scar", "scar on face",
               "scar on cheek", "tattoo", "arm tattoo", "shoulder tattoo", "vitiligo", "sunburn"]

# ------------------------------------------------------------------ the head
HAIR_COLOR = ["black hair", "brown hair", "light brown hair", "blonde hair", "platinum blonde hair", "red hair", "auburn hair", "orange hair",
              "white hair", "silver hair", "grey hair", "pink hair", "blue hair", "dark blue hair", "green hair", "purple hair",
              "multicolored hair", "two-tone hair", "gradient hair", "streaked hair", "colored inner hair"]
HAIR_STYLE = {
    "f": ["long hair", "very long hair", "medium hair", "bob cut", "ponytail", "high ponytail", "side ponytail", "twintails", "low twintails",
          "twin braids", "single braid", "french braid", "hair bun", "double bun", "messy bun", "half updo", "hime cut", "blunt bangs",
          "side-swept bangs", "hair over one eye", "drill hair", "pixie cut", "wavy hair", "curly hair", "straight hair", "hair intakes"],
    "m": ["short hair", "buzz cut", "crew cut", "undercut", "slicked back hair", "spiked hair", "messy hair", "man bun", "mohawk", "mullet",
          "side part", "curly hair", "long hair", "ponytail", "dreadlocks", "cornrows", "bald", "afro", "wolf cut", "shaggy hair"],
    "u": ["messy hair", "wavy hair", "curly hair", "straight hair", "shoulder-length hair", "afro", "dreadlocks", "braid",
          "hair between eyes", "ahoge", "wolf cut", "shaggy hair", "short hair", "medium hair"],
}
FACIAL_HAIR = ["beard", "stubble", "mustache", "goatee", "sideburns", "full beard", "short beard", "clean-shaven"]
EYE_COLOR = ["blue eyes", "green eyes", "brown eyes", "red eyes", "purple eyes", "yellow eyes", "amber eyes", "grey eyes", "hazel eyes",
             "golden eyes", "aqua eyes", "pink eyes", "black eyes", "heterochromia"]
EYE_DETAIL = ["long eyelashes", "sharp eyes", "droopy eyes", "tsurime", "tareme", "slit pupils", "glowing eyes", "sparkling eyes",
              "detailed eyes", "eye reflection", "ringed eyes", "almond eyes", "hooded eyes", "monolid", "deep-set eyes"]
EYEBROWS = ["thick eyebrows", "thin eyebrows", "arched eyebrows", "bushy eyebrows", "short eyebrows", "straight eyebrows", "raised eyebrow",
            "furrowed brow", "v-shaped eyebrows"]
NOSE = ["small nose", "button nose", "sharp nose", "upturned nose", "aquiline nose", "freckles on nose", "nose piercing", "septum piercing",
        "nose ring", "broad nose"]
LIPS = ["full lips", "thin lips", "plump lips", "glossy lips", "pink lips", "red lips", "dark lips", "cupid's bow", "lip piercing", "chapped lips"]
MAKEUP = {"f": ["makeup", "light makeup", "heavy makeup", "eyeliner", "winged eyeliner", "eyeshadow", "red eyeshadow", "smokey eyes",
                "mascara", "lipstick", "red lipstick", "black lipstick", "nude lipstick", "nail polish", "red nails", "black nails",
                "glitter makeup", "goth makeup", "face paint", "no makeup"],
          "m": ["eyeliner", "black nails", "face paint", "war paint", "no makeup", "guyliner", "smudged eyeliner", "light makeup",
                "black eyeshadow", "nail polish", "glitter on cheek", "kohl", "concealer", "lip balm", "stage makeup", "body paint"],
          "u": ["eyeliner", "face paint", "black nails", "no makeup", "light makeup", "glitter on cheek", "nail polish", "smudged eyeliner",
                "stage makeup", "body paint", "kohl", "war paint", "lip balm", "black eyeshadow", "concealer"]}
ACCESSORIES = {
    "f": ["earrings", "hoop earrings", "stud earrings", "necklace", "pendant", "pearl necklace", "choker", "hair ribbon", "hair bow",
          "hairclip", "hair flower", "headband", "tiara", "bracelet", "bangle", "ring", "wristwatch", "glasses", "round eyewear",
          "sunglasses", "beret", "sun hat", "scarf", "gloves", "anklet", "handbag", "hair scrunchie", "ear piercing"],
    "m": ["wristwatch", "glasses", "sunglasses", "chain necklace", "dog tags", "ring", "single earring", "baseball cap", "beanie", "fedora",
          "bracelet", "bandana", "scarf", "gloves", "belt", "ear piercing", "headphones around neck"],
    "u": ["glasses", "sunglasses", "wristwatch", "necklace", "bracelet", "ring", "scarf", "headphones", "ear piercing", "beanie", "cap"],
}
GAZE = {"solo": ["looking at viewer", "looking away", "looking to the side", "looking down", "looking up", "looking back", "looking afar",
                 "closed eyes", "half-closed eyes", "sideways glance", "staring", "looking ahead", "upturned eyes", "averting eyes",
                 "looking afar", "glancing back", "looking at hand", "eyes half-open", "gazing upward", "side glance", "looking through hair"],
        "people": ["eye contact", "looking at another", "looking at viewer", "looking away", "closed eyes", "looking down", "looking back", "looking at each other",
                   "looking in same direction", "glancing at another", "looking afar", "looking up", "staring at another", "looking ahead",
                   "side glance", "eyes closed, smiling"]}
MOUTH = ["closed mouth", "open mouth", "parted lips", "biting lip", "tongue out", "licking lips", "pout", "puckered lips", "puffy cheeks",
         "clenched teeth", "fang", "teeth", "grin", "chewing", "whistling", "bubble blowing", "mouth hold", "smile", "frown", "wavy mouth"]

# ------------------------------------------------------------------ a real animal with them (SFW ideas only)
PETS = {
    "home": ["cat", "black cat", "orange cat", "calico cat", "kitten", "dog", "shiba inu", "golden retriever", "corgi", "pug",
             "dachshund", "husky", "poodle", "rabbit", "hamster", "parrot", "budgerigar", "goldfish bowl", "ferret", "tabby cat",
             "white cat", "siamese cat", "maine coon", "beagle", "pomeranian", "samoyed", "border collie", "chinchilla", "guinea pig",
             "cockatiel", "lop rabbit"],
    "wild": ["fox", "deer", "fawn", "owl", "rabbit", "squirrel", "hedgehog", "songbird", "horse", "pony", "goat", "sheep",
             "chicken", "duck", "wolf", "crow", "butterfly", "dragonfly", "frog", "robin", "heron", "swan",
             "squirrel, acorn", "chipmunk", "goose", "bee", "ladybug", "hare"],
    "sea": ["seagull", "parrot", "dolphin", "sea turtle", "crab", "cat", "dog", "pelican", "starfish", "hermit crab", "otter",
            "seal", "puffin", "jellyfish", "tropical fish", "albatross", "ship cat", "pirate parrot", "turtle", "cormorant"],
    "dark": ["black cat", "raven", "crow", "owl", "bat", "snake", "wolf", "spider", "rat", "moth", "black dog", "toad",
             "vulture", "lizard", "scorpion", "doberman", "barn owl", "crows, flock", "black goat", "beetle"],
    "fantasy": ["owl", "raven", "black cat", "horse", "white horse", "hawk", "wolf", "fox", "stag", "falcon", "eagle",
                "white wolf", "black horse", "snow owl", "lynx", "doe", "hound", "dove", "peacock", "pony"],
    "city": ["cat", "dog", "shiba inu", "pigeon", "crow", "corgi", "french bulldog", "small dog", "stray cat", "dachshund",
             "pug", "sparrow", "pomeranian", "greyhound", "black cat", "golden retriever", "chihuahua", "poodle", "husky", "tabby cat"],
}
PETS_BY_THEME = {"Home": "home", "Bedroom": "home", "Portrait": "home", "Studio": "home", "Office": "home", "Food": "city",
                 "Street": "city", "World cities": "city", "Retro 80s-90s": "city", "Travel": "city", "Party": "city", "Fashion": "city",
                 "Nature": "wild", "Outdoors": "wild", "Countryside": "wild", "Sports": "wild", "Holidays": "home", "Architecture": "city",
                 "Seafaring": "sea", "Horror": "dark", "Historical": "fantasy", "Myth": "fantasy", "Fantasy": "fantasy", "Creature": "fantasy",
                 "Steampunk": "city", "Post-apocalypse": "wild", "Film": "city", "Music & stage": "city", "Hotel": "home", "Gym": "city",
                 "Bath & shower": "home", "Sci-fi": "city", "Kitchen": "home", "Living room": "home",
                 "Balcony": "home", "Garden": "home", "Restroom": "city", "School": "city"}
WITH_PET = ["holding animal", "animal on shoulder", "animal on lap", "petting", "animal hug", "carrying animal", "walking animal",
            "looking at animal", "animal at feet", "feeding animal"]

# too big to hold, carry or have on a lap
BIG_ANIMALS = {"horse", "white horse", "black horse", "pony", "deer", "doe", "stag", "wolf", "white wolf", "goat", "black goat", "sheep",
               "dolphin", "pelican", "husky", "golden retriever", "samoyed", "seal", "swan", "goose", "heron", "vulture", "doberman", "greyhound",
               "hound", "border collie", "peacock", "albatross", "eagle", "black dog", "lynx", "otter"}
# insects, fish and the like: watched, or on a hand at most
SMALL_WILD = {"butterfly", "dragonfly", "bee", "ladybug", "moth", "beetle", "spider", "scorpion", "frog", "toad", "jellyfish",
              "tropical fish", "starfish", "hermit crab", "crab", "goldfish bowl", "crows, flock", "lizard", "snake", "squirrel, acorn",
              "chipmunk", "robin", "sparrow", "pigeon", "seagull", "bat", "rat"}
WITH_SMALL = ["looking at animal", "animal on hand", "watching animal"]
WITH_BIG = ["petting", "looking at animal", "feeding animal", "walking animal"]


def pets_for(theme, rng):
    """A few real animals for the theme, each with what the people do with it now and then."""
    kinds = PETS[PETS_BY_THEME.get(theme, "home")]
    def doing(k):
        if k in SMALL_WILD:
            return WITH_SMALL
        return WITH_BIG if k in BIG_ANIMALS else WITH_PET
    return [k if rng.random() < 0.4 else f"{k}, {rng.choice(doing(k))}" for k in kinds]


# ------------------------------------------------------------------ camera
SHOT = ["extreme close-up", "close-up", "portrait", "upper body", "cowboy shot", "full body", "medium shot", "wide shot", "very wide shot",
        "establishing shot", "head out of frame", "feet out of frame"]
ANGLE = ["from above", "from below", "high angle", "low angle", "eye level", "dutch angle", "overhead shot", "worm's eye view",
         "aerial view", "straight-on", "tilted frame", "slightly from above", "slightly from below", "bird's eye view",
         "ground level", "canted angle", "shoulder level"]
VIEW = ["front view", "from side", "from behind", "three-quarter view", "profile", "pov", "over-the-shoulder shot", "reflection",
        "back view", "selfie", "side view", "three-quarter back view", "looking back view", "half-turned", "frontal view",
        "rear view"]
FRAMING = ["centered", "rule of thirds", "symmetry", "negative space", "frame within frame", "foreground blur", "depth of field", "bokeh",
           "wide-angle lens", "fisheye", "telephoto lens", "35mm lens", "85mm lens", "macro", "tilt-shift", "motion blur",
           "chromatic aberration", "lens flare", "leading lines", "silhouette framing", "diagonal composition", "off-center", "cinematic composition", "shallow depth of field", "deep focus"]

# ------------------------------------------------------------------ light, beside the scene's own source
LIGHT_QUALITY = ["soft lighting", "hard lighting", "diffused light", "high contrast", "low contrast", "harsh shadows", "soft shadows",
                 "even lighting", "low key", "high key", "chiaroscuro", "specular highlights", "subtle lighting", "crisp lighting",
                 "gentle shadows", "deep shadows", "contrast lighting"]
LIGHT_MOOD = ["warm lighting", "cool lighting", "moody lighting", "dramatic lighting", "cinematic lighting", "romantic lighting",
              "eerie lighting", "dreamy lighting", "cozy lighting", "gloomy lighting", "ethereal lighting", "golden glow",
              "nostalgic lighting", "intimate lighting", "melancholic lighting", "mysterious lighting", "vibrant lighting"]
LIGHT_SUPPORT = ["rim lighting", "backlighting", "side lighting", "fill light", "edge lighting", "top lighting", "underlighting",
                 "bounce light", "two-tone lighting", "colored rim light", "hair light", "kicker light", "split lighting",
                 "rembrandt lighting", "butterfly lighting", "key light", "loop lighting"]
LIGHT_VOLUME = ["volumetric lighting", "god rays", "light rays", "sunbeam", "light shafts", "light particles", "dust particles",
                "atmospheric haze", "crepuscular rays", "bloom", "glowing particles", "caustics", "hazy light",
                "light bloom", "floating dust", "lens glow", "soft haze"]
# natural light, from the hour and the sky (see when.py)
NATURAL = {"morning": ["morning light", "soft morning sunlight", "early morning light", "dawn light", "low sun", "cool morning light",
                       "pale sunlight", "sunrise glow", "morning haze", "fresh morning light", "soft dawn light", "first light"],
           "day": ["natural light", "daylight", "sunlight", "bright daylight", "midday sun", "harsh sunlight", "clear daylight",
                   "overhead sun", "bright sun", "noon light", "sunny", "strong sunlight"],
           "afternoon": ["afternoon light", "warm sunlight", "late afternoon sun", "golden light", "slanting sunlight", "soft afternoon light",
                         "long shadows", "warm daylight", "honey light", "mellow sunlight", "low afternoon sun", "amber light"],
           "evening": ["sunset light", "evening light", "golden hour", "dusk light", "orange sunlight", "twilight", "afterglow",
                       "fading light", "red sky glow", "blue hour", "dusky light", "last light"],
           "night": ["moonlight", "night light", "starlight", "dim moonlight", "city glow", "blue night light", "lamplight", "dark night",
                     "silver moonlight", "full moon light", "faint light", "night glow"]}
NATURAL_SKY = {"overcast": ["overcast light", "diffused daylight", "flat light", "soft grey light"],
               "rain": ["rainy light", "grey light", "wet reflections", "gloomy light"],
               "fog": ["foggy light", "misty light", "hazy light", "muted light"],
               "snow": ["snow light", "cold light", "bright snow glare", "blue winter light"],
               "cloudy": ["cloudy light", "broken sunlight", "soft clouds light"],
               "clear": ["clear light", "crisp light"]}

# ------------------------------------------------------------------ colour
COLOR = ["color grading", "warm color grading", "cool color grading", "teal and orange", "muted colors", "pastel colors", "vibrant colors",
         "high saturation", "desaturated", "monochrome", "sepia", "limited palette", "earth tones", "neon colors", "split toning",
         "cross processing", "bleach bypass", "faded colors", "golden tones", "blue tones", "red tones", "complementary colors",
         "color contrast", "kodak portra 400", "cinestill 800t", "fujifilm colors", "film grain", "matte colors", "jewel tones", "duotone", "technicolor", "autumn colors", "candy colors", "kodachrome"]

# ------------------------------------------------------------------ jobs: what they wear, carry, and what goes on around them
# name: (themes, women's wear, men's wear, props, effects). Fiction stays in its own worlds: a knight or a
# witch only in Fantasy or Myth, a netrunner only in Sci-fi, an airship pilot only in Steampunk.
JOBS = {
    "nurse": (["Office", "Home", "Horror", "Film", "Red light", "Bath & shower", "School", "Portrait"], "nurse uniform, nurse cap", "scrubs", "stethoscope, clipboard", ""),
    "doctor": (["Office", "Horror", "Film", "Sci-fi", "Post-apocalypse", "Portrait"], "lab coat, blouse", "lab coat, shirt, necktie", "stethoscope, id card", ""),
    "surgeon": (["Horror", "Film", "Sci-fi"], "surgical gown, surgical mask", "surgical gown, surgical mask", "scalpel, surgical gloves", ""),
    "police officer": (["Street", "Film", "Office", "World cities", "Retro 80s-90s", "Horror", "Portrait"], "police uniform, police hat", "police uniform, police hat",
                       "handcuffs, badge, radio", ""),
    "firefighter": (["Street", "Film", "World cities", "Portrait"], "firefighter jacket, helmet", "firefighter jacket, helmet", "fire hose, axe", "smoke, embers"),
    "chef": (["Food", "Home", "Hotel", "Party", "Kitchen", "Holidays", "Portrait"], "chef uniform, chef hat", "chef uniform, chef hat", "kitchen knife, ladle", "steam, flames"),
    "baker": (["Food", "Countryside", "Holidays", "Kitchen"], "apron, headscarf", "apron, baker hat", "rolling pin, flour", "flour dust"),
    "barista": (["Food", "Street", "World cities", "Kitchen", "Holidays", "Portrait"], "apron, rolled sleeves", "apron, rolled sleeves", "coffee cup, milk pitcher", "steam"),
    "waitress": (["Food", "Retro 80s-90s", "Party", "Hotel", "Kitchen", "Restroom", "Holidays"], "waitress uniform, apron", "waiter uniform, bow tie", "serving tray, notepad", ""),
    "bartender": (["Party", "Hotel", "Food", "Historical", "Music & stage", "Living room", "Balcony", "Red light", "Restroom"], "vest, bow tie", "vest, bow tie", "cocktail shaker, bottles", ""),
    "sommelier": (["Food", "Hotel", "Countryside", "Kitchen"], "black vest, apron", "black vest, apron", "wine glass, wine bottle", ""),
    "maid": (["Home", "Hotel", "Historical", "Steampunk", "Fantasy", "Red light", "Kitchen", "Living room", "Bedroom"], "maid, maid headdress, apron", "butler, tailcoat", "feather duster, tea set", ""),
    "receptionist": (["Hotel", "Office"], "blazer, pencil skirt, name tag", "suit, name tag", "phone, keys", ""),
    "office worker": (["Office", "Street", "World cities", "Restroom", "Portrait"], "office lady, pencil skirt, blouse", "salaryman, suit, necktie", "laptop, id card", ""),
    "secretary": (["Office", "Red light"], "blouse, pencil skirt, glasses", "suit, glasses", "clipboard, pen", ""),
    "ceo": (["Office", "Hotel", "Architecture"], "power suit", "three-piece suit", "smartphone, briefcase", ""),
    "lawyer": (["Office", "Film"], "skirt suit", "suit, necktie", "briefcase, documents", ""),
    "teacher": (["Office", "Countryside", "Historical", "School"], "cardigan, long skirt, glasses", "shirt, sweater vest, glasses", "book, chalk", ""),
    "librarian": (["Portrait", "Office", "Architecture", "Fantasy", "Historical", "School"], "cardigan, glasses, long skirt", "cardigan, glasses", "stack of books", "dust particles"),
    "scientist": (["Sci-fi", "Steampunk", "Office", "Creature", "School"], "lab coat, safety goggles", "lab coat, safety goggles", "test tube, tablet", "glowing liquid"),
    "engineer": (["Sci-fi", "Steampunk", "Architecture", "Post-apocalypse"], "coveralls, hard hat", "coveralls, hard hat", "wrench, blueprint", "sparks"),
    "mechanic": (["Street", "Retro 80s-90s", "Sci-fi", "Post-apocalypse"], "mechanic overalls, tank top", "mechanic overalls", "wrench, oil stains", "sparks"),
    "construction worker": (["Street", "Architecture"], "high-visibility vest, hard hat", "high-visibility vest, hard hat", "toolbelt, shovel", "dust"),
    "farmer": (["Countryside", "Nature", "Garden", "Post-apocalypse", "Outdoors"], "overalls, straw hat", "overalls, straw hat", "pitchfork, basket", ""),
    "fisherman": (["Seafaring", "Countryside", "Nature", "Outdoors"], "raincoat, rubber boots", "raincoat, rubber boots", "fishing rod, net", "sea spray"),
    "gardener": (["Home", "Nature", "Outdoors", "Portrait", "Garden", "Balcony"], "gardening apron, gloves", "gardening apron, gloves", "watering can, trowel", ""),
    "janitor": (["Restroom", "Office", "School", "Horror"], "janitor uniform, rubber gloves", "janitor uniform, rubber gloves", "mop, bucket", ""),
    "plumber": (["Restroom", "Kitchen"], "work overalls, tool belt", "work overalls, tool belt", "wrench, toolbox", "water droplets"),
    "coach": (["School", "Sports", "Gym"], "track jacket, whistle", "track jacket, whistle", "clipboard, stopwatch", ""),
    "homemaker": (["Kitchen", "Living room", "Home", "Balcony"], "apron, cardigan", "apron, sweater", "laundry basket, ladle", ""),
    "landscaper": (["Garden"], "work shirt, gardening gloves", "work shirt, gardening gloves", "hedge trimmer, rake", "grass clippings"),
    "writer": (["Bedroom", "Living room", "Balcony", "Office", "Food", "Portrait", "Home"], "cardigan, glasses", "sweater, glasses", "notebook, pen", ""),
    "influencer": (["Fashion", "Food", "Travel", "World cities", "Street", "Bedroom", "Balcony", "Gym", "Party", "Portrait", "Studio", "Living room", "Home"],
                   "trendy outfit", "trendy outfit", "smartphone, ring light", ""),
    "fashion designer": (["Fashion", "Studio"], "chic blouse, tape measure", "black turtleneck, tape measure", "sketchbook, fabric swatches", ""),
    "makeup artist": (["Fashion", "Studio", "Film", "Music & stage"], "black apron, makeup belt", "black apron, makeup belt", "makeup brush, palette", "powder dust"),
    "tailor": (["Fashion", "Historical", "Steampunk"], "waistcoat, tape measure", "waistcoat, tape measure", "scissors, pins", ""),
    "spa attendant": (["Bath & shower", "Hotel"], "spa uniform", "spa uniform", "towels, aroma oil", "steam"),
    "swimmer": (["Bath & shower", "Sports", "Outdoors", "Travel", "Seafaring"], "competition swimsuit, swim cap", "swim briefs, swim cap",
                "swim goggles", "water splash"),
    "skier": (["Holidays", "Outdoors", "Sports", "Travel"], "ski jacket, ski goggles", "ski jacket, ski goggles", "ski poles", "snow spray"),
    "ice skater": (["Holidays", "Sports", "Outdoors"], "skating dress", "skating outfit", "ice skates", "ice sparkles"),
    "survivor": (["Post-apocalypse", "Horror"], "torn clothes, backpack", "torn clothes, backpack", "flashlight, crowbar", "dust"),
    "medic": (["Post-apocalypse", "Film", "Sci-fi", "Sports"], "medic uniform, armband", "medic uniform, armband", "first aid kit", ""),
    "raider": (["Post-apocalypse"], "spiked shoulder pads, leather", "spiked shoulder pads, leather", "chain, makeshift weapon", "smoke"),
    "hunter": (["Post-apocalypse", "Outdoors", "Nature", "Fantasy", "Countryside", "Creature"], "hunting jacket, boots", "hunting jacket, boots",
               "bow, quiver", ""),
    "pole dancer": (["Red light", "Party"], "pole dance outfit", "pole dance outfit", "dance pole", "stage lights"),
    "bunny girl": (["Red light", "Party", "Retro 80s-90s"], "playboy bunny, bunny ears", "bunny ears, bow tie", "tray, cocktail", ""),
    "security guard": (["Restroom", "Office", "Street", "Film", "Hotel", "Music & stage", "Party"], "security uniform", "security uniform",
                       "radio, flashlight", ""),
    "explorer": (["Creature", "Travel", "Outdoors", "Nature", "Historical", "Seafaring", "Steampunk"], "explorer outfit, pith helmet",
                 "explorer outfit, pith helmet", "map, compass", ""),
    "camp counselor": (["Horror", "Outdoors", "Nature"], "camp shirt, shorts", "camp shirt, shorts", "whistle, flashlight", ""),
    "ghost hunter": (["Horror", "Film", "Architecture"], "field jacket, headlamp", "field jacket, headlamp", "emf reader, camera", "ghostly glow"),
    "gravedigger": (["Horror", "Historical"], "work clothes, gloves", "work clothes, gloves", "shovel, lantern", "fog"),
    "mountain guide": (["Outdoors", "Nature", "Travel"], "climbing gear", "climbing gear", "rope, carabiner", ""),
    "diver": (["Seafaring", "Outdoors", "Travel", "Sports"], "wetsuit, diving mask", "wetsuit, diving mask", "oxygen tank, flippers", "bubbles"),
    "marine biologist": (["Seafaring", "Sci-fi"], "wetsuit, lab coat", "field vest, lab coat", "specimen jar, clipboard", ""),
    "referee": (["Sports", "Gym"], "referee shirt, whistle", "referee shirt, whistle", "whistle, yellow card", ""),
    "cheerleader": (["Sports", "School", "Retro 80s-90s", "Party"], "cheerleader outfit", "cheerleader uniform", "pom poms", "confetti"),
    "martial artist": (["Sports", "Gym", "Historical", "Fantasy", "Film"], "dougi, black belt", "dougi, black belt", "hand wraps", "motion blur"),
    "sculptor": (["Studio", "Historical", "Architecture"], "apron, dusty clothes", "apron, dusty clothes", "chisel, clay", "marble dust"),
    "tour guide": (["World cities", "Travel", "Architecture", "Historical"], "polo shirt, lanyard", "polo shirt, lanyard", "flag, microphone", ""),
    "beekeeper": (["Garden", "Countryside", "Balcony"], "beekeeper suit, veil hat", "beekeeper suit, veil hat", "honeycomb frame, smoker", "bees"),
    "stylist": (["Fashion", "Studio"], "chic outfit, clothing rack", "chic outfit, clothing rack", "garment bag, pins", ""),
    "bath attendant": (["Bath & shower"], "yukata, tasuki", "jinbei, towel on shoulder", "wooden bucket, towels", "steam"),
    "florist": (["Street", "Food", "Holidays", "Garden"], "apron, sundress", "apron, shirt", "bouquet, flower scissors", "petals"),
    "photographer": (["Fashion", "Portrait", "Studio", "Travel", "Garden", "Creature", "Outdoors"], "casual clothes, camera strap", "casual clothes, camera strap", "camera", "camera flash"),
    "painter": (["Studio", "Portrait", "Historical", "School", "Garden", "Bedroom", "Living room", "Balcony", "Home"], "smock, paint-stained apron", "smock, paint-stained apron", "paintbrush, palette", "paint splatter"),
    "musician": (["Music & stage", "Party", "Street", "School", "Living room", "Bedroom", "Balcony", "Holidays", "Portrait", "Home"], "stage outfit", "stage outfit", "guitar", "stage lights"),
    "singer": (["Music & stage", "Party", "Historical"], "evening gown", "suit", "microphone", "spotlight"),
    "dancer": (["Music & stage", "Party", "Gym", "Historical", "Studio", "Portrait", "Red light"], "dance costume", "dance costume", "", "motion blur"),
    "idol": (["Music & stage"], "idol clothes, frills", "idol clothes", "microphone, glowsticks", "sparkles, confetti"),
    "model": (["Fashion", "Studio", "Portrait", "Bath & shower", "Bedroom", "Restroom", "Garden"], "haute couture", "designer suit", "", "camera flash"),
    "dj": (["Party", "Music & stage", "Retro 80s-90s"], "crop top, headphones", "tank top, headphones", "turntable, headphones", "laser lights"),
    "athlete": (["Sports", "Gym", "School", "Restroom"], "sportswear, number bib", "sportswear, number bib", "medal", "sweat, motion blur"),
    "boxer": (["Sports", "Gym"], "boxing shorts, sports bra", "boxing shorts, boxing gloves", "boxing gloves, mouthguard", "sweat"),
    "lifeguard": (["Nature", "Outdoors", "Bath & shower", "Travel"], "red swimsuit, whistle", "red swim trunks, whistle", "rescue buoy", ""),
    "personal trainer": (["Gym", "Sports"], "sports bra, leggings, whistle", "tank top, whistle", "stopwatch, clipboard", ""),
    "yoga instructor": (["Gym", "Sports", "Outdoors", "Garden", "Balcony", "Bedroom", "Home", "Living room"], "yoga outfit", "yoga outfit", "yoga mat", ""),
    "massage therapist": (["Bath & shower", "Hotel", "Red light"], "spa uniform", "spa uniform", "massage oil, towel", "steam"),
    "pilot": (["Travel", "Sci-fi", "Retro 80s-90s"], "pilot uniform, pilot cap", "pilot uniform, pilot cap", "aviator sunglasses", ""),
    "flight attendant": (["Travel"], "flight attendant uniform, scarf", "flight attendant uniform", "trolley, tray", ""),
    "sailor": (["Seafaring", "Travel"], "sailor uniform", "sailor uniform, sailor hat", "rope, compass", "sea spray"),
    "ship captain": (["Seafaring", "Travel"], "captain uniform, captain hat", "captain uniform, captain hat", "telescope, ship wheel", ""),
    "soldier": (["Post-apocalypse", "Film", "Seafaring", "Portrait"], "military uniform, combat boots", "military uniform, combat boots", "rifle, dog tags", "smoke"),
    "detective": (["Film", "Street", "Historical", "Steampunk", "Horror"], "trench coat, fedora", "trench coat, fedora", "magnifying glass, notebook", "cigarette smoke"),
    "astronaut": (["Sci-fi"], "spacesuit", "spacesuit", "space helmet", "floating"),
    "streamer": (["Home", "Bedroom", "Retro 80s-90s", "Living room"], "hoodie, cat ear headphones", "hoodie, headset", "microphone, monitor", "rgb lighting"),
    "hacker": (["Sci-fi", "Office", "Street"], "hoodie, techwear", "hoodie, techwear", "laptop, cables", "holographic interface"),
    "tattoo artist": (["Studio", "Street"], "tank top, tattoos", "tank top, tattoos", "tattoo machine, gloves", ""),
    "hairdresser": (["Fashion", "Studio", "Street"], "apron, scissors", "apron, scissors", "comb, hair dryer", ""),
    "priest": (["Horror", "Myth", "Historical", "Architecture"], "nun, habit", "priest, cassock", "cross, rosary", "candlelight"),
    "miko": (["Myth", "Holidays", "Architecture", "Historical"], "miko, hakama", "kannushi", "gohei, broom", "falling petals"),
    "geisha": (["Historical", "World cities"], "geisha, kimono, kanzashi", "kimono, haori", "folding fan, umbrella", "falling petals"),
    "samurai": (["Historical", "Film"], "samurai armor", "samurai armor", "katana", "falling petals"),
    "ninja": (["Historical", "Film"], "ninja, mask", "ninja, mask", "kunai, shuriken", "smoke"),
    "cowboy": (["Historical", "Film", "Countryside"], "cowboy hat, cowboy boots", "cowboy hat, cowboy boots", "lasso, revolver", "dust"),
    "pirate": (["Seafaring", "Historical", "Fantasy"], "pirate hat, pirate coat", "pirate hat, pirate coat", "cutlass, flintlock", "sea spray"),
    # fantasy and fiction
    "knight": (["Fantasy", "Myth"], "armor, cape", "plate armor, cape", "sword, shield", "glint"),
    "paladin": (["Fantasy", "Myth"], "white armor, holy symbol", "white armor, holy symbol", "warhammer, shield", "holy light"),
    "wizard": (["Fantasy", "Myth"], "witch hat, robe", "wizard hat, robe", "staff, spellbook", "magic circle, glowing runes"),
    "witch": (["Fantasy", "Myth", "Creature", "Horror"], "witch hat, black dress", "warlock robe", "broom, potion", "magic, sparkles"),
    "sorceress": (["Fantasy", "Myth"], "sorceress robe, circlet", "sorcerer robe, circlet", "crystal orb", "magic aura, floating particles"),
    "cleric": (["Fantasy", "Myth"], "priestess robe", "cleric robe", "holy symbol, staff", "holy light"),
    "rogue": (["Fantasy"], "hooded cloak, leather armor", "hooded cloak, leather armor", "dagger, lockpick", "shadows"),
    "assassin": (["Fantasy", "Myth"], "assassin, hood, mask", "assassin, hood, mask", "hidden blade, dagger", "smoke"),
    "ranger": (["Fantasy"], "ranger, green cloak", "ranger, green cloak", "bow, quiver", "falling leaves"),
    "bard": (["Fantasy"], "bard outfit, feathered hat", "bard outfit, feathered hat", "lute", "musical notes"),
    "druid": (["Fantasy", "Myth", "Creature"], "druid robe, leaf crown", "druid robe, antlers", "wooden staff", "glowing plants"),
    "necromancer": (["Fantasy"], "black robe, skull ornament", "black robe, skull ornament", "skull staff", "green fire, ghosts"),
    "alchemist": (["Fantasy"], "apron, goggles", "apron, goggles", "potion flasks", "colored smoke"),
    "blacksmith": (["Fantasy", "Historical"], "leather apron", "leather apron, shirtless", "hammer, tongs", "sparks, embers"),
    "merchant": (["Fantasy", "Historical", "World cities"], "merchant clothes, coin purse", "merchant clothes, coin purse", "scales, goods", ""),
    "princess": (["Fantasy", "Myth", "Historical"], "princess, gown, tiara", "prince, royal clothes, crown", "scepter", "sparkles"),
    "queen": (["Fantasy", "Myth", "Historical"], "queen, royal gown, crown", "king, royal robe, crown", "throne, scepter", ""),
    "adventurer": (["Fantasy"], "adventurer, leather armor, backpack", "adventurer, leather armor, backpack",
                   "map, lantern", ""),
    "gladiator": (["Historical"], "gladiator armor", "gladiator armor", "gladius, shield", "dust"),
    "valkyrie": (["Fantasy", "Myth"], "valkyrie, winged helmet", "viking armor, horned helmet", "spear, shield", "feathers"),
    "monk": (["Fantasy", "Myth", "Historical"], "monk robe", "monk robe, prayer beads", "prayer beads", "incense smoke"),
    "vampire hunter": (["Fantasy", "Myth", "Horror"], "long coat, hunter hat", "long coat, hunter hat", "crossbow, stakes", "fog"),
    "exorcist": (["Fantasy", "Myth", "Horror"], "nun, habit", "priest, cassock", "holy water, rosary", "ofuda, glowing seals"),
    "bounty hunter": (["Sci-fi"], "armor, helmet", "armor, helmet", "blaster", "smoke"),
    "starship captain": (["Sci-fi"], "captain uniform", "captain uniform", "data pad", "holograms"),
    "mecha pilot": (["Sci-fi"], "pilot suit", "pilot suit", "helmet", "holographic display"),
    "netrunner": (["Sci-fi"], "techwear, cyber implants", "techwear, cyber implants", "neural cable", "holograms, glitch effect"),
    "space marine": (["Sci-fi"], "power armor", "power armor", "rifle", "muzzle flash"),
    "scavenger": (["Post-apocalypse"], "scavenger, gas mask", "scavenger, gas mask", "makeshift weapon, backpack", "dust"),
    "airship pilot": (["Steampunk"], "aviator goggles, leather jacket", "aviator goggles, leather jacket", "spyglass", "clouds"),
    "inventor": (["Steampunk"], "goggles, corset, tool belt", "goggles, waistcoat, tool belt", "wrench, gadget", "steam, sparks"),
    "zookeeper": (["Creature", "Nature"], "zookeeper uniform, cap", "zookeeper uniform, cap", "bucket, brush", ""),
    "veterinarian": (["Creature", "Countryside", "Nature"], "scrubs, stethoscope", "scrubs, stethoscope", "medical bag", ""),
    "wildlife ranger": (["Creature", "Nature", "Outdoors"], "ranger uniform, hat", "ranger uniform, hat", "binoculars, radio", ""),
    "monster tamer": (["Fantasy", "Creature"], "tamer outfit, whip", "tamer outfit, whip", "monster ball, leash", ""),
    "dragon rider": (["Fantasy", "Myth"], "riding armor, goggles", "riding armor, goggles", "lance, saddle", "wind"),
}
TEASE = ["open clothes", "unbuttoned", "clothes pull", "strap slip", "skirt lift", "shirt lift", "torn clothes", "partially unbuttoned",
         "unzipped", "wet clothes", "see-through clothes", "off shoulder", "loose clothes", "half-undressed", "clothes slipping",
         "undone belt"]


def _by_sex(table, f, m):
    if f and not m:
        return table["f"]
    if m and not f:
        return table["m"]
    if f and m:
        return table["f"] + table["m"]
    return table["u"]


def _hair(color, style):
    """A colour and a style; no colour for a bald head."""
    return style if style == "bald" else f"{color}, {style}"


def pools(f, m, people, rng):
    """The character parts' entries for an idea with women (f) and/or men (m); people: how many."""
    rng = rng or random.Random()
    build = [x for x in _by_sex(BUILD, f, m)]
    out = {
        "build": [b if rng.random() < 0.5 else f"{b}, {rng.choice(_by_sex(BUILD_DETAIL, f, m))}" for b in build],
        "skin": [", ".join(dict.fromkeys(x for x in (rng.choice(_by_sex(SKIN_TONE, f, m)),
                                                     rng.choice(SKIN_TEXTURE) if rng.random() < 0.6 else "",
                                                     rng.choice(SKIN_DETAIL) if rng.random() < 0.4 else "") if x)) for _ in range(18)],
        "hair": [_hair(rng.choice(HAIR_COLOR), rng.choice(_by_sex(HAIR_STYLE, f, m))) for _ in range(20)],
        "eyes": [f"{c}, {rng.choice(EYE_DETAIL)}" if rng.random() < 0.6 else c for c in EYE_COLOR + rng.sample(EYE_COLOR, 6)],
        "face": [", ".join(rng.sample(EYEBROWS, 1) + rng.sample(NOSE, 1) + rng.sample(LIPS, 1))
                 + (f", {rng.choice(FACIAL_HAIR)}" if m and not f and rng.random() < 0.5 else "") for _ in range(18)],
        "makeup": _by_sex(MAKEUP, f, m),
        "accessory": _by_sex(ACCESSORIES, f, m),
        "gaze": GAZE["solo"] if people <= 1 else GAZE["people"],
        "mouth": MOUTH,
    }
    return out


def jobs_for(theme):
    return [name for name, (themes, *_rest) in JOBS.items() if themes == "*" or theme in themes]


def job_wear(name, f, m):
    """What someone of a job wears: a woman's, a man's, or both for a mixed cast."""
    _themes, fw, mw, _props, _fx = JOBS[name]
    if f and m:
        return f"{fw}, {mw}"
    return fw if f or not m else mw
