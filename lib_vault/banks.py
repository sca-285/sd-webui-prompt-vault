"""Muse's wider vocabulary, around every scene: wardrobes by kind of place, light sources, styles,
details and doings anyone can have. A scene's own lists come first; these give each part of a card
enough to roll through (fifteen and more) without leaving the scene's world."""

from __future__ import annotations

import re

# ------------------------------------------------------------------ wardrobes
# what people wear, by the kind of place: "f" a woman's, "m" a man's
WARDROBE = {
    "casual": {
        "f": ["t-shirt, jeans", "hoodie, shorts", "sweater, skirt", "cardigan, sundress", "crop top, high-waist jeans",
              "denim jacket, t-shirt, skirt", "blouse, jeans", "striped shirt, shorts", "oversized hoodie", "turtleneck, plaid skirt",
              "tank top, cargo pants", "off-shoulder top, jeans", "polo shirt, skirt", "flannel shirt, jeans", "sweatshirt, leggings",
              "linen shirt, shorts", "camisole, long skirt", "jumpsuit", "overalls, t-shirt", "knit vest, blouse"],
        "m": ["t-shirt, jeans", "hoodie, jeans", "flannel shirt, chinos", "denim jacket, t-shirt", "polo shirt, shorts",
              "sweater, jeans", "henley shirt, jeans", "bomber jacket, t-shirt", "oversized hoodie, cargo pants", "graphic t-shirt, shorts",
              "linen shirt, chinos", "cardigan, t-shirt", "track jacket, jeans", "shirt, rolled sleeves", "sweatshirt, joggers",
              "tank top, shorts", "overshirt, t-shirt", "turtleneck, slacks", "baseball jacket, jeans", "button-up shirt, jeans"],
    },
    "cozy": {
        "f": ["pajamas", "oversized sweater", "oversized shirt, bare legs", "nightgown", "knit cardigan, shorts", "hoodie, pajama pants",
              "camisole, pajama shorts", "loungewear", "bathrobe", "sweater dress", "fleece pajamas", "t-shirt, sleep shorts",
              "silk pajamas", "onesie", "off-shoulder sweater", "cardigan, leggings", "thermal shirt, sweatpants", "knit sweater, socks"],
        "m": ["pajamas", "hoodie, sweatpants", "t-shirt, boxers", "tank top, sweatpants", "knit sweater", "flannel pajamas",
              "bathrobe", "loungewear", "oversized t-shirt", "henley shirt, sweatpants", "cardigan, t-shirt", "thermal shirt",
              "silk pajamas", "fleece jacket, sweatpants", "sweatshirt, shorts", "onesie", "knit cardigan", "t-shirt, pajama pants"],
    },
    "formal": {
        "f": ["evening gown", "cocktail dress", "little black dress", "satin dress", "velvet dress", "sequin dress", "slip dress",
              "off-shoulder dress", "backless dress", "qipao", "wrap dress", "pencil dress", "pantsuit", "halter dress",
              "mermaid dress", "silk blouse, wide-leg pants", "bodycon dress", "one-shoulder dress", "lace dress", "tuxedo dress"],
        "m": ["suit, necktie", "tuxedo, bow tie", "three-piece suit", "double-breasted suit", "dress shirt, vest", "velvet blazer",
              "dinner jacket", "suit, no tie", "turtleneck, blazer", "white suit", "black suit, black shirt", "waistcoat, dress shirt",
              "linen suit", "pinstripe suit", "dress shirt, suspenders", "blazer, open collar", "morning coat", "tailcoat",
              "suit, pocket square", "grey suit, necktie"],
    },
    "business": {
        "f": ["office lady, pencil skirt, blouse", "pantsuit", "blazer, pencil skirt", "blouse, slacks", "sheath dress, blazer",
              "cardigan, pencil skirt", "turtleneck, slacks", "shirt dress", "vest, blouse, skirt", "skirt suit", "silk blouse, skirt",
              "blazer, turtleneck", "button-up shirt, pencil skirt", "trench coat, skirt suit", "pleated skirt, blouse", "wrap dress"],
        "m": ["business suit, necktie", "dress shirt, necktie", "blazer, dress shirt", "suit, loose necktie", "vest, dress shirt",
              "shirt, rolled sleeves, necktie", "cardigan, dress shirt", "turtleneck, blazer", "trench coat, suit", "polo shirt, slacks",
              "sweater vest, dress shirt", "three-piece suit", "suit jacket, open collar", "shirt, suspenders", "salaryman, suit",
              "waistcoat, rolled sleeves"],
    },
    "sporty": {
        "f": ["sports bra, leggings", "gym clothes", "tank top, running shorts", "track suit", "crop top, yoga pants",
              "sports bra, bike shorts", "athletic wear", "tennis dress", "jersey, shorts", "zip-up jacket, leggings",
              "compression top, shorts", "racerback tank top, leggings", "hoodie, joggers", "unitard", "swimsuit, swim cap",
              "volleyball uniform", "basketball uniform", "track jacket, shorts"],
        "m": ["tank top, gym shorts", "compression shirt, shorts", "track suit", "t-shirt, joggers", "sleeveless shirt, shorts",
              "jersey, shorts", "hoodie, sweatpants", "athletic wear", "basketball uniform", "football uniform", "running shorts, shirtless",
              "rash guard, shorts", "track jacket, joggers", "muscle shirt, shorts", "tennis clothes", "cycling jersey, bike shorts",
              "boxing shorts, hand wraps", "baseball uniform"],
    },
    "beach": {
        "f": ["bikini", "one-piece swimsuit", "string bikini", "bikini, sarong", "swimsuit, cover-up", "high-waist bikini",
              "sundress, sandals", "bikini top, denim shorts", "halter bikini", "frilled bikini", "sports bikini", "beach cover-up",
              "crochet bikini", "rash guard, bikini bottom", "linen shirt, bikini", "wetsuit", "side-tie bikini", "monokini"],
        "m": ["swim trunks", "board shorts", "swim trunks, open shirt", "hawaiian shirt, shorts", "tank top, swim trunks",
              "rash guard, board shorts", "linen shirt, shorts", "speedo", "wetsuit", "shirtless, shorts", "sleeveless shirt, shorts",
              "polo shirt, swim trunks", "unbuttoned shirt, board shorts", "t-shirt, swim trunks", "jammers", "beach shorts, sandals"],
    },
    "outdoor": {
        "f": ["hiking clothes", "windbreaker, leggings", "flannel shirt, jeans", "puffer vest, hiking pants", "rain jacket, boots",
              "fleece jacket, shorts", "cargo pants, tank top", "anorak, hiking boots", "sweater, jeans, boots", "parka, beanie",
              "denim jacket, sundress", "field jacket, jeans", "utility vest, t-shirt", "hoodie, hiking shorts", "overalls, boots",
              "raincoat, rain boots", "trench coat, scarf", "camping clothes"],
        "m": ["hiking clothes", "flannel shirt, jeans", "windbreaker, cargo pants", "fleece jacket, hiking pants", "rain jacket, boots",
              "puffer vest, henley shirt", "field jacket, jeans", "anorak, hiking boots", "parka, beanie", "denim jacket, hoodie",
              "utility vest, t-shirt", "canvas jacket, work pants", "sweater, jeans, boots", "raincoat", "camping clothes",
              "overshirt, cargo shorts", "hoodie, hiking shorts", "trench coat"],
    },
    "winter": {
        "f": ["winter coat, scarf", "puffer jacket, beanie", "turtleneck sweater, coat", "fur-trimmed coat", "knit sweater, mittens",
              "ski jacket, ski pants", "duffel coat, scarf", "wool coat, earmuffs", "parka, boots", "cable-knit sweater, scarf",
              "sweater dress, tights", "fur coat", "peacoat, beret", "down jacket, knit hat", "cardigan, scarf, gloves", "snowsuit"],
        "m": ["winter coat, scarf", "puffer jacket, beanie", "peacoat, scarf", "wool coat, gloves", "parka, boots", "ski jacket",
              "cable-knit sweater", "turtleneck, overcoat", "duffel coat", "down jacket, knit hat", "fur-trimmed parka",
              "flannel shirt, puffer vest", "trench coat, scarf", "sweater, scarf, gloves", "shearling jacket", "snowsuit"],
    },
    "street": {
        "f": ["leather jacket, mini skirt", "streetwear", "oversized hoodie, bike shorts", "techwear", "crop top, cargo pants",
              "bomber jacket, ripped jeans", "plaid skirt, combat boots", "fishnets, shorts", "varsity jacket, skirt",
              "windbreaker, track pants", "graphic t-shirt, ripped jeans", "punk fashion", "denim jacket, fishnets", "chain belt, jeans",
              "harness, tank top", "oversized jacket, bike shorts", "gothic fashion", "y2k fashion"],
        "m": ["leather jacket, ripped jeans", "streetwear", "oversized hoodie, cargo pants", "techwear", "bomber jacket, joggers",
              "varsity jacket, jeans", "windbreaker, track pants", "graphic t-shirt, ripped jeans", "punk fashion", "denim vest, jeans",
              "chain necklace, tank top", "oversized t-shirt, shorts", "sleeveless hoodie, joggers", "coach jacket, jeans",
              "gothic fashion", "camo jacket, cargo pants", "clothes around waist, t-shirt", "y2k fashion"],
    },
    "party": {
        "f": ["sequin dress", "bodycon dress", "glitter top, mini skirt", "metallic dress", "crop top, leather pants", "tube top, mini skirt",
              "party dress", "halter top, shorts", "slip dress", "fishnet top, skirt", "cocktail dress", "backless dress",
              "latex dress", "corset top, jeans", "neon top, skirt", "jumpsuit", "rave outfit", "off-shoulder dress"],
        "m": ["open shirt, chain necklace", "leather jacket, black t-shirt", "silk shirt, slacks", "black shirt, jeans",
              "velvet blazer, t-shirt", "patterned shirt, chinos", "mesh shirt", "tank top, jeans", "bomber jacket, black jeans",
              "unbuttoned shirt, slacks", "suit, no tie", "neon shirt", "rave outfit", "sleeveless shirt, cargo pants",
              "printed shirt, shorts", "turtleneck, blazer"],
    },
    "rustic": {
        "f": ["sundress, straw hat", "overalls, t-shirt", "gingham dress", "flannel shirt, jeans", "peasant blouse, long skirt",
              "apron, dress", "cardigan, long skirt", "denim overalls", "plaid shirt, boots", "linen dress", "work dress, apron",
              "sweater, corduroy skirt", "farm clothes", "cotton dress, boots", "knit shawl, dress", "rubber boots, raincoat"],
        "m": ["overalls, t-shirt", "flannel shirt, jeans", "straw hat, linen shirt", "work shirt, suspenders", "plaid shirt, boots",
              "henley shirt, work pants", "farm clothes", "denim jacket, jeans", "knit sweater, corduroy pants", "vest, rolled sleeves",
              "canvas jacket", "work boots, jeans", "linen shirt, trousers", "flat cap, wool vest", "apron, work shirt", "rubber boots, raincoat"],
    },
    "bath": {
        "f": ["towel", "bathrobe", "towel wrap", "towel on head, bathrobe", "yukata", "swimsuit", "bath towel, wet hair",
              "spa robe", "camisole, shorts", "short robe", "bikini", "slip, wet hair", "kimono robe", "hand towel"],
        "m": ["towel around waist", "bathrobe", "yukata", "swim trunks", "towel on shoulders", "spa robe", "shirtless, shorts",
              "kimono robe", "towel, wet hair", "open robe", "tank top, shorts", "hand towel"],
    },
    "fantasy": {
        "f": ["adventurer clothes", "leather armor", "cloak, tunic", "elven dress", "mage robe", "corset, long skirt", "chainmail",
              "ranger outfit", "priestess robe", "battle dress", "fur cloak, leather armor", "noblewoman dress", "hooded cloak",
              "bikini armor", "witch hat, robe", "plate armor", "circlet, flowing gown", "tunic, leggings, boots"],
        "m": ["adventurer clothes", "leather armor", "cloak, tunic", "mage robe", "chainmail", "plate armor", "ranger outfit",
              "fur cloak, leather armor", "hooded cloak", "noble attire", "doublet, cape", "tabard, chainmail", "monk robe",
              "barbarian, fur", "elven armor", "tunic, belt, boots", "battle armor, cape", "wizard robe"],
    },
    "historical": {
        "f": ["victorian dress", "corset, petticoat", "regency dress", "kimono", "hanfu", "1920s flapper dress", "renaissance gown",
              "bustle dress", "1950s dress", "edwardian dress", "maid outfit", "hoop skirt", "peasant dress", "qipao", "toga",
              "medieval dress", "riding habit", "1940s dress"],
        "m": ["victorian suit", "tailcoat, top hat", "regency coat", "kimono, hakama", "hanfu", "1920s suit, fedora", "doublet",
              "military uniform", "frock coat", "toga", "samurai armor", "waistcoat, cravat", "medieval tunic", "1950s suit",
              "trench coat, fedora", "butler outfit", "peasant clothes", "1940s suit"],
    },
    "scifi": {
        "f": ["bodysuit", "plugsuit", "space suit", "futuristic armor", "techwear", "pilot suit", "cyberpunk jacket", "neon jacket",
              "uniform, futuristic", "latex bodysuit", "mecha pilot suit", "holographic jacket", "power armor", "flight suit",
              "visor, bodysuit", "glowing clothes", "chrome armor", "starship uniform"],
        "m": ["bodysuit", "space suit", "futuristic armor", "techwear", "pilot suit", "cyberpunk jacket", "uniform, futuristic",
              "mecha pilot suit", "power armor", "flight suit", "visor, armor", "trench coat, cybernetics", "glowing clothes",
              "chrome armor", "starship uniform", "tactical vest, techwear", "neon jacket", "exosuit"],
    },
    "steampunk": {
        "f": ["steampunk, corset, goggles", "victorian dress, gears", "aviator jacket, goggles", "corset, bustle skirt",
              "waistcoat, pocket watch", "leather corset, top hat", "brass armor", "airship captain coat", "lab coat, goggles",
              "leather gloves, corset", "tailcoat, skirt", "explorer outfit, goggles"],
        "m": ["steampunk, goggles, vest", "aviator jacket, goggles", "waistcoat, pocket watch", "top hat, tailcoat", "brass armor",
              "airship captain coat", "lab coat, goggles", "leather apron, gears", "frock coat, gears", "suspenders, rolled sleeves, goggles",
              "explorer outfit", "mechanical arm, vest"],
    },
    "wasteland": {
        "f": ["torn clothes, bandana", "leather jacket, cargo pants", "tactical vest", "gas mask, coat", "tattered cloak",
              "scavenger outfit", "military jacket, tank top", "duster coat", "ripped jeans, crop top", "makeshift armor",
              "bandages, tank top", "hooded poncho", "dirty overalls", "utility belt, jacket"],
        "m": ["torn clothes, bandana", "leather jacket, cargo pants", "tactical vest", "gas mask, coat", "tattered cloak",
              "scavenger outfit", "military jacket", "duster coat", "makeshift armor", "bandages, tank top", "hooded poncho",
              "dirty overalls", "utility belt, jacket", "ripped jeans, vest"],
    },
    "nautical": {
        "f": ["sailor dress", "striped shirt, shorts", "captain coat", "pirate outfit", "rain jacket, boots", "linen dress",
              "bikini, sarong", "navy uniform", "knit sweater, beanie", "corset, pirate hat", "wetsuit", "oilskin coat"],
        "m": ["sailor uniform", "striped shirt, shorts", "captain coat", "pirate outfit", "fisherman sweater", "rain jacket, boots",
              "navy uniform", "linen shirt, rolled sleeves", "knit sweater, beanie", "pirate hat, coat", "wetsuit", "oilskin coat"],
    },
    "stage": {
        "f": ["stage outfit", "idol outfit", "sequin dress", "leather jacket, crop top", "ballet tutu", "dance costume", "gothic dress",
              "glitter jumpsuit", "rockstar outfit", "evening gown", "corset, fishnets", "showgirl costume", "kpop outfit", "cheongsam"],
        "m": ["stage outfit", "leather jacket, black jeans", "sequin jacket", "rockstar outfit", "tuxedo", "dance costume",
              "open shirt, chain necklace", "kpop outfit", "suit, no tie", "glitter jacket", "tank top, ripped jeans", "conductor coat"],
    },
    "retro": {
        "f": ["80s fashion", "neon windbreaker", "leg warmers, leotard", "shoulder pads, blazer", "high-waist jeans, crop top",
              "90s fashion", "denim jacket, mini skirt", "scrunchie, oversized sweater", "track suit, retro", "slip dress, choker",
              "polka dot dress", "flannel shirt, ripped jeans", "aerobics outfit", "varsity jacket"],
        "m": ["80s fashion", "neon windbreaker", "denim jacket, jeans", "90s fashion", "track suit, retro", "flannel shirt, ripped jeans",
              "leather jacket, white t-shirt", "hawaiian shirt", "varsity jacket", "bomber jacket", "suit, shoulder pads",
              "oversized shirt, baggy jeans", "letterman jacket", "polo shirt, khakis"],
    },
    "festive": {
        "f": ["christmas sweater", "santa costume", "red dress, fur trim", "winter coat, scarf", "kimono", "witch costume",
              "party dress", "knit sweater, scarf", "yukata", "halloween costume", "velvet dress", "bunny costume", "new year kimono",
              "elf costume"],
        "m": ["christmas sweater", "santa costume", "winter coat, scarf", "kimono", "vampire costume", "suit, red necktie",
              "knit sweater, scarf", "yukata", "halloween costume", "velvet blazer", "jinbei", "reindeer sweater", "pumpkin costume",
              "elf costume"],
    },
    "school": {
        "f": ["school uniform", "serafuku", "blazer, pleated skirt", "sweater vest, pleated skirt", "cardigan, school uniform",
              "gym uniform", "track suit", "sailor collar, skirt", "blouse, ribbon, skirt", "hoodie, school uniform", "lab coat, uniform",
              "blouse, pencil skirt", "smock, uniform", "winter uniform, scarf"],
        "m": ["school uniform", "gakuran", "blazer, necktie", "sweater vest, shirt", "cardigan, school uniform", "gym uniform",
              "track suit", "shirt, loose necktie", "hoodie, school uniform", "lab coat, uniform", "dress shirt, necktie",
              "winter uniform, scarf"],
    },
    "lingerie": {
        "f": ["lace lingerie", "silk robe, lingerie", "corset, stockings", "babydoll", "garter belt, thighhighs", "sheer bodysuit",
              "latex lingerie", "fishnet bodystocking", "teddy", "strappy lingerie", "bra, panties", "harness, lingerie",
              "chemise", "negligee", "body chain", "open robe, lingerie", "leather lingerie", "bunny suit"],
        "m": ["boxer briefs", "jockstrap", "silk robe, open", "leather harness", "briefs", "open shirt, briefs", "latex shorts",
              "unbuttoned shirt, bare chest", "towel around waist", "mesh shirt, briefs", "suspenders, shirtless", "bow tie, shirtless",
              "leather pants, shirtless", "open robe, boxers"],
    },
}

