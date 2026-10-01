"""Where the automatic guess of a zone's space is wrong: file|place|zone=kind,zone=kind. And places' climates."""
RAW = """
horror|Haunted mansion|Grand staircase=view,Nursery=view,Ballroom=view
horror|Abandoned hospital|Corridor=view,Ward=view
horror|Cabin in woods|Cabin interior=view,Porch=out,Campfire=out
horror|Witch hut|Cauldron=view,Swamp door=out
horror|Carnival night|Carousel=out,Fortune tent=in
horror|Sunken church|Flooded nave=view,Altar=view,Belfry=out
horror|Slasher camp|Cabins=view
myth|Greek temple|Altar=view
myth|Olympus|Throne hall=view
myth|Underworld|River Styx=none,Throne=none,Asphodel=none
myth|Norse hall|Longship=out,Rune stone=out
myth|Egyptian temple|Hypostyle hall=view,Throne room=view
myth|Japanese shrine|Main hall=out,Sacred tree=out
myth|Fae court|Mushroom ring=out
fantasy|Tavern|Main hall=view,Inn room=view
fantasy|Wizard tower|Study=view,Observatory=view
fantasy|Dwarven forge|Forge=in
fantasy|Royal castle|Throne room=view,Ballroom=view,Royal bedchamber=view
fantasy|Dragon lair|Lava cave=in
creature|Monster sanctuary|Clinic=view
creature|Giant forest|Mushroom grove=out
creature|Alien zoo|Habitat=view,Lab=in
fashion|Atelier|Dress forms=view,Cutting table=view
fashion|Cyclorama lookbook|White cyc=in,Color cyc=in
fashion|Street style|Shop window=out
fashion|Rooftop campaign|Glass railing=out
film|Sci-fi bridge|Viewport=none,Engine room=none
film|Road movie|Convertible=out,Diner=view
film|Musical|Stage=in,Rain street set=in
film|Kung fu film|Tea house=view
film|Gothic horror set|Castle hall=view,Bedchamber=view
film|Western saloon|Poker table=view
film|Noir motel|Bed=view
food|Ramen shop|Counter seats=in
food|Bakery|Counter=view,Work table=view
food|Fine dining|Dining room=view
food|Street food|Food truck=out
food|Home kitchen|Stove=view,Island=view,Dining nook=view
food|Tea house|Tatami room=view
food|Diner|Counter=view
home|Living room|Sofa=view,Fireplace=view,Bookshelf=view
home|Bedroom|Bed=view
home|Bathroom|Bathtub=view
home|Home office|Desk=view,Reading chair=view
home|Kitchen night|Counter=view
sports|Tennis court|Baseline=out,Net=out,Bench=out
sports|Pool|Lanes=view,Diving board=view,Pool deck=view
sports|Ski slope|Lodge=view
sports|Yoga studio|Studio floor=view
bedroom|Morning bed|Sheets=view,Breakfast tray=view
bedroom|Dorm room|Bunk=view,Desk=view,Floor=view
bedroom|Loft|Armchair=view
bedroom|Cabin bedroom|Quilt bed=view,Fur rug=view
bedroom|Hotel suite|King bed=view,Sitting area=view
bedroom|Moroccan room|Daybed=view,Courtyard=out
bedroom|Rainy night bedroom|Rug=view
gym|Yoga loft|Mats=view
gym|Pool gym|Lanes=view,Jacuzzi=view,Deck=view
gym|Dance studio|Mirror wall=view
gym|Home gym|Living room=view
hotel|Hotel room|Bed=view
hotel|Penthouse|Terrace=out
hotel|Ryokan|Futon room=view,Private bath=out
hotel|Overwater villa|Bedroom=view
hotel|Honeymoon suite|Bed=view,Jacuzzi=view
office|Open office|Desks=view,Break room=view
office|Executive office|Desk=view,Bar cart=view
office|Meeting room|Table=view
office|Late night office|Desk=view,Lounge=view
office|Startup loft|Desks=view,Game area=view
office|Reception|Waiting area=view
office|Home office call|Desk=view,Bed=view,Kitchen table=view
outdoors|Campsite|Tent=in
outdoors|Desert oasis|Tent=in
studio|Photo studio|White sweep=in
studio|Art studio|Easel=view,Model stand=view,Sculpture=view
studio|Dance rehearsal|Mirror=view,Center=view,Corner=view
studio|Pottery studio|Wheel=view,Kiln=in,Glazing=view
studio|Boudoir studio|Velvet chair=view
redlight|Window district|Booth=in,Canal street=out
portrait|Studio headshot|Grey backdrop=in
portrait|Old library|Rolling ladder=view
scifi|Android lab|Test room=in
scifi|Desert planet|Wreck=out
scifi|Mecha hangar|Launch bay=in
scifi|Utopian city|Monorail=out
scifi|Retro future diner|Booth=view,Counter=view
party|House party|Living room=view,Kitchen=view
party|Masquerade|Ballroom=view,Salon=view
party|Rooftop party|DJ deck=out
party|Wedding reception|Dance floor=view,Head table=view
bath|Onsen|Private bath=view
bath|Luxury bathroom|Bathtub=view
bath|Spa|Jacuzzi=view
bath|Bathtub at home|Tub=view
street|Subway|Platform=in
street|Back alley|Dumpsters=out
street|Bus terminal|Waiting hall=view,Ticket window=in
street|Laundromat|Machines=view,Folding table=view
nature|Beach|Tide pools=out
architecture|Cathedral|Nave=view,Bell tower=view
architecture|Brutalist complex|Stairwell=view
architecture|Japanese temple|Pagoda=out
architecture|Glass skyscraper|Lobby=view,Elevator=view
architecture|Train station|Grand hall=view,Waiting room=view
architecture|Lighthouse|Lantern room=view,Keeper cottage=view
architecture|Abandoned factory|Machine hall=view,Catwalk=view,Rooftop=out
"""
SKY = {}
for line in RAW.strip().splitlines():
    stem, place, zones = line.split("|")
    for z in zones.split(","):
        k, v = z.split("=")
        SKY[(stem, place, k)] = v

