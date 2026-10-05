"""Muse scenes as tags. A theme has places, a place has zones; every zone is a scene at every level.

Authoring: entries are separated by "|", the tags of one entry by ",".
  P(title, f="wear|wear", m="wear|wear", light="...", mood="calm happy", surf="bed:bed|wall:window",
    acts=dict(solo=..., pair=..., groups=...), zones=[Z(...), Z(...), Z(...)])
  Z(title, where="...", detail="...", solo="...", pair="...", groups="...", surf=None, light=None)
"""
import json, os, random, re, sys
REPO = os.environ.get("REPO") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from lib_vault import when as W
from skies import SKY, CLIMATE

OUT = os.path.join(REPO, "data", "muse_scenes")
os.makedirs(OUT, exist_ok=True)
LEVELS = ("sfw", "suggestive", "nude", "explicit")


def L(s):
    """'a, b | c' -> ['a, b', 'c']"""
    if s is None:
        return []
    if isinstance(s, list):
        return s
    return [x.strip() for x in s.split("|") if x.strip()]


# ------------------------------------------------------------------ people
F_TEASE = L("lace lingerie | open robe, lingerie | oversized shirt, bare legs | unbuttoned shirt, bra peek | towel, wet hair"
            " | slip dress, strap slip | babydoll | garter belt, thighhighs | crop top, panties | sheer nightgown | string bikini"
            " | off-shoulder sweater, panties")
M_TEASE = L("open shirt, bare chest | towel around waist | boxer briefs | unbuttoned pants, shirtless | sweatpants, shirtless"
            " | jockstrap | open robe, bare chest | tank top, briefs")

# anthros: species, features (female and male alike unless given apart)
ANTHROS = [
    ("wolf", L("grey fur, bushy tail, pointy ears | black fur, amber eyes, wolf tail"), [], []),
    ("fox", L("orange fur, white chest fur, fluffy tail | arctic fox, white fur, fluffy tail"), [], []),
    ("husky", L("husky markings, blue eyes, curled tail"), [], []),
    ("german shepherd", L("tan fur, black back, pointy ears"), [], []),
    ("hyena", L("spotted fur, round ears, short mane"), [], []),
    ("cat", L("tabby fur, long tail, whiskers | black cat, green eyes"), [], []),
    ("tiger", L("orange fur, black stripes, white muzzle | white tiger, black stripes"), [], []),
    ("lion", [], L("tawny fur, tufted tail"), L("mane, tawny fur, tufted tail")),
    ("leopard", L("spotted fur, long tail | snow leopard, thick tail, spotted fur"), [], []),
    ("cheetah", L("spotted fur, tear marks, slim build"), [], []),
    ("lynx", L("tufted ears, short tail, spotted fur"), [], []),
    ("panther", L("black fur, yellow eyes, sleek"), [], []),
    ("deer", [], L("spotted fur, white tail, large ears"), L("antlers, brown fur")),
    ("horse", L("mane, hooves, horse tail | black horse, long mane, hooves"), [], []),
    ("zebra", L("zebra stripes, mane, hooves"), [], []),
    ("cow", [], L("horns, cow print, hooves"), []),
    ("bull", [], [], L("horns, nose ring, hooves, muscular")),
    ("goat", [], L("curled horns, hooves, goat ears"), L("ram horns, goat beard, hooves")),
    ("rabbit", L("long ears, fluffy tail, white fur | lop ears, brown fur"), [], []),
    ("bear", L("brown fur, round ears, burly"), [], []),
    ("panda", L("black and white fur, round ears"), [], []),
    ("otter", L("brown fur, webbed hands, thick tail"), [], []),
    ("mouse", L("round ears, thin tail, grey fur"), [], []),
    ("rat", L("long tail, grey fur, whiskers"), [], []),
    ("squirrel", L("bushy tail, red fur"), [], []),
    ("eagle", L("feathers, wings, beak, talons"), [], []),
    ("owl", L("feathers, wings, large eyes, beak"), [], []),
    ("raven", L("black feathers, wings, beak"), [], []),
    ("shark", L("grey skin, dorsal fin, gills, sharp teeth"), [], []),
    ("orca", L("black and white skin, dorsal fin, tail fin"), [], []),
    ("dolphin", L("smooth grey skin, blowhole, tail fin"), [], []),
    ("lizard", L("green scales, long tail, slit pupils"), [], []),
    ("crocodile", L("armored scales, long snout, thick tail"), [], []),
    ("dragon", L("scales, horns, wings, long tail | eastern dragon, scales, whiskers, horns"), [], []),
]
ANTHRO_BODIES = [(k, sex, feat) for k, both, fe, ma in ANTHROS for sex, own in (("female", fe), ("male", ma)) for feat in (own or both)]

