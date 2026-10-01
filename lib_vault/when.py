"""Time of day and weather: the When part of a Muse idea, and what it allows of the others.

A scene that has a sky (outdoors, or a room with a window, a balcony, a skylight) lists its
"times": "night, rain", "morning, clear sky"... Muse draws one first, then keeps out of the
other parts whatever it contradicts: no golden hour at night, no sunbathing in the rain, no
starry sky at noon. Entries that say nothing about the hour or the sky go with anything.
"""

from __future__ import annotations

import re

TIMES = ("morning", "day", "afternoon", "evening", "night")
WEATHERS = ("clear", "cloudy", "overcast", "rain", "fog", "snow")
DAYLIGHT = {"morning", "day", "afternoon", "evening"}

# words -> the hours they can be true at
TIME_WORDS = [
    (r"\b(dawn|sunrise|daybreak|breakfast)\b", {"morning"}),
    (r"\bmorning\b", {"morning"}),
    (r"\b(noon|midday|high noon)\b", {"day"}),
    (r"\bafternoon\b", {"afternoon", "day"}),
    (r"\b(golden hour|blue hour)\b", {"morning", "evening"}),
    (r"\b(sunset|dusk|twilight)\b", {"evening"}),
    (r"\bevening\b", {"evening", "night"}),
    (r"\b(city lights|fireflies|fireworks)\b", {"evening", "night"}),
    (r"\b(night|nighttime|midnight|moon|moonlight|moonlit|full moon|starry|stars|starlight|stargazing|milky way|aurora)\b", {"night"}),
    (r"\b(daylight|daytime|sunny|harsh sun|bright sun|midday sun|blue sky|sunbathing|sunbathe|sunscreen|tropical sun|sunlight|"
     r"sunbeams?|sunlit|sun rays|god rays|dappled|lens flare|sunshine|sun glare|desert sun|snow glare|sun hat|twin suns)\b", DAYLIGHT),
]
# words -> the skies they can be true under
WEATHER_WORDS = [
    (r"\b(rain|rainy|raining|raindrops?|downpour|drizzle|storm|stormy|thunder\w*|lightning)\b", {"rain"}),
    (r"\b(snowing|snowfall|snowflakes?|blizzard)\b", {"snow"}),
    (r"\b(snow|snowy|snowfield|frost|frozen|icicles?|winter)\b", {"snow", "clear", "cloudy", "overcast", "fog"}),
    (r"\b(fog|foggy)\b", {"fog", "overcast", "rain"}),
    (r"\b(overcast|grey sky|gray sky|gloomy)\b", {"overcast", "rain", "fog", "snow"}),
    (r"\b(sunny|blue sky|clear sky|harsh sun|bright sun|midday sun|tropical sun|desert sun|sunbathing|sunbathe|sunscreen|"
     r"starry|stars|starlight|stargazing|milky way|aurora|god rays|sun rays|lens flare|sunshine|sunbeams?|sunlight|dappled sunlight|"
     r"golden hour|sunset|sunrise|sun glare|snow glare)\b", {"clear", "cloudy"}),
]

# what the When part says, word for word; the generator writes these and nothing else
TIME_TAG = {"morning": "morning", "day": "day", "afternoon": "afternoon", "evening": "evening", "night": "night"}
WEATHER_TAG = {  # by hour where it reads differently
    "clear": {"day": "blue sky", "afternoon": "blue sky", "night": "starry sky", "*": "clear sky"},
    "cloudy": {"*": "cloudy sky"}, "overcast": {"*": "overcast"}, "rain": {"*": "rain"}, "fog": {"*": "fog"},
    "snow": {"*": "snowing"},
}
_PARSE_TIME = {"morning": "morning", "dawn": "morning", "sunrise": "morning", "day": "day", "noon": "day", "midday": "day",
               "afternoon": "afternoon", "evening": "evening", "sunset": "evening", "dusk": "evening", "night": "night",
               "midnight": "night"}
_PARSE_WEATHER = {"clear sky": "clear", "blue sky": "clear", "starry sky": "clear", "sunny": "clear", "cloudy sky": "cloudy",
                  "cloudy": "cloudy", "overcast": "overcast", "rain": "rain", "heavy rain": "rain", "light rain": "rain",
                  "thunderstorm": "rain", "fog": "fog", "foggy": "fog", "snowing": "snow", "snow": "snow", "blizzard": "snow"}


def tag(time, weather=None):
    """('night', 'clear') -> 'night, starry sky'"""
    out = [TIME_TAG[time]]
    if weather:
        w = WEATHER_TAG[weather]
        out.append(w.get(time, w["*"]))
    return ", ".join(out)


def parse(entry):
    """'night, rain' -> ('night', 'rain'); what a When entry says, or (None, None)."""
    time = weather = None
    for piece in (p.strip().lower() for p in str(entry or "").split(",")):
        time = time or _PARSE_TIME.get(piece)
        weather = weather or _PARSE_WEATHER.get(piece)
    return time, weather


def needs(entry):
    """(hours, skies) an entry can be true at; None where it does not say."""
    low = str(entry or "").lower()
    times = weathers = None
    for rx, ok in TIME_WORDS:
        if re.search(rx, low):
            times = set(ok) if times is None else times & ok
    for rx, ok in WEATHER_WORDS:
        if re.search(rx, low):
            weathers = set(ok) if weathers is None else weathers & ok
    return times, weathers


def fits(entry, time, weather):
    """Whether an entry can be true at this hour under this sky."""
    times, weathers = needs(entry)
    return (time is None or times is None or time in times) and (weather is None or weathers is None or weather in weathers)
