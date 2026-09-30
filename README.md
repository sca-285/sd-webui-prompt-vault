# Stable Diffusion WebUI Prompt Vault

A prompt workbench for **Stable Diffusion WebUI Forge**, **reForge** and **Forge Classic (Neo)**:
a searchable tag library, saved prompts and history, and three local AI helpers (TIPO,
Qwen-VL and the WD14 tagger) in one tab.

![The library](docs/library.webp)

## Features

- **Editor.** A positive and a negative prompt, pulled from and sent to txt2img or img2img.
- **Tag library.** 2,000+ tags in 20 categories. Click a tag to add it, click again to
  remove it; tags already in the prompt are lit.
  - **Search** across the whole library.
  - **Right-click** an added tag to change its weight: `(tag:1.2)`.
  - **Shift+click** sends a tag to the other prompt. Tags of the *Negative* categories go
    to the negative prompt by themselves.
  - **Hide NSFW** hides the categories with NSFW in their name, for when the screen is shared.
- **Library editing, no reload.** Add, rename, move and delete tags, groups and
  categories; import and export the library as JSON.
- **Suggestions while you type**, from your library and about 10,000 Danbooru tags.
  **🔍 Check tags** lists the tags that are neither (typos, made-up tags) and adds them to
  the library in one click.
- **Saved prompts**: the positive and negative prompt under a name, with a thumbnail.
- **History**: the prompts of your last generations, one click from coming back.
- **🌱 TIPO** turns a few tags or a short idea into a full prompt.
- **✍️ Qwen** rewrites a prompt: tags into a paragraph, a paragraph into tags, any
  language into English, or any instruction ("make it night time").
- **🏞️ Image → Prompt**: exact Danbooru tags with WD14, a description with Qwen, or both.
  An image made by the WebUI gives back its own prompt with 🧾.
- **💡 Muse**, a floating button on every tab: a prompt idea now and then (every 5–30
  minutes, never while an image is generating) or whenever you ask (`Alt+M`).
  - Ideas come from **packs** (portrait, film, horror, sci-fi… and NSFW packs, off until you
    turn them on), each made of coherent scenes: the subject, action, place and light of an
    idea always belong together. Pick the packs you want on its settings page (the gear).
  - **Send** writes the idea into txt2img, img2img or the Vault editor, replacing or
    appending, and adds the idea's negatives that are missing from your negative prompt.
  - Edit the idea before sending, step back through the last 20 with ‹ ›, expand it with
    **TIPO**, keep words out with **Never use**, give the button your own **avatar**.
  - Drag the button anywhere; the ring around it fills up until the next idea.
  - NSFW ideas never carry minor-related tags, whatever a pack says, and always send
    `child, loli, shota, underage` as negatives.

![The AI tools](docs/ai-tools.webp)

## Your data is safe

The library, saved prompts, history and Muse's settings live **outside the extension**, in a
`prompt_vault` folder in the WebUI folder (**Settings → Prompt Vault** can move it).
Updating or reinstalling the extension never touches them.

- Every save goes to a temporary file first and then replaces the real one, so a crash in
  the middle of a save cannot leave a broken file.
- The last 20 versions of the library are kept in `prompt_vault/backups`.
- **🧺 Add missing default tags** (in *Edit the library*) adds what a newer version of
  the default library has and yours does not. It removes nothing.

**Coming from the first versions?** Those kept the library inside the extension's own
folder (`prompt_vault.json`). On first start, the newest `prompt_vault.json` found in
`extensions/` becomes your library, tags you added included; the old file is left as it
was. Install this version, start the WebUI once, check your tags, then delete the old
extension folder. Keep the two from being enabled at the same time: both would add a
*Prompt Vault* tab.

## Installation

**Extensions → Install from URL**, paste this repository's URL, **Install**, then restart
the WebUI. Or clone it into `extensions/`.

The library, the editor, saved prompts and history need nothing more.

### The AI models: download them first

Each AI tool needs its model files. **Download them yourself with a browser or a download
manager** before the first use: it is much faster than letting the extension fetch a 1 GB
file over one connection while you wait, and a broken download can be resumed. Direct
links for every model are in **[SETUP_AI.md](SETUP_AI.md)**. The short version, for the
recommended models:

| Tool | Download | Put it in |
|---|---|---|
| WD14 | [model.onnx](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/model.onnx) and [selected_tags.csv](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/selected_tags.csv) (~470 MB) | `models/prompt_vault/wd14/wd-swinv2-tagger-v3/` |
| TIPO | [TIPO-500M-ft-F16.gguf](https://huggingface.co/KBlueLeaf/TIPO-500M-ft/resolve/main/TIPO-500M-ft-F16.gguf) (~1 GB) | `models/prompt_vault/tipo/` |
| llama-server (for TIPO and Qwen) | from [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases): the zip for your GPU, and for NVIDIA also the matching `cudart-…` zip | unzip both into one folder, e.g. `H:\AI\llama.cpp\`; paste the path of `llama-server.exe` in Settings |
| Qwen-VL | two files of one size: `Qwen3VL-4B-Instruct-Q8_0.gguf` and `mmproj-Qwen3VL-4B-Instruct-F16.gguf` from [Qwen3-VL-4B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/tree/main) | any folder, e.g. `models\VLM\`; paste both paths in Settings |

Which zip fits your GPU, which Qwen size fits your VRAM, and how to check that it all
works: **[SETUP_AI.md](SETUP_AI.md)**, sections 1 and 2.

Keep the file names as they download. Then check the model choices in **Settings →
Prompt Vault (WD14 tagger)**, **(TIPO)** and **(Qwen / llama-server)**.

If a WD14 or TIPO file is missing, the extension still downloads it the first time a
button needs it; the console shows the progress.

The extension installs `onnxruntime` for WD14 when nothing provides it yet. Qwen and
TIPO run in llama-server, a separate program: nothing else is installed into the WebUI.

## Memory

- The AI models load when a button needs them and are **freed after a few idle
  minutes** (Settings). **⏹️ Stop all AI models** frees them at once.
- Qwen and TIPO **never run together** by default.
- While Qwen loads, the checkpoint can leave VRAM and come back afterwards (on by default).
- WD14 runs on the CPU.
- A llama-server left running by a WebUI that crashed is stopped at the next start.

## Settings

**Settings → Prompt Vault**: the data folder, suggestions, history, hiding NSFW by default,
showing Muse at all. Everything else about Muse is on its own panel.
**Prompt Vault (Qwen / llama-server)**, **(TIPO)** and **(WD14 tagger)**: the models and
how they run; see [SETUP_AI.md](SETUP_AI.md).

## Files

```
prompt_vault/            (in the WebUI folder)
├─ library.json          your library
├─ prompts.json          saved prompts
├─ history.json          history
├─ backups/              earlier versions of the library
└─ muse/
   ├─ state.json         Muse's settings
   ├─ avatar.png         your avatar, if you chose one
   └─ packs/             packs of your own (optional)
models/prompt_vault/
├─ tipo/
│  └─ TIPO-500M-ft-F16.gguf
└─ wd14/
   └─ wd-swinv2-tagger-v3/
      ├─ model.onnx
      └─ selected_tags.csv
```

## Muse packs of your own

A pack is a JSON file in `prompt_vault/muse/packs/`; a pack with the id of a shipped one
(see `data/muse_packs/`) replaces it. It is made of **scenes**: each scene holds what
belongs together (who is there, what they do, where, in what light), and an idea takes
one scene, then one entry of each of its lists. Keep every entry of a list compatible
with every entry of the others *in the same scene*, and the ideas stay coherent.

```json
{
  "id": "my_pack", "name": "My pack", "nsfw": false,
  "styles": ["film still, 35mm"], "negatives": ["blurry", "watermark"],
  "scenes": [
    {"title": "Night market",
     "subjects": ["1girl, yukata", "1boy, jinbei"],
     "actions": ["holding a candy apple", "looking at the lanterns"],
     "settings": ["summer festival at night, food stalls"],
     "lighting": ["paper lantern light"],
     "camera": ["cowboy shot"],
     "details": ["fireworks in the sky"]}
  ]
}
```

A list a scene leaves out (here `styles`) comes from the pack, so the pack's own lists must
suit every scene. The first pack format, without scenes, still works as one big scene.

## Credits

- **TIPO** and **KGen** by KohakuBlueLeaf (<https://github.com/KohakuBlueleaf/KGen>,
  Apache-2.0). The TIPO request format and answer parsing are adapted from KGen; see
  [NOTICE.md](NOTICE.md).
- **WD14 tagger** models by SmilingWolf (<https://huggingface.co/SmilingWolf>).
- **Qwen-VL** by the Qwen team; **llama.cpp** by ggml-org.

Thanks also to **Claude**, Anthropic's AI assistant, for help building this extension.

## License

MIT, see [LICENSE](LICENSE). The parts adapted from KGen stay under Apache-2.0, see
[NOTICE.md](NOTICE.md). The models are not part of this repository: each keeps its own license.
