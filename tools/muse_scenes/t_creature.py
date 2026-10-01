from lib import P, Z, theme

NSFW = "photorealistic, detailed skin | hentai, anime coloring | dark fantasy, oil painting | painterly, erotic illustration"

# who lives where: the beings of each place (mythic, monster, synth) and its real animals (SFW)
VAMP = dict(mythic="1girl, solo, vampire, pale skin, red eyes, fangs | 1boy, solo, vampire, pale skin, fangs | 1girl, solo, vampire queen, bat wings"
                   " | 1boy, solo, vampire lord, cape, fangs | 1girl, solo, dhampir, red eyes",
            monster="1girl, solo, bat girl, bat wings, fangs | 1boy, solo, ghoul, claws | 1girl, solo, ghost, translucent",
            animal="bat, flying | black cat, glowing eyes | raven, perched | wolf, howling | owl, moonlight")
WOLF = dict(monster="1boy, solo, werewolf, monster, wolf head, claws, fur | 1girl, solo, werewolf, monster girl, claws, fur"
                    " | 1boy, solo, werewolf, mid-transformation, torn clothes | 1girl, solo, werewolf girl, glowing eyes, fur",
            mythic="1girl, solo, wolf girl, wolf ears, wolf tail | 1boy, solo, wolf boy, wolf ears, wolf tail",
            animal="wolf, howling | wolf pack | grey wolf, snow | deer, startled | raven")
FRANK = dict(monster="1boy, solo, frankenstein's monster, stitches, bolts in neck | 1girl, solo, bride of frankenstein, stitches, streaked hair"
                     " | 1girl, solo, flesh golem, stitches | 1boy, solo, zombie, grey skin | 1girl, solo, zombie girl, stitches, grey skin",
             synth="1girl, solo, cyborg, mechanical arm | 1boy, solo, cyborg, exposed wiring",
             animal="rat | crow, perched | black cat | spider, web")
DEMON = dict(mythic="1girl, solo, succubus, demon horns, bat wings, demon tail | 1boy, solo, incubus, demon horns, demon tail"
                    " | 1girl, solo, demon girl, horns, red skin | 1boy, solo, demon lord, large horns, red skin | 1girl, solo, imp, small horns, demon tail"
                    " | 1boy, solo, fallen angel, black wings | 1girl, solo, fallen angel, black wings, broken halo",
             monster="1boy, solo, hellhound, flaming fur | 1girl, solo, lich, glowing eyes, crown",
             animal="black snake | crow | vulture")
ANGEL = dict(mythic="1girl, solo, angel, feathered wings, halo | 1boy, solo, angel, feathered wings, halo | 1girl, solo, seraph, six wings, halo"
                    " | 1boy, solo, archangel, armor, wings | 1girl, solo, valkyrie, winged helmet | 1boy, solo, fallen angel, black wings",
             animal="white dove, flying | swan | white horse | white peacock")
DRAGON = dict(mythic="1girl, solo, dragon girl, dragon horns, dragon tail | 1boy, solo, dragon boy, dragon horns, scales"
                     " | 1girl, solo, dragonkin, scales, wings | 1boy, solo, dragonborn, scales, horns | 1girl, solo, wyvern girl, wings",
              animal="komodo dragon | eagle, flying | snake, coiled | lizard, sunning")
ELF = dict(mythic="1girl, solo, elf, pointy ears | 1boy, solo, elf, pointy ears | 1girl, solo, dark elf, pointy ears, dark skin"
                  " | 1boy, solo, high elf, long hair, circlet | 1girl, solo, dryad, bark skin, leaves in hair | 1boy, solo, satyr, goat horns, goat legs"
                  " | 1girl, solo, wood nymph, flower crown",
           animal="deer, antlers | white stag | owl, perched | fox | butterflies | rabbit")
ORC = dict(mythic="1boy, solo, orc, green skin, tusks, muscular | 1girl, solo, orc, green skin, tusks | 1boy, solo, half-orc, scars"
                  " | 1girl, solo, half-orc, tusks, braids | 1boy, solo, ogre, huge | 1boy, solo, minotaur, bull horns | 1girl, solo, troll, blue skin",
           animal="warg | boar | horse, armored | wolf")