# beings that are not human, by kind: who they are, never what they wear (that is the Wear part)
BEINGS = {
    "mythic": L("1girl, solo, vampire, pale skin, red eyes, fangs | 1boy, solo, vampire, pale skin, fangs | 1girl, solo, elf, pointy ears"
                " | 1boy, solo, elf, pointy ears | 1girl, solo, dark elf, pointy ears, dark skin | 1girl, solo, succubus, demon horns, bat wings, demon tail"
                " | 1boy, solo, incubus, demon horns, demon tail | 1girl, solo, demon girl, horns, demon tail | 1boy, solo, demon, horns, red skin"
                " | 1girl, solo, angel, feathered wings, halo | 1boy, solo, angel, feathered wings, halo | 1girl, solo, fallen angel, black wings"
                " | 1boy, solo, fallen angel, black wings | 1girl, solo, kitsune, fox ears, fox tail | 1girl, solo, oni, horns | 1boy, solo, oni, horns, red skin"
                " | 1girl, solo, mermaid, fish tail | 1boy, solo, merman, fish tail | 1girl, solo, dryad, bark skin, leaves in hair"
                " | 1boy, solo, satyr, goat horns, goat legs | 1girl, solo, centaur, horse body | 1girl, solo, lamia, snake tail"
                " | 1girl, solo, harpy, feathered arms, bird legs | 1girl, solo, dragon girl, dragon horns, dragon tail"
                " | 1boy, solo, dragon boy, dragon horns, scales | 1girl, solo, orc, green skin, tusks | 1boy, solo, orc, green skin, tusks, muscular"
                " | 1boy, solo, minotaur, bull horns | 1girl, solo, pixie, fairy wings, pointy ears | 1boy, solo, fairy, insect wings"
                " | 1girl, solo, gorgon, snake hair | 1girl, solo, genie, smoke tail | 1girl, solo, yuki-onna, pale skin, frost"
                " | 1boy, solo, tengu, black wings | 1girl, solo, cat girl, cat ears, cat tail"),
    "monster": L("1boy, solo, werewolf, monster, wolf head, claws, fur | 1girl, solo, werewolf, monster girl, claws, fur"
                 " | 1boy, solo, frankenstein's monster, stitches, bolts in neck | 1girl, solo, bride of frankenstein, stitches, streaked hair"
                 " | 1girl, solo, zombie girl, stitches, grey skin | 1boy, solo, zombie, grey skin | 1girl, solo, ghost, translucent"
                 " | 1girl, solo, mummy, bandages | 1boy, solo, mummy, bandages | 1girl, solo, slime girl, translucent body"
                 " | 1boy, solo, gargoyle, stone skin, wings | 1girl, solo, gargoyle girl, stone skin, wings | 1boy, solo, golem, stone body"
                 " | 1boy, solo, lich, glowing eyes, crown | 1girl, solo, banshee, ghostly | 1girl, solo, alraune, plant girl, flower"
                 " | 1girl, solo, arachne, spider legs | 1girl, solo, jiangshi, ofuda | 1boy, solo, ghoul, claws | 1girl, solo, skeleton girl, bones"),
    "synth": L("1girl, solo, android, mechanical joints | 1boy, solo, android, mechanical joints | 1girl, solo, gynoid, porcelain skin"
               " | 1boy, solo, humanoid robot, metal body | 1girl, solo, robot girl, glowing eyes | 1girl, solo, cyborg, mechanical arm"
               " | 1boy, solo, cyborg, cybernetic eye | 1girl, solo, mecha musume, mechanical parts | 1boy, solo, mecha, giant robot"
               " | 1girl, solo, alien, blue skin, antennae | 1boy, solo, alien, grey skin, large eyes | 1girl, solo, alien girl, green skin"
               " | 1girl, solo, hologram, translucent, glitch | 1boy, solo, cyborg soldier, visor | 1girl, solo, android, glowing seams"
               " | 1girl, solo, replicant, synthetic skin | 1boy, solo, mechanoid, exposed wiring"),
}
# real creatures, for the Animals cast: SFW only, by theme where they belong
ANIMALS = {
    "*": L("cat, sitting | black cat, sleeping | dog, lying down | crow, perched | sparrow | butterfly | pigeon | fox, curled up"),
    "wild": L("red fox | deer, antlers | wolf, howling | rabbit | owl, perched | horse, grazing | brown bear | eagle, flying | lynx"
              " | squirrel | hedgehog | badger | swan | heron"),
    "sea": L("seagull | dolphin, jumping | sea turtle | crab | whale | jellyfish | octopus | pelican | seal"),
    "exotic": L("tiger, prowling | lion, mane | elephant | panther | snake, coiled | crocodile | parrot | gorilla | cheetah, running"
                " | wolf pack | polar bear | komodo dragon | peacock"),
}
ANIMALS_BY_THEME = {"Nature": "wild", "Outdoors": "wild", "Countryside": "wild", "Travel": "wild", "Sports": "*", "Creature": "exotic",
                    "Seafaring": "sea", "Myth": "wild", "Fantasy": "wild", "Post-apocalypse": "wild", "Holidays": "*"}

# ------------------------------------------------------------------ what people do, by level and surface
# {bed} and the like become the zone's own words; "soft" is what someone can lie on
SURF = ("bed", "wall", "table", "chair", "floor", "water")
SOFT = ("bed", "floor")