# a theme's usual wardrobes; a place's own words can take it elsewhere (a beach, the snow, a gym)
THEME_WARDROBE = {
    "Portrait": ("casual", "formal"), "Fashion": ("formal", "street"), "Film": ("casual", "formal"), "Horror": ("casual", "street"),
    "Street": ("street", "casual"), "Home": ("cozy", "casual"), "Food": ("casual",), "Architecture": ("casual", "business"),
    "Nature": ("outdoor",), "Creature": ("fantasy",), "Myth": ("fantasy",), "Sci-fi": ("scifi",), "Sports": ("sporty",),
    "Party": ("party",), "Bath & shower": ("bath",), "Bedroom": ("cozy",), "Fantasy": ("fantasy",), "Gym": ("sporty",),
    "Hotel": ("formal", "cozy"), "Office": ("business",), "Outdoors": ("outdoor", "casual"), "Studio": ("casual", "formal"),
    "Travel": ("casual", "outdoor"), "Countryside": ("rustic",), "Historical": ("historical",), "Post-apocalypse": ("wasteland",),
    "Steampunk": ("steampunk",), "Seafaring": ("nautical",), "Music & stage": ("stage",), "World cities": ("casual", "street"),
    "Retro 80s-90s": ("retro",), "Holidays": ("festive",), "Red light": ("lingerie",), "Kitchen": ("cozy", "casual"),
    "Living room": ("cozy", "casual"), "Balcony": ("casual", "cozy"), "Garden": ("casual", "rustic"), "Restroom": ("casual", "party"),
    "School": ("school",),
}
# a place's words that say what is worn there, whatever the theme (only where the theme is of our own time)
PLACE_WARDROBE = [
    (r"beach|pool|surf|lagoon|island|shore|tropical|swim|lake|waterfall|hot spring|onsen", "beach"),
    (r"snow|ski|winter|ice|frozen|igloo|arctic|cabin bedroom", "winter"),
    (r"gym|yoga|track|court|stadium|boxing|locker|pilates|dojo", "sporty"),
    (r"club|party|disco|rave|bar\b|lounge|casino|karaoke", "party"),
    (r"office|boardroom|cubicle|conference", "business"),
    (r"bath|shower|spa|sauna|hammam", "bath"),
    (r"bedroom|pajama|sleepover|morning bed", "cozy"),
    (r"gala|ball\b|ballroom|opera|wedding|fine dining|penthouse", "formal"),
]
MODERN_THEMES = {"Portrait", "Fashion", "Film", "Horror", "Street", "Home", "Food", "Architecture", "Nature", "Sports", "Party",
                 "Bath & shower", "Bedroom", "Gym", "Hotel", "Office", "Outdoors", "Studio", "Travel", "Countryside", "Music & stage",
                 "World cities", "Kitchen", "Living room", "Balcony", "Garden", "Restroom", "Holidays"}


