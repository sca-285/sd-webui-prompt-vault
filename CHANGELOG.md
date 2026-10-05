# Changelog

Prompt Vault follows [semantic versioning](https://semver.org): a new major version may change
the library or saved-prompt files, a minor one adds features, a patch fixes them.
Your data (`prompt_vault/` in the WebUI folder) is never touched by an update.

## 1.1.0 (2026-10-05)

### Muse: every part has something to roll
- Every part of a card now has fifteen and more values to roll through, and a roll never brings back what
  the part has already been until every other one has come: ten rolls, ten different values.
- Wear by kind of place (casual, cozy, formal, business, sporty, beach, outdoor, winter, street, party,
  rustic, bath, fantasy, historical, sci-fi, steampunk, wasteland, nautical, stage, retro, festive,
  school, lingerie), some twenty each for a woman and a man; a job's clothes worn a few ways.
- Doings anyone can have in a place, and doings with what a spot has (sitting at the table, leaning on
  the wall); more teasing, nude and explicit doings, for groups, futanari and non-humans too.
- More shots, angles, viewpoints, light sources (none electric in old worlds), natural light by hour
  and sky, light quality, mood, support and volume, details, styles, expressions (14 per mood), gaze,
  mouth, makeup for men, animals (big ones are never carried, small ones never walked), 30 more jobs.
- A part rolled by hand is drawn even where another part already says something like it.
- Logic: no close-up for two or more people, women's teasing doings for women, poses that need a prop
  only where the prop is, no indoor details under the sea or in an underworld.

### Faster
- An idea takes about 6 ms instead of 15 (the scenes the filters leave are kept between ideas), and the
  scenes are read in the background when the WebUI starts, so the first idea comes at once.

### The Vault tab
- Copy buttons on the Positive and Negative boxes.
- Duplicate tags are dropped when a prompt is sent to txt2img or img2img.
- Fixed: a broken line in the tab's script.

### For contributors
- `tests/run.py` also checks that every part has ten values or more to roll, and that the JavaScript parses.

## 1.0.0 (2026-10-01)

The first release.

### The Vault tab
- An editor for the positive and negative prompt, pulled from and sent to txt2img or img2img.
- A tag library of 2,000+ tags in 20 categories: click to add, right-click to weight,
  Shift+click for the other prompt, search, Hide NSFW; edit it in place, import and export it.
- Suggestions while you type, from the library and about 10,000 Danbooru tags; **Check tags**
  finds typos and made-up tags.
- **Arrange** puts tags in the usual order and drops duplicates (instant, or with Qwen).
- Saved prompts with thumbnails, and the history of your generations.
- Local AI helpers: TIPO (expand a prompt), Qwen-VL (rewrite, describe an image), WD14 (tag an
  image). They run on demand and stop when idle.
- **Image → Prompt** reads an image with WD14, Qwen or both, or takes the prompt saved in it.
- A **Send to Prompt Vault** button under the txt2img and img2img galleries takes the image
  shown there to Image → Prompt.
- The extension has an icon, on its tab and on that button.

### Muse
- A floating button on every tab (`Alt+M`) with prompt ideas, on demand or on a timer.
- 39 themes, about 4,100 scenes: nine places per theme, three spots per place, at four levels
  (SFW, suggestive, nude, explicit; NSFW stays locked until it is turned on). Kitchen, Living
  room, Balcony, Garden, Restroom and School (SFW only) among them.
- Casts from no humans to mixed groups of 6+, futanari, furry, kemono, human + furry, myth and
  fantasy beings, monsters, sci-fi beings and real animals (SFW only); count tags written
  for you.
- Every filter choice leaves 25 scenes or more; what cannot be is greyed out with the reason.
- An idea is a scene in parts (character, face, action, scene, light, camera, look), each
  rolled or locked on its own; the Parts switches turn whole groups off.
- Hour and sky that fit the place; jobs that stay in their worlds; poses that fit the place;
  small parts left out when another part already says the same thing.
- Act and Kink filters for explicit ideas (33 kinks), with anatomy tags that fit the cast.
- Tags, never sentences. NSFW ideas are adults only: every one carries `mature`, and
  minor-related words are dropped from any scene.
- **Your prompt**, two ways: *Keep in front* (what every idea starts with, kept as ideas change)
  or *Build around* (Muse reads your tags into parts, picks a scene that has them and draws
  the rest to fit; 🌱 marks your parts).
- ✕ on a part takes it out of the idea; its + chip brings it back.
- Double-click a part on the card to write it yourself (locked, ✎); double-click a + chip for a
  part the idea left out.
- Tag suggestions while typing in Muse's boxes; optional in the txt2img and img2img prompts.
- Send to txt2img, img2img or the Vault; **Generate** in txt2img or img2img, the image back
  on the card; Arrange, Describe and TIPO on the card; Save; 500 ideas of history.
- A wide two-column card, an avatar of your own, a draggable button.

### For contributors
- `tools/muse_scenes` writes the scene files; `python3 tests/run.py` checks everything, and
  GitHub Actions runs it on every push.
- `python3 tools/package.py` builds the release zip.