SFW_GESTURES = {
    "solo": L("hand on hip | hand in own hair | head tilt | hand on own cheek | arms behind back | hand on own chin | adjusting hair"
              " | hand in pocket | arms crossed | looking away | looking at viewer | waving | peace sign | thumbs up"
              " | hand on own chest | fist on hip | hands clasped | finger on chin | stretching arms | hand shading eyes"),
    "pair": L("holding hands | arm around shoulder | hand on another's shoulder | hand on another's cheek | high five | arm hug"
              " | back-to-back | leaning on person | hand on another's head | eye contact | linked arms | pinky swear"
              " | fist bump | hand on another's back | heads together"),
    "groups": L("arms around shoulders | group hug | high five | v | pointing | waving | laughing together | fist bump"
                " | thumbs up | linked arms | arms raised | clapping"),
}
# what anyone can do anywhere, under the place's own
SFW_ANY = {"solo": L("looking at viewer, smile"), "pair": L("chatting, smiling | walking together"),
           "groups": L("group photo | chatting, group")}
# what anyone does with what a spot has, SFW: added to every zone's own doings
SFW_SURF = {
    "solo": {"bed": L("sitting on {bed} | lying on {bed}, reading | sitting on edge, {bed} | lying on {bed}, looking up"),
             "wall": L("leaning against {wall} | back against {wall} | hand on {wall} | standing by {wall}"),
             "table": L("sitting at {table} | leaning on {table} | elbows on {table} | standing by {table}"),
             "chair": L("sitting on {chair} | sitting on {chair}, crossed legs | leaning back, {chair} | sitting sideways, {chair}"),
             "floor": L("sitting on {floor} | kneeling on {floor} | sitting cross-legged, {floor} | lying on {floor}"),
             "water": L("standing in {water} | wading in {water} | sitting by {water} | hand in {water}")},
    "pair": {"bed": L("sitting on {bed}, together | lying on {bed}, talking"), "wall": L("leaning against {wall}, together"),
             "table": L("sitting at {table}, facing another | leaning on {table}, together"),
             "chair": L("sitting side by side, {chair}"), "floor": L("sitting on {floor}, together"),
             "water": L("standing in {water}, together | splashing, {water}")},
    "groups": {"table": L("sitting around {table}"), "chair": L("sitting in row, {chair}"), "floor": L("sitting on {floor}, circle"),
               "wall": L("lined up, {wall}"), "water": L("in {water}, together")},
}
TEASE = {
    "solo": {"bed": L("lying on {bed}, on stomach | kneeling on {bed} | on back, on {bed}, legs up | sitting on {bed}, knees up"),
             "wall": L("leaning against {wall} | back against {wall}, looking at viewer"),
             "table": L("sitting on {table}, crossed legs | leaning on {table}, bent over"),
             "chair": L("sitting on {chair}, crossed legs | straddling {chair}"),
             "floor": L("sitting on {floor}, hugging knees | kneeling on {floor}"),
             "water": L("standing in {water}, looking back | wading in {water}"),
             "*": L("looking back | arms up, stretching | lip biting | undressing | strap slip | hand on own chest"
                    " | clothes pull | looking at viewer, seductive smile | shirt lift | bending forward"
                    " | hand on own thigh | arched back | unbuttoning shirt | looking over shoulder | hip sway")},
    "pair": {"bed": L("lying on {bed}, kiss | on {bed}, straddling"), "wall": L("against {wall}, kiss | pinned against {wall}"),
             "table": L("sitting on {table}, kiss"), "chair": L("sitting on lap, {chair}"), "water": L("hug, in {water}"),
             "*": L("kiss | undressing another | hug, hands under clothes | whispering | french kiss | neck kiss | sitting on lap"
                    " | hand on another's thigh | ear nibbling | pulling another closer | forehead to forehead | lap sitting, kiss"
                    " | hands on hips, close | grabbing collar, kiss | embrace from behind | unzipping another")},
    "groups": {"bed": L("lying on {bed}, cuddling"), "water": L("splashing, in {water}"),
               "*": L("kiss, group | undressing another | lounging, flirting | neck kiss | dancing close | sitting on laps"
                      " | whispering, group | hands on another's body | toasting, flirting | group hug, close | kiss on cheek"
                      " | pulling another close | strip game | body shots | feeding another | massage, shoulders"
                      " | hands under clothes | lying together, flirting")},
}
# a woman's own, at the suggestive level
F_TEASE_ACTS = L("skirt lift | adjusting stockings | panty peek | cleavage, leaning forward | pulling down strap | bra peek"
                 " | lifting skirt hem | adjusting bra")