def wardrobes(theme, title):
    """The wardrobes of a scene: its theme's, and the place's own where its words say so."""
    keys = list(THEME_WARDROBE.get(theme, ("casual",)))
    if theme in MODERN_THEMES:
        low = (title or "").lower()
        for rx, key in PLACE_WARDROBE:
            if re.search(rx, low) and key not in keys:
                keys.insert(0, key)
    return keys


def wear(theme, title, sex):
    """A scene's wider wardrobe for a woman ("f") or a man ("m")."""
    out = []
    for key in wardrobes(theme, title):
        out += WARDROBE[key][sex]
    return out


# ------------------------------------------------------------------ light sources, by kind of space
LIGHT_SOURCE = {
    "out": ["sunlight", "daylight", "natural light", "ambient light", "sunlight through clouds", "dappled sunlight",
            "reflected light", "skylight", "street lights", "lanterns", "string lights", "moonlight", "starlight", "city glow"],
    "view": ["window light", "natural light", "ambient light", "light through window", "sunlight through curtains",
             "lamp light", "ceiling light", "soft indoor light", "warm interior light", "skylight", "light through blinds",
             "moonlight through window", "fairy lights", "night lamp"],
    "in": ["ambient light", "indoor lighting", "ceiling light", "lamp light", "practical lights", "artificial light",
           "warm interior light", "recessed lighting", "soft indoor light", "candlelight", "dim light", "warm light",
           "overhead light", "table lamp", "wall sconce"],
    # under the sea, in space, in an underworld: no sky, no room
    "none": ["ambient light", "dim light", "eerie glow", "soft glow", "glowing light", "faint light", "cold light",
             "bioluminescence", "otherworldly light", "diffuse glow"],
}
# old worlds have no electric light
OLD_LIGHT = {"Historical", "Fantasy", "Myth", "Creature", "Steampunk", "Seafaring"}
ELECTRIC = re.compile(r"street lights|ceiling|fluorescent|neon|led |recessed|night lamp|fairy lights|city glow|spotlight|lamp light|"
                      r"indoor lighting|artificial|practical|overhead light|table lamp|wall sconce")