PIXIE = dict(mythic="1girl, solo, pixie, fairy wings, pointy ears | 1boy, solo, fairy, insect wings | 1girl, solo, fairy, butterfly wings"
                    " | 1girl, solo, flower fairy, petal dress | 1boy, solo, sprite, glowing | 1girl, solo, alraune, plant girl, flower",
             animal="butterfly | hummingbird | bee | ladybug | frog, lily pad | dragonfly")
ROBOT = dict(synth="1girl, solo, android, mechanical joints | 1boy, solo, android, mechanical joints | 1girl, solo, gynoid, porcelain skin"
                   " | 1boy, solo, humanoid robot, metal body | 1girl, solo, robot girl, glowing eyes | 1girl, solo, mecha musume, mechanical parts"
                   " | 1boy, solo, mecha, giant robot | 1girl, solo, cyborg, mechanical arm | 1boy, solo, mechanoid, exposed wiring",
             animal="robot dog | mechanical bird | cat, on conveyor")
ALIEN = dict(synth="1girl, solo, alien, blue skin, antennae | 1boy, solo, alien, grey skin, large eyes | 1girl, solo, alien girl, green skin"
                   " | 1boy, solo, insectoid alien, carapace | 1girl, solo, alien, bioluminescent skin | 1girl, solo, hologram, translucent, glitch",
             monster="1girl, solo, slime girl, translucent body | 1boy, solo, tentacle monster",
             animal="jellyfish | octopus | deep sea fish | glowing insects")
WILD = dict(animal="tiger, prowling | lion, mane | elephant | gorilla | cheetah, running | polar bear | wolf pack | giraffe | rhinoceros"
                   " | zebra herd | hippopotamus | panther | crocodile | flamingo | bald eagle",
            mythic="1girl, solo, kemonomimi, cat ears, tail | 1boy, solo, beastman, wolf ears",
            monster="1girl, solo, lamia, snake tail | 1girl, solo, arachne, spider legs")