NUDE = {
    "solo": {"bed": L("lying on {bed} | on side, on {bed} | sitting on {bed}, knees up | on stomach, on {bed}, legs up"),
             "floor": L("lying on {floor} | sitting on {floor}, hugging knees"),
             "water": L("standing in {water} | bathing, in {water} | wet body, in {water}"),
             "chair": L("sitting on {chair}, crossed legs"), "table": L("sitting on {table}"),
             "wall": L("leaning against {wall} | back against {wall}"),
             "*": L("standing, contrapposto | arms up, stretching | looking back | hands behind head | sitting, knees up"
                    " | covering breasts | hand on own hip | hair over shoulder | twisting torso | kneeling, upright"
                    " | reclining | stretching on toes | crossing arms under chest | towel in hand | looking over shoulder")},
    "pair": {"bed": L("lying together, on {bed} | cuddling, on {bed} | spooning, on {bed}"), "floor": L("lying together, on {floor}"),
             "water": L("bathing together, in {water}"), "wall": L("hug, against {wall}"),
             "*": L("hug | kiss | forehead to forehead | caressing | holding hands | back-to-back | hand on another's cheek"
                    " | embrace from behind | lying on chest | stroking hair | intertwined fingers | head on shoulder | slow dance"
                    " | tracing skin | nuzzling")},
    "groups": {"bed": L("cuddling, on {bed} | lying together, on {bed}"), "floor": L("lounging, on {floor}"),
               "water": L("bathing together, in {water}"), "*": L("group hug | lounging together | sitting in circle | arms around shoulders"
                                                                   " | resting heads on laps | intertwined | posing together | leaning on another"
                                                                   " | massage | lying in pile | holding hands, circle | stretching together"
                                                                   " | back to back, sitting | caressing another | kiss, group | dancing together")},
}
SEX = {
    "1girl": {"bed": L("female masturbation, on {bed} | fingering, spread legs, on {bed} | vibrator, on back, on {bed}"),
              "floor": L("female masturbation, on {floor}, spread legs | dildo riding, on {floor}"),
              "water": L("female masturbation, in {water}"), "chair": L("female masturbation, on {chair}, legs over armrests"),
              "table": L("sitting on {table}, fingering"), "wall": L("female masturbation, against {wall}"),
              "*": L("female masturbation | spread legs, fingering | spread pussy | grabbing own breast | presenting, from behind"
                     " | clitoral stimulation | spread legs, looking at viewer")},
    "1boy": {"bed": L("male masturbation, on {bed}"), "chair": L("male masturbation, on {chair}, spread legs"),
             "water": L("male masturbation, in {water}"), "wall": L("male masturbation, against {wall}"),
             "*": L("male masturbation | erection, looking at viewer | penis grab | precum, erection | spread legs, erection")},
    "1girl1boy": {
        "soft": L("missionary, on {soft} | cowgirl position, on {soft} | reverse cowgirl position, on {soft} | doggystyle, on {soft}"
                  " | spooning, sex, on {soft} | 69, on {soft} | mating press | amazon position | piledriver | prone bone | lotus position"
                  " | face sitting | paizuri | breast sucking, sex | thigh sex | full nelson | girl on top | boy on top"),
        "wall": L("standing sex, against {wall} | sex from behind, against {wall} | suspended congress, against {wall}"),
        "table": L("sex, on {table} | bent over {table}, sex from behind | missionary, on {table}"),
        "chair": L("sitting on lap, sex, {chair} | reverse cowgirl position, on {chair} | upright straddle, {chair}"),
        "water": L("sex, in {water} | standing sex, in {water}"),
        "*": L("fellatio, looking up | cunnilingus | deepthroat | breast sucking | fingering | handjob | anilingus"
               " | standing sex | sex from behind | kiss, sex | irrumatio"),
    },
    "2girls": {
        "soft": L("tribadism, on {soft} | 69, on {soft} | face sitting | scissoring | breast sucking | fingering | strap-on, sex"
                  " | cunnilingus, spread legs | anilingus | girl on top, kiss | double dildo"),
        "wall": L("fingering, against {wall}"), "table": L("cunnilingus, on {table}"), "chair": L("straddling, {chair}, fingering"),
        "water": L("fingering, in {water}"),
        "*": L("kiss, fingering | cunnilingus | breast sucking | licking nipple | grinding | breast press"),
    },
    "2boys": {
        "soft": L("anal, missionary, on {soft} | anal, from behind, on {soft} | anal, straddling | prone bone | 69 | anilingus"
                  " | spooning, anal | legs up, anal | mutual masturbation | full nelson"),
        "wall": L("anal, standing, against {wall}"), "table": L("bent over {table}, anal"), "chair": L("straddling, {chair}, anal"),
        "water": L("anal, in {water}"),
        "*": L("fellatio | frottage, kiss | deepthroat | licking nipple | handjob | suspended congress"),
    },
    "harem": {
        "soft": L("group sex, cowgirl position | face sitting, cowgirl position | cooperative paizuri | lineup, doggystyle"
                  " | group sex, taking turns | harem, kiss, cowgirl position | double cunnilingus"),
        "table": L("bent over {table}, group sex"), "wall": L("standing sex, against {wall}, multiple girls"),
        "water": L("group sex, in {water}"), "*": L("cooperative fellatio | double fellatio | group sex, kiss | harem, handjob | harem, breast sucking"
                                        " | multiple girls, kiss, sex | cooperative handjob | girl on top, kiss, harem | harem, paizuri"
                                        " | sex from behind, multiple girls | harem, cunnilingus | group sex, fingering"),
    },
    "reverse": {
        "soft": L("double penetration | spitroast | gangbang | triple penetration | cowgirl position, fellatio | group sex, sandwiched"
                  " | breast sucking, multiple boys"),
        "table": L("spitroast, on {table}"), "wall": L("standing sex, against {wall}, multiple boys"), "water": L("group sex, in {water}"),
        "*": L("double handjob | fellatio, multiple boys | group sex | double fellatio | bukkake | sex from behind, fellatio"
               " | breast sucking, multiple boys | group sex, girl on top | handjob, fellatio | cunnilingus, multiple boys"
               " | standing sex, multiple boys | gangbang, kiss"),
    },
    "mixed": {"soft": L("orgy | partner swap | daisy chain | orgy, 69 | orgy, doggystyle | group sex, cowgirl position"),
              "table": L("group sex, on {table}"), "water": L("group sex, in {water}"), "*": L("group sex | orgy, kiss | fellatio, orgy | orgy, cunnilingus"
                                                 " | group sex, from behind | orgy, handjob | orgy, fingering | group sex, girl on top"
                                                 " | orgy, breast sucking | group sex, standing sex | orgy, paizuri | group sex, kiss")},
    "girls": {"soft": L("daisy chain, cunnilingus | breast sucking, fingering | strap-on, group sex | face sitting, tribadism"
                        " | yuri, group sex, kiss"),
              "water": L("group sex, in {water}"), "*": L("yuri, group sex | kiss, fingering | breast press, kiss | cunnilingus, yuri"
                                                 " | breast sucking, yuri | tribadism, yuri | fingering, group | face sitting, yuri"
                                                 " | licking nipple, yuri | strap-on, yuri | grinding, yuri | anilingus, yuri")},
    "boys": {"soft": L("anal, group sex | gangbang | anilingus | spitroast | frottage, group sex"), "water": L("group sex, in {water}"),
             "*": L("yaoi, group sex | fellatio, group sex | handjob, group sex | anal, yaoi | double fellatio, yaoi"
                    " | frottage, yaoi | spitroast, yaoi | licking nipple, yaoi | anilingus, yaoi | deepthroat, yaoi"
                    " | anal, from behind, yaoi | mutual masturbation, yaoi")},
    "futa": {"bed": L("futanari masturbation, on {bed}"), "chair": L("futanari masturbation, on {chair}"),
             "water": L("futanari masturbation, in {water}"),
             "*": L("futanari masturbation | penis grab, fingering | erection, looking at viewer | autofellatio | precum, erection"
                    " | futanari, stroking | futanari, ejaculation | futanari, spread legs, erection | futanari, grabbing own breast"
                    " | futanari, kneeling, erection | futanari, cum | futanari, standing, erection | futanari, lying, masturbation")},
    "futa_girl": {"soft": L("futa with female, missionary | futa with female, cowgirl position | futa with female, doggystyle | 69"
                            " | futa with female, mating press"),
                  "wall": L("futa with female, standing sex, against {wall}"), "table": L("futa with female, on {table}"),
                  "water": L("futa with female, in {water}"),
                  "*": L("fellatio, futanari | cunnilingus, erection | futa with female, kiss | handjob, futanari"
                         " | futa with female, sex from behind | futa with female, standing sex | breast sucking, futanari"
                         " | futa with female, girl on top | futa with female, prone bone | paizuri, futanari | 69, futanari"
                         " | futa with female, spooning | fingering, erection | kiss, penis grab")},
    "futa_boy": {"soft": L("futa with male, anal | futa with male, cowgirl position | futa with male, missionary"),
                 "wall": L("futa with male, against {wall}"), "table": L("futa with male, bent over {table}"),
                 "water": L("futa with male, in {water}"), "*": L("mutual masturbation | fellatio | futa with male, frottage"
                                                                  " | futa with male, anal, from behind | futa with male, girl on top | handjob, futanari"
                                                                  " | futa with male, kiss | 69, futanari | futa with male, standing sex"
                                                                  " | futa with male, spooning | deepthroat, futanari | paizuri, futanari")},
    "human_furry": {"soft": L("missionary, on {soft} | cowgirl position | doggystyle | mating press | 69 | breast sucking | prone bone"),
                    "wall": L("standing sex, against {wall} | suspended congress, against {wall}"), "table": L("sex, on {table}"),
                    "water": L("sex, in {water}"),
                    "*": L("fellatio | cunnilingus | handjob | fingering | kiss, interspecies | sex from behind")},
    "furry": {"soft": L("on back, spread legs, on {soft} | presenting, on {soft}"),
              "*": L("masturbation | spread legs, looking at viewer | presenting | raised tail, presenting | masturbation, lying on back"
                     " | masturbation, sitting | masturbation, kneeling | touching self | spread legs, sitting | on all fours, presenting"
                     " | looking back, raised tail | lying on side, masturbation | hand between legs | arched back, masturbation")},
    "nonhuman": {"soft": L("on back, on {soft}, masturbation"), "*": L("masturbation | spread legs, looking at viewer | presenting"
                                                                    " | masturbation, lying on back | masturbation, sitting | masturbation, kneeling"
                                                                    " | touching self | spread legs, sitting | on all fours, presenting"
                                                                    " | looking back, presenting | lying on side, masturbation | hand between legs"
                                                                    " | arched back, masturbation | standing, touching self")},
}
MOODS = {"suggestive": ["sultry", "playful", "shy"], "nude": ["calm", "shy", "sultry"], "explicit": ["passion"]}
GESTURES = {
    "suggestive": {"solo": L("finger to mouth | hand on hip | hair over shoulder | hand on own thigh | hand in own hair | finger on lips"
                             " | hand on own collarbone | thumb in waistband | head tilt | hands behind back | twirling hair"
                             " | tugging collar | biting finger | hand on own neck"),
                   "pair": L("hands in hair | arms around neck | hand on another's waist | hand on another's thigh | hand on another's chest"
                             " | fingers interlaced | hand on another's jaw | hand on another's hip | gripping shirt | hand on another's back"
                             " | hand on another's neck | hands on another's shoulders | finger on another's lips | tugging another's collar"
                             " | arm around waist | hand on another's cheek"),
                   "groups": L("arms around shoulders | hands on another's body | hand on another's waist | leaning on another"
                               " | hands in another's hair | hand on another's thigh | fingers interlaced | hand on another's chest"
                               " | arm around waist | hand on another's hip | hand on own hip | finger to mouth | head tilt"
                               " | hair over shoulder | hand on another's back")},
    "nude": {"people": L("head tilt | hair over shoulder | relaxed | hand on own chest | covering mouth | hand on own hip"
                         " | hands behind head | arm across chest | hand in own hair | hand on own thigh | arms at sides"
                         " | covering crotch | hand on own stomach | fingers on collarbone")},
    "explicit": {"people": L("arched back | curled toes | sweat | clenched hands | grabbing sheets | trembling | ahegao"
                             " | hand on another's head | gripping hips | legs wrapped around | spread legs | hands pinned"
                             " | holding legs | toes spread | back arch, head back | hand grabbing hair | fingers digging in")},
}
LEVEL_CAMERA = {"suggestive": L("cowboy shot | full body | from side | from behind | pov | upper body | thigh focus | ass focus"
                                " | from below | dutch angle | close-up | knees up"),
                "nude": L("full body | cowboy shot | from side | from behind | from above | upper body | from below | close-up"
                          " | knees up | lower body | wide shot | back view"),
                "explicit": L("full body, from side | from above | full body | pov | from below | close-up | cowboy shot"
                              " | upper body | from behind | lower body | between legs | pov, from above | dutch angle")}