def light_sources(theme, exposure):
    out = LIGHT_SOURCE.get(exposure or "in", LIGHT_SOURCE["in"])
    if theme in OLD_LIGHT:
        out = [x for x in out if not ELECTRIC.search(x)]
        out += ["torchlight", "candlelight", "firelight", "lantern light", "oil lamp light", "hearth glow"] if exposure in ("in", "view") \
            else ["lantern light", "campfire glow", "torchlight, night"] if exposure == "out" else []
    return list(dict.fromkeys(out))


# ------------------------------------------------------------------ where: the same place, seen a little differently
SETTING_TOUCH = {
    "out": ["", "scenery", "detailed background", "blurry background", "background", "wide landscape", "horizon", "depth"],
    "view": ["", "detailed background", "blurry background", "interior", "background", "cozy atmosphere"],
    "in": ["", "detailed background", "blurry background", "interior", "background", "cluttered"],
    "none": ["", "detailed background", "blurry background", "background", "depth", "atmosphere"],
}

# ------------------------------------------------------------------ details anyone can see there
DETAIL_ANY = {
    "out": ["birds", "fallen leaves", "clouds", "wind", "grass", "distant mountains", "flowers", "trees", "sky",
            "power lines", "signs"],
    "view": ["curtains", "potted plant", "picture frame", "books", "rug", "lamp", "window", "cushions", "vase", "shelves"],
    "in": ["potted plant", "picture frame", "shelves", "lamp", "rug", "boxes", "clock", "poster", "chairs", "mirror"],
    "none": ["floating particles", "drifting motes", "faint glow", "shadows", "mist", "debris"],
}
OLD_DETAIL = re.compile(r"power lines|signs|poster|clock|potted plant|picture frame|lamp")