theme("creature", "Creature", [
    P("Vampire castle", f="gothic dress, lace | victorian gown | black corset dress | velvet cloak", m="frock coat, cravat | cape, high collar | victorian suit | velvet coat",
      light="candlelight | moonlight, window | red candlelight | torchlight", mood="tense cool", surf="bed:coffin bed|wall:stone wall|chair:throne|table:banquet table",
      detail="candelabras | bats | blood goblet | stained glass | cobwebs | red roses", beings=VAMP, none="bats, flying | coffin, candles | castle, full moon",
      acts=dict(solo="drinking from goblet | sitting on throne | looking out window", pair="neck biting | waltz, ballroom | toast, goblets", groups="vampire court | feast"),
      zones=[
          Z("Throne hall", "vampire castle, throne | gothic hall, red carpet | throne room, candles", "throne | red carpet | portraits", solo="lounging, throne | crossed legs, throne",
            pair="kneeling, throne | standing beside throne", groups="court, throne", sky="view"),
          Z("Crypt", "crypt, coffins | vampire crypt | catacombs, candles", "coffins | skulls | candles", solo="rising from coffin | lying in coffin", pair="coffin, together",
            groups="coven, crypt", sky="in"),
          Z("Balcony", "castle balcony, full moon | gothic balcony | balcony, cliffs", "full moon | bats | fog", solo="leaning, balustrade | cape, wind", pair="balcony, embrace",
            groups="balcony, gathering", sky="out"),
      ]),
    P("Werewolf forest", f="hooded cloak | torn dress | hunter outfit | flannel, jeans", m="torn shirt | hunter coat | flannel shirt | cloak",
      light="moonlight | fog light | lantern light | blue hour", mood="tense", surf="floor:forest floor|wall:tree trunk",
      detail="full moon | claw marks | fog | broken branches | howling | paw prints", beings=WOLF, times="evening night", none="full moon, forest | claw marks, tree | wolf, howling",
      acts=dict(solo="howling | running, forest | crouching, claws", pair="chased | hiding, tree | standoff", groups="pack | hunt"),
      zones=[
          Z("Clearing", "moonlit clearing | forest clearing, full moon | glade, moonlight", "full moon | grass | fog", solo="howling, moon | transforming", pair="circling, clearing", groups="pack, clearing"),
          Z("Dark woods", "dark forest | twisted trees, fog | woods, night", "twisted trees | roots | eyes in dark", solo="prowling | sniffing air", pair="chase, woods", groups="hunt, woods"),
          Z("Cabin", "forest cabin, night | hunter cabin | cabin, porch", "lantern | axe | claw marks", solo="porch, lantern | barricading door", pair="cabin, together",
            groups="hunters, cabin", sky="view"),
      ]),
    P("Frankenstein lab", f="lab coat, victorian | corset, apron | gothic dress | surgical gown", m="lab coat, victorian | leather apron | waistcoat | surgical gown",
      light="lightning flash | electric arcs | lamp light | green glow", mood="tense serious", surf="table:operating slab|wall:stone wall|floor:stone floor",
      detail="tesla coils | lightning | bubbling flasks | stitches | levers | body parts jars", beings=FRANK, none="operating slab, lightning | tesla coil, sparks",
      acts=dict(solo="pulling lever | waking, slab | examining stitches", pair="bringing to life | holding hands, stitches | experiment", groups="angry mob | lab assistants"),
      zones=[
          Z("Operating slab", "laboratory, operating slab | gothic lab, slab | mad scientist lab", "slab | straps | sparks", solo="sitting up, slab | lying, slab", pair="operating",
            groups="experiment, crowd", sky="in"),
          Z("Tower top", "tower lab, open roof | storm, tower | lab tower, lightning rod", "lightning rod | storm | chains", solo="arms raised, lightning", pair="lightning, together",
            groups="tower, crowd", sky="out"),
          Z("Village edge", "village, torches | castle gate, mob | windmill, night", "torches | pitchforks | windmill", solo="fleeing | standing, gate", pair="fleeing together",
            groups="angry mob", sky="out"),
      ]),
    P("Demon realm", f="demon outfit, revealing | black leather | dark robe | chains, lingerie", m="demon armor | black leather | dark robe | open shirt, chains",
      light="hellfire | red glow | lava light | purple light", mood="tense cool", surf="floor:obsidian floor|chair:bone throne|bed:velvet bed|wall:obsidian wall",
      detail="hellfire | lava rivers | chains | skulls | brimstone | summoning circle", beings=DEMON, none="lava rivers | hellfire, ruins | demon statue",
      acts=dict(solo="summoning fire | sitting on throne | spreading wings", pair="contract, handshake | dancing, flames | kneeling", groups="demon court | ritual"),
      zones=[
          Z("Throne", "demon throne room | bone throne | hell palace", "bone throne | chains | fire", solo="lounging, throne", pair="kneeling, throne", groups="court", sky="in"),
          Z("Lava bridge", "lava bridge | hell, lava rivers | volcanic chasm", "lava | heat haze | embers", solo="walking, lava bridge", pair="crossing, lava", groups="march, lava", sky="none"),
          Z("Summoning room", "summoning circle | ritual chamber | pentagram floor", "pentagram | candles | smoke", solo="emerging, circle", pair="summoned, kneeling", groups="cultists", sky="in"),
      ]),
    P("Celestial sanctuary", f="white robe, gold trim | flowing white dress | angel armor | sheer white gown", m="white robe, gold trim | angel armor | white tunic | silk robe",
      light="divine light | golden glow | sunbeam | soft white light", mood="calm", surf="floor:clouds|wall:marble column|chair:marble bench|water:pool",
      detail="clouds | golden gates | feathers | harps | halos | marble columns", beings=ANGEL, none="golden gates, clouds | feathers, falling | marble temple, clouds",
      acts=dict(solo="praying, light | spreading wings | playing harp", pair="wings embrace | blessing | flying together", groups="choir | angels, circle"),
      zones=[
          Z("Gates", "golden gates, clouds | heavenly gates | gates, light", "gates | clouds | light", solo="standing, gates", pair="welcoming", groups="host, gates", sky="none"),
          Z("Cloud garden", "garden, clouds | heavenly garden | flowers, clouds", "white flowers | fountain | doves", solo="sitting, fountain", pair="garden, together", groups="garden", sky="none"),
          Z("Temple", "marble temple, sky | celestial temple | sky temple", "columns | sky | statues", solo="kneeling, altar", pair="temple, together", groups="choir, temple", sky="none"),
      ]),
    P("Dragon roost", f="dragon rider armor | adventurer outfit | scale armor | cloak", m="dragon rider armor | adventurer outfit | scale armor | cloak",
      light="sunset | storm light | golden hour | fire glow", mood="calm serious", surf="floor:rock|wall:cliff|bed:gold hoard",
      detail="giant dragon | nest | scales | dragon eggs | gold coins | smoke", beings=DRAGON, none="dragon, sleeping | dragon, flying | dragon eggs, nest",
      acts=dict(solo="touching dragon | riding dragon | breathing fire", pair="riding dragon together | feeding dragon | spreading wings, together", groups="dragon riders"),
      zones=[
          Z("Nest", "dragon nest, cliff | nest, eggs | aerie, dragons", "eggs | hatchling | straw", solo="holding egg | sitting, nest", pair="hatching, together", groups="nest, gathering", sky="out"),
          Z("Hoard", "dragon hoard | gold, cave | treasure, dragon cave", "gold | gems | crowns", solo="lying on gold | counting gems", pair="hoard, together", groups="hoard, raid", sky="in"),
          Z("Sky", "dragon flight, sky | above clouds | mountains, dragon", "clouds | wind | sun", solo="flying, wings | riding, sky", pair="flying together", groups="formation", sky="out"),
      ]),
    P("Elven grove", f="elven dress | ranger outfit | circlet, gown | leaf armor", m="elven armor | ranger cloak | robe, circlet | leaf armor",
      light="dappled light | god rays | glowing flowers | moonlight", mood="calm", surf="floor:moss|water:spring|wall:ancient tree",
      detail="giant trees | glowing flowers | elven lanterns | waterfalls | fireflies | silver leaves", beings=ELF, none="ancient tree, glowing | elven city, trees",
      acts=dict(solo="archery | singing, forest | reading scroll", pair="dancing, forest | archery lesson | walking, bridge", groups="council | festival"),
      zones=[
          Z("Tree city", "elven city, giant trees | treetop bridges | tree palace", "bridges | lanterns | leaves", solo="walking, bridge", pair="bridge, together", groups="festival", sky="out"),
          Z("Moon spring", "moonlit spring | sacred spring, elves | pool, glowing", "glowing water | stones | flowers", solo="bathing, spring", pair="spring, together", groups="ritual, spring", sky="out"),
          Z("Archery glade", "archery glade | forest range | elven training ground", "targets | bows | arrows", solo="aiming bow", pair="lesson", groups="archers", sky="out"),
      ]),
    P("Orc war camp", f="leather armor, furs | tribal outfit | warrior armor | bone jewelry", m="leather armor, furs | tribal outfit | spiked armor | loincloth, warpaint",
      light="bonfire | torchlight | sunset | smoke, red light", mood="tense playful", surf="floor:dirt|bed:fur pile|wall:palisade",
      detail="war drums | bonfire | banners | tusks | spears | war paint", beings=ORC, none="war camp, bonfire | banners, smoke",
      acts=dict(solo="sharpening axe | roaring | arm flex", pair="arm wrestling | sparring | feast, meat", groups="war chant | feast"),
      zones=[
          Z("Bonfire", "war camp, bonfire | orc camp, fire | camp, drums", "bonfire | drums | meat", solo="dancing, fire", pair="toast, fire", groups="war chant", sky="out"),
          Z("Chieftain tent", "chieftain tent | war tent, furs | tent, banners", "furs | maps | trophies", solo="sitting, furs", pair="tent, together", groups="war council", sky="in"),
          Z("Arena", "fighting pit | arena, camp | sand pit", "sand | crowd | weapons", solo="victory, arena", pair="fight, arena", groups="crowd, arena", sky="out"),
      ]),
    P("Pixie garden", f="petal dress | leaf dress | flower crown, gown | sheer wings dress", m="leaf tunic | petal cloak | vine armor | flower crown, tunic",
      light="sunbeam | dappled light | fireflies | golden hour", mood="playful happy", surf="floor:moss|water:pond|chair:mushroom",
      detail="giant flowers | mushrooms | dew drops | fireflies | butterflies | glowing pollen", beings=PIXIE, none="giant flowers, dew | fairy ring, mushrooms",
      acts=dict(solo="sitting on mushroom | flying, sparkles | sleeping, flower", pair="dancing, sparkles | flying together | sharing dew drop", groups="fairy ring dance"),
      zones=[
          Z("Flower bed", "giant flowers | flower garden, oversized | garden, petals", "petals | pollen | bees", solo="sitting, flower", pair="flowers, together", groups="flower dance", sky="out"),
          Z("Mushroom ring", "fairy ring | mushroom circle | glade, mushrooms", "mushrooms | glow | dew", solo="dancing, ring", pair="ring, together", groups="fairy ring", sky="out"),
          Z("Lily pond", "lily pond | pond, lotus | garden pond", "lily pads | frogs | dragonflies", solo="sitting, lily pad", pair="pond, together", groups="pond, gathering", sky="out"),
      ]),
    P("Robot factory", f="technician uniform | bodysuit | lab coat | jumpsuit", m="technician uniform | bodysuit | lab coat | jumpsuit",
      light="cold white light | blue light | sparks | warning lights", mood="serious tense", surf="table:assembly table|wall:robot arms|floor:metal floor|bed:charging pod",
      detail="robot arms | sparks | assembly line | spare parts | cables | holographic display", beings=ROBOT, none="assembly line, robot arms | giant robot, hangar",
      acts=dict(solo="booting up | charging | repairing arm", pair="repairing another | first touch | scanning", groups="assembly line | robot army"),
      zones=[
          Z("Assembly line", "robot assembly line | factory, robots | conveyor, androids", "conveyor | robot arms | sparks", solo="assembly, robot arms", pair="assembling", groups="robot army", sky="in"),
          Z("Charging bay", "charging pods | android storage | pods, cables", "pods | cables | lights", solo="charging, pod", pair="pods, together", groups="pods, row", sky="in"),
          Z("Mecha hangar", "mecha hangar | giant robot, hangar | robot bay", "giant robot | cranes | ladders", solo="standing, mecha", pair="hangar, together", groups="crew, hangar", sky="in"),
      ]),
    P("Alien world", f="space suit | explorer suit | alien outfit | bodysuit", m="space suit | explorer suit | alien outfit | bodysuit",
      light="bioluminescence | twin suns | purple light | alien glow", mood="tense calm", surf="floor:alien ground|water:glowing pool",
      detail="alien plants | two moons | crystals | strange sky | spores | ringed planet", beings=ALIEN, none="alien landscape | glowing flora | ringed planet, sky",
      acts=dict(solo="scanning plant | first contact | touching crystal", pair="first contact, hands | exploring together | translator, talking", groups="expedition | alien council"),
      zones=[
          Z("Glowing jungle", "bioluminescent jungle | alien forest | glowing flora", "glow | spores | vines", solo="touching glow", pair="walking, glow", groups="expedition", sky="out"),
          Z("Crystal field", "crystal field | alien desert, crystals | crystal spires", "crystals | moons | sand", solo="collecting crystal shard | looking at moons", pair="crystals, together", groups="survey", sky="out"),
          Z("Alien city", "alien city | alien architecture | floating city, alien", "spires | ships | lights", solo="walking, alien city", pair="city, together", groups="crowd, aliens", sky="out"),
      ]),
    P("Wildlife reserve", f="safari outfit | ranger uniform | khaki shirt, shorts | explorer outfit", m="safari outfit | ranger uniform | khaki shirt | explorer outfit",
      light="golden hour | harsh sun | sunrise | dusty light", mood="calm happy", surf="floor:grass|chair:jeep seat",
      detail="acacia trees | savanna | binoculars | jeep | dust | watering hole", beings=WILD, weather="clear cloudy rain",
      none="lion, savanna | elephant herd | giraffes, sunset",
      acts=dict(solo="looking through binoculars | photographing animals | standing, jeep", pair="safari, jeep | watching animals together | feeding animal",
                groups="safari tour | rangers"),
      zones=[
          Z("Savanna", "savanna, acacia | grassland, animals | african plains", "acacia | herds | dust", solo="watching herd", pair="watching, together", groups="tour", sky="out"),
          Z("Watering hole", "watering hole | river, animals | waterhole, savanna", "elephants | zebras | water", solo="crouching, water", pair="hiding, grass", groups="rangers", sky="out"),
          Z("Rescue center", "animal sanctuary | rescue center, enclosure | wildlife clinic", "enclosures | bottles | crates", solo="feeding animal", pair="caring, animal",
            groups="keepers", sky="out"),
      ]),
], "creature design, concept art | fantasy illustration | dark fantasy art | wildlife photography", NSFW, "full body | wide shot | from below | dynamic angle")