LEVEL_DETAILS = {"suggestive": L("clothes on floor | dropped clothes | wine glasses | candles | lipstick mark | rose petals"),
                 "nude": L("folded clothes | clothes on floor | towel | rose petals | candles | robe on floor"),
                 "explicit": L("discarded clothes | sweat | condom wrapper | tissue box | clothes on floor | messy sheets"
                               " | lube bottle | steam | wet spot | torn panties")}

CASTS = ("1girl", "1boy", "1girl1boy", "2girls", "2boys", "girls", "boys", "harem", "reverse", "mixed", "furry", "kemono",
         "mythic", "monster", "synth", "futa", "futa_girl", "futa_boy", "human_furry")
SEX_KEY = {"kemono": "furry", "mythic": "nonhuman", "monster": "nonhuman", "synth": "nonhuman"}  # whose acts they share
FUTA = ("futa", "futa_girl", "futa_boy")
CLASS = {"1girl": "solo", "1boy": "solo", "furry": "solo", "kemono": "solo", "mythic": "solo", "monster": "solo", "synth": "solo", "futa": "solo",
         "1girl1boy": "pair", "2girls": "pair", "2boys": "pair", "futa_girl": "pair", "futa_boy": "pair", "human_furry": "pair",
         "girls": "groups", "boys": "groups", "harem": "groups", "reverse": "groups", "mixed": "groups"}