# ------------------------------------------------------------------ styles anyone can take
STYLE_ANY = ["photorealistic", "anime illustration", "digital painting", "watercolor", "oil painting", "film photography",
             "cinematic", "concept art", "cel shading", "semi-realistic", "3d render", "ink illustration", "pastel illustration",
             "analog photo", "detailed illustration", "painterly", "manga style", "realistic", "soft illustration",
             "35mm photograph", "studio photography", "matte painting"]
STYLE_NSFW = ["photorealistic", "hentai", "anime coloring", "digital painting", "oil painting", "boudoir photography",
              "erotic illustration", "painterly", "semi-realistic", "3d render", "cel shading", "realistic", "glamour photography",
              "soft focus photography", "detailed illustration", "film photography", "ink illustration", "cinematic"]

# ------------------------------------------------------------------ doings and poses for anyone, anywhere
# "modern" ones are only for themes of our own time
ACT_ANY = {
    "solo": ["standing", "walking", "looking around", "turning around", "stretching", "leaning forward", "posing",
             "looking back", "looking up", "sitting", "crouching", "waiting",
             "daydreaming", "humming", "lost in thought", "pacing", "resting"],
    "pair": ["talking", "laughing together", "walking side by side", "standing together", "looking at each other",
             "whispering", "joking", "holding hands", "arm in arm", "leaning on another", "side by side",
             "facing another", "shoulder to shoulder", "back to back"],
    "groups": ["chatting", "laughing together", "standing together", "walking together", "posing together", "huddle",
               "gathered around", "group pose", "talking in circle", "cheering", "sitting together"],
}
ACT_MODERN = {
    "solo": ["holding phone", "taking selfie", "checking phone", "listening to music, earphones", "texting", "taking photo",
             "drinking coffee", "holding drink"],
    "pair": ["taking selfie together", "looking at phone together", "sharing earphones", "taking photo of another"],
    "groups": ["group selfie", "taking photos", "looking at phones"],
}
# gestures for two or more people
GESTURE_MORE = {
    "pair": ["hand on another's back", "fist bump", "linked arms", "pinky swear", "hand on another's arm", "pointing at another",
             "heads together", "pat on head", "nudging another", "hand on another's waist"],
    "groups": ["linked arms", "fist bump", "hands together", "pointing", "peace sign", "thumbs up", "hand on shoulder",
               "arms raised", "clapping", "group high five"],
}