DRY = "clear cloudy"
TROPIC = "clear cloudy rain"
CLIMATE = {  # (file, place): skies it gets
    ("fashion", "Desert shoot"): DRY, ("outdoors", "Desert oasis"): DRY, ("scifi", "Desert planet"): DRY, ("nature", "Desert"): DRY,
    ("myth", "Egyptian temple"): DRY, ("nature", "Beach"): TROPIC, ("outdoors", "Secluded beach"): TROPIC, ("nature", "Jungle"): TROPIC,
    ("hotel", "Overwater villa"): TROPIC, ("party", "Beach party"): TROPIC, ("fashion", "Beach editorial"): TROPIC,
    ("party", "Pool party"): DRY + " rain", ("hotel", "Pool terrace"): TROPIC, ("scifi", "Alien jungle"): TROPIC + " fog",
}
RAW2 = """
travel|Airport|Check-in=view,Arrivals=view
travel|Landmark|Viewpoint=out
travel|Cruise ship|Balcony cabin=out,Grand atrium=view
travel|Mountain homestay|Porch=out
travel|Road trip|Camper van=out
countryside|Barn|Stalls=view
countryside|Watermill|Millpond=out
countryside|Stable|Stalls=view
historical|Roman bath|Caldarium=view
historical|Edo Japan|Castle=out
historical|Speakeasy|Bar=in,Dance floor=in
historical|Wild west ranch|Corral=out,Prairie=out
historical|Belle epoque Paris|Cabaret=in,Boulevard=out
apocalypse|Ruined city|Subway=in
apocalypse|Survivor camp|Shelter=in
apocalypse|Radio tower|Base=out
apocalypse|Greenhouse colony|Solar field=out
steampunk|Clockwork workshop|Forge=view
steampunk|Underground city|Market=in,Cavern street=in
seafaring|Sailing yacht|Helm=out
seafaring|Smuggler cove|Cave=in
seafaring|Naval ship|Bunks=in
music|Jazz club|Bar=in
cities|Venice|Canal=out
cities|Cherry blossom|Night lanterns=out
retro|Drive-in|Car=out,Truck bed=out,Snack bar=out
retro|Roller rink|Rail=in,Skate counter=in
retro|Bowling alley|Lane=in,Seats=in,Bar=in
retro|Shopping mall|Food court=view
holidays|Cherry blossom|Night lanterns=out
holidays|Lunar new year|Temple=out
"""
for line in RAW2.strip().splitlines():
    stem, place, zones = line.split("|")
    for z in zones.split(","):
        k, v = z.split("=")
        SKY[(stem, place, k)] = v