def _fill(items, names):
    out = []
    for t in items:
        try:
            out.append(t.format(**names))
        except KeyError:
            pass
    return out


def _surf_names(spec):
    """'bed:bed|wall:brick wall' -> {'bed': 'bed', 'wall': 'brick wall'}"""
    out = {}
    for e in L(spec):
        k, _, v = e.partition(":")
        out[k.strip()] = v.strip() or k.strip()
    if "soft" not in out and ("bed" in out or "floor" in out):
        out["soft"] = out.get("bed") or out["floor"]
    return out


def _by_surface(lib, names):
    """The entries of one library row that need a surface the zone has."""
    out = []
    for kind in SURF:
        if kind in names:
            out += lib.get(kind, [])
    if "soft" in names:
        out += lib.get("soft", [])
    return list(dict.fromkeys(_fill(out, names)))


def _join(*bits):
    return ", ".join(b for b in bits if b)


HUMANS = ("1girl", "1boy", "1girl1boy", "2girls", "2boys", "girls", "boys", "harem", "reverse", "mixed", "futa", "futa_girl", "futa_boy")


def _subjects(level, theme_name, rng, beings=None, n=18):
    """Who is there, never what they wear: the cast tags say it for humans; anthros and beings by kind."""
    out = {c: [""] for c in HUMANS}
    out["furry"] = [_join(f"anthro {sex}", kind, feat) for kind, sex, feat in rng.sample(ANTHRO_BODIES, n)]
    out["kemono"] = [_join(f"anthro {sex}", kind, feat) for kind, sex, feat in rng.sample(ANTHRO_BODIES, n)]
    mixed = []
    for kind, sex, feat in rng.sample(ANTHRO_BODIES, n):
        human = "1girl" if sex == "male" else "1boy"
        mixed.append(_join(human, f"anthro {sex}", kind, feat))
    out["human_furry"] = mixed
    for kind, pool in BEINGS.items():
        own = (beings or {}).get(kind)
        out[kind] = L(own) if own else rng.sample(pool, min(n, len(pool)))
    if level == "sfw":
        out["none"] = []
        own = (beings or {}).get("animal")
        out["animal"] = L(own) if own else ANIMALS[ANIMALS_BY_THEME.get(theme_name, "*")]
        for c in FUTA:
            out.pop(c)
    return out