# ------------------------------------------------------------------ shot sizes, for people and for places
# close shots are for one person: two or more do not fit in them
CLOSE_SHOTS = {"extreme close-up", "close-up", "face focus", "medium close-up", "portrait", "bust shot"}
SHOT_PEOPLE = ["upper body", "cowboy shot", "full body", "portrait", "medium shot", "close-up", "wide shot", "knees up",
               "head out of frame", "feet out of frame", "lower body", "very wide shot", "bust shot", "waist up",
               "full shot", "extreme close-up", "face focus", "medium close-up"]
SHOT_PLACE = ["wide shot", "very wide shot", "establishing shot", "scenery", "landscape", "panorama", "wide shot, scenery",
              "medium shot", "still life", "interior view", "exterior view", "vista"]

# ------------------------------------------------------------------ a job's clothes, worn a little differently
JOB_TOUCH = ["rolled sleeves", "name tag", "id badge", "gloves", "loose collar", "glasses", "wristwatch", "boots", "sneakers",
             "scarf", "jacket over shoulders", "hair tie", "lanyard", "belt", "unbuttoned collar", "cap"]
# what a job's effects can be joined by
FX_ANY = ["sparkles", "light particles", "glint", "motion blur", "glow", "bokeh lights", "floating dust", "lens flare", "steam",
          "speed lines", "shimmer", "soft glow"]