# ------------------------------------------------------------------ space, hour and sky
SKIES = []  # (file, place, zone, exposure): for review
OUT_WORDS = (r"street|field|meadow|beach|forest|woods|park|garden|rooftop|roof|terrace|balcony|lake|mountain|desert|dunes?|alley|"
             r"crosswalk|crossing|market|dock|pier|jetty|cliff|shore|trail|path|courtyard|plaza|square|bridge|ruins|graveyard|cemetery|"
             r"canyon|oasis|slope|track|skate|camp|deck|vineyard|highway|road|parking|gas station|landing pad|island|sky|waterfall|"
             r"stream|creek|river|jungle|cove|tide pools|stone circle|hill|summit|ridge|helipad|patio|lawn|porch|festival|bonfire|"
             r"campfire|torii|outdoor|outside|pool|lagoon|spring|grove|glade|clearing|harbor|coast|sea|ocean|waves|surf|fountain|"
             r"overpass|bus stop|bus bay|platform|exterior|yard|orchard|farm|pasture|valley|nest|aerie|peak|shoreline|dunes|tents?\b")
VIEW_WORDS = r"window|viewport|skylight|glass wall|glass roof|greenhouse|conservatory|observation|porthole|cupola|penthouse|bay window|veranda|engawa"
NONE_WORDS = r"underwater|kelp|abyss|submarine|space station|station module|airlock|starship|sunken|atlantis|coral|deep sea|mecha cockpit"


def auto_sky(theme_name, p, z):
    """out (outdoors), view (a room with a window on the sky), in (a closed room), none (space, under the sea)."""
    text = " ".join([p.title, z.title] + z.where).lower()
    if re.search(NONE_WORDS, text):
        return "none"
    if re.search(VIEW_WORDS, text):
        return "view"
    if re.search(OUT_WORDS, text) and not re.search(r"interior|indoor|room\b|hall\b|lobby|kitchen|cellar|booth|cabin|tent interior", text):
        return "out"
    return "in"


def _spaced(where, exp):
    """Settings with what kind of space they are: outdoors, indoors, a window on the sky."""
    tag = {"out": "outdoors", "view": "indoors", "in": "indoors"}.get(exp)
    out = []
    for w in where:
        low = w.lower()
        pre = []
        if tag and tag not in low:
            pre.append(tag)
        if exp == "view" and not re.search(r"window|viewport|skylight|glass|porthole|veranda|engawa|balcony", low):
            pre.append("window")
        out.append(", ".join(pre + [w]))
    return out


def _times(p, z, exp, weather):
    """Every hour and sky the zone's own words allow: no 'night' where its only light is golden hour."""
    if exp not in ("out", "view"):
        return []
    lights = (z.light or []) + p.light
    title = f"{p.title} {z.title}"
    texts = " ".join(z.where + z.detail + p.detail + lights).lower()
    if re.search(r"\bsnow|blizzard|frozen|winter|icicle", texts) and "snow" not in weather:
        weather += " snow"  # a place with snow on the ground can have it falling
    out = []
    for t in (p.times.split() if isinstance(p.times, str) else W.TIMES):
        for w in weather.split():
            if not W.fits(title, t, w) or not any(W.fits(x, t, w) for x in z.where) or not any(W.fits(x, t, w) for x in lights):
                continue
            out.append(W.tag(t, w))
    return out


# ------------------------------------------------------------------ authoring


class Z:
    def __init__(self, title, where, detail, solo=None, pair=None, groups=None, surf=None, light=None, none=None, sky=None, weather=None):
        self.sky, self.weather = sky, weather
        self.title, self.where, self.detail = title, L(where), L(detail)
        self.acts = {"solo": L(solo), "pair": L(pair), "groups": L(groups)}
        self.surf, self.light, self.none = surf, L(light), L(none)


class P:
    def __init__(self, title, f, m, light, mood, surf, zones, acts=None, tease_f=None, tease_m=None, gestures=None,
                 camera=None, nsfw=None, levels=LEVELS, detail=None, none=None, sky=None, weather=None, times=None, beings=None):
        self.beings = beings
        self.sky, self.weather, self.times = sky, weather, times
        self.detail, self.none = L(detail), L(none)
        self.title, self.f, self.m, self.light = title, L(f), L(m), L(light)
        self.mood = mood.split() if isinstance(mood, str) else mood
        self.surf, self.zones = surf, zones
        self.acts = {k: L(v) for k, v in (acts or {}).items()}
        self.tease_f, self.tease_m = L(tease_f), L(tease_m)
        self.gestures, self.camera = gestures, L(camera)
        self.nsfw = {lvl: {k: L(v) for k, v in d.items()} for lvl, d in (nsfw or {}).items()}  # own acts by level and class or cast
        self.levels = levels


def theme(stem, name, places, styles, nsfw_styles, camera, nonhuman="default", weather="clear cloudy overcast rain fog", sky=None):
    """One file: templates by level (shared by every place), by place and level, then one scene per zone and level."""
    assert len(places) >= 1
    rng = random.Random(stem)
    templates, scenes = {}, []
    for level in LEVELS:
        if not any(level in p.levels for p in places):
            continue
        t = {"rating": level}
        if level == "sfw":
            t["camera"] = {"people": L(camera), "*": L("wide shot, scenery | wide shot | establishing shot")}
            t["gestures"] = SFW_GESTURES
            t["actions"] = SFW_ANY
        else:
            t["mood"] = MOODS[level]
            t["camera"] = {"people": LEVEL_CAMERA[level], "*": L("wide shot")}
            t["gestures"] = GESTURES[level]
            t["details"] = LEVEL_DETAILS[level]
            t["styles"] = L(nsfw_styles)
            if level in ("suggestive", "nude"):
                lib = TEASE if level == "suggestive" else NUDE
                t["actions"] = {cls: lib[cls]["*"] for cls in ("solo", "pair", "groups")}
                if level == "suggestive":
                    t["actions"].update({c: F_TEASE_ACTS for c in ("1girl", "futa")})
            else:
                t["actions"] = {cast: SEX[SEX_KEY.get(cast, cast)]["*"] for cast in CASTS}
        templates[level] = t
    for pi, p in enumerate(places):
        for level in p.levels:
            pid = f"p{pi}:{level}"
            t = {}
            if level == "sfw":
                f, m = p.f, p.m
            else:
                own = "sfw" not in p.levels  # an NSFW place: its own wear is what it is about
                f = p.tease_f or (p.f if own else rng.sample(F_TEASE, 5))
                m = p.tease_m or (p.m if own else rng.sample(M_TEASE, 4))
            t["wear"] = {"f": f, "m": m}
            if f"p{pi}" not in templates:  # who can be there: the same at every level (Muse keeps SFW and NSFW casts apart)
                templates[f"p{pi}"] = {"subjects": _subjects("sfw" if "sfw" in p.levels else level, name, rng, p.beings)}
                if "sfw" in p.levels:
                    templates[f"p{pi}"]["subjects"].update({c: [""] for c in FUTA})
            t["lighting"] = p.light
            if p.detail:
                t["details"] = p.detail
            if level == "sfw":
                t["mood"] = p.mood
                if p.acts or p.none:
                    t["actions"] = {k: v for k, v in p.acts.items() if v}
                    if p.none:
                        t["actions"]["none"] = p.none
                if p.gestures:
                    t["gestures"] = {"people": L(p.gestures)}
                if p.camera:
                    t["camera"] = {"people": p.camera}
            elif p.nsfw.get(level):
                t["actions"] = p.nsfw[level]
            templates[pid] = t
            for zi, z in enumerate(p.zones):
                names = _surf_names(z.surf if z.surf is not None else p.surf)
                zid = f"p{pi}z{zi}"
                if zid not in templates:  # where, what is there and the sky: the same at every level
                    exp = z.sky or p.sky or SKY.get((stem, p.title, z.title)) or sky or auto_sky(name, p, z)
                    SKIES.append((stem, p.title, z.title, exp))
                    zt = {"settings": _spaced(z.where, exp), "details": z.detail}
                    times = _times(p, z, exp, z.weather or p.weather or CLIMATE.get((stem, p.title)) or weather)
                    if times:
                        zt["times"] = times
                    elif exp in ("out", "view"):
                        print("  no sky fits:", name, p.title, z.title)
                    if z.light:
                        zt["lighting"] = z.light
                    templates[zid] = zt
                s = {"use": [level, f"p{pi}", pid, zid], "title": f"{p.title} · {z.title}"}
                if level == "sfw":
                    acts = {k: list(dict.fromkeys(v + _by_surface(SFW_SURF[k], names))) for k, v in z.acts.items() if v}
                    if z.none:
                        acts["none"] = z.none
                else:
                    lib = {"suggestive": TEASE, "nude": NUDE}.get(level)
                    if lib:
                        acts = {cls: _by_surface(lib[cls], names) for cls in ("solo", "pair", "groups")}
                    else:
                        acts = {cast: _by_surface(SEX[SEX_KEY.get(cast, cast)], names) for cast in CASTS}
                    acts = {k: v for k, v in acts.items() if v}
                if acts:
                    s["actions"] = acts
                scenes.append(s)
    data = {"theme": name, "styles": L(styles), "templates": templates, "scenes": scenes}
    path = os.path.join(OUT, stem + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("{\n")
        for k in ("theme", "styles"):
            fh.write(f' {json.dumps(k)}: {json.dumps(data[k], ensure_ascii=False)},\n')
        fh.write(' "templates": {\n')
        fh.write(",\n".join(f'  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)}' for k, v in templates.items()))
        fh.write('\n },\n "scenes": [\n')
        fh.write(",\n".join(f'  {json.dumps(s, ensure_ascii=False)}' for s in scenes))
        fh.write("\n ]\n}\n")
    return len(scenes)
