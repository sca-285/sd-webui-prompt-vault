# Setting up the AI tools

Prompt Vault has three helpers. All of them run on your own machine, and each one
is optional: the library, the editor, saved prompts and history work without any of them.

| Tool | Does | Needs | Memory |
|---|---|---|---|
| **WD14** | image → Danbooru tags, each with a confidence | two files you download | CPU, no VRAM |
| **TIPO** | a few tags or a short idea → a full prompt | llama-server and one .gguf you download | 0.4–2 GB, GPU or CPU |
| **Qwen-VL** | image → tags or a description; rewrites, translates and edits prompts | llama-server and two .gguf files you download | 2–7 GB VRAM |

Qwen and TIPO both run in **llama-server**, a small program from llama.cpp that the
extension starts when it needs it and stops after a few idle minutes. Nothing has to be
installed into the WebUI and nothing is compiled.

## 1. llama-server (for Qwen and TIPO)

llama-server is part of **llama.cpp**. It is not installed: you unzip it and point the
extension at it.

### Download

Open <https://github.com/ggml-org/llama.cpp/releases> and take the **newest** release
(the tags are build numbers such as `b10456`). Under **Assets**, pick the zip for your
graphics card. `bXXXXX` below is the build number of the release you opened:

| Your GPU | Download | Also download |
|---|---|---|
| NVIDIA RTX 20 / 30 / 40 | `llama-bXXXXX-bin-win-cuda-12.4-x64.zip` | `cudart-llama-bin-win-cuda-12.4-x64.zip` |
| NVIDIA RTX 50, or any NVIDIA with a recent driver | `llama-bXXXXX-bin-win-cuda-13.x-x64.zip` | `cudart-llama-bin-win-cuda-13.x-x64.zip` (same 13.x number) |
| AMD Radeon | `llama-bXXXXX-bin-win-vulkan-x64.zip` (or `win-rocm-…` for a ROCm-supported card) | nothing |
| Intel Arc | `llama-bXXXXX-bin-win-vulkan-x64.zip` | nothing |
| No GPU / to keep the VRAM free | `llama-bXXXXX-bin-win-cpu-x64.zip` | nothing |

On Linux, take `llama-bXXXXX-bin-ubuntu-vulkan-x64.tar.gz` (or `ubuntu-x64` for the CPU).

The **cudart** zip holds the CUDA runtime DLLs; without it the CUDA build does not start
("cudart64_12.dll was not found"). The CUDA 13 build needs a recent NVIDIA driver: run
`nvidia-smi` in a command prompt, and if the top right says `CUDA Version: 13.0` or
higher, CUDA 13 works; otherwise take CUDA 12.4 (or update the driver). For RTX 50 cards,
take CUDA 13.

### Install

1. Make a folder, e.g. `H:\AI\llama.cpp\`.
2. Unzip **both** zips (the build and the cudart one) **into that same folder**, so that
   `llama-server.exe` and the `cudart64_*.dll` / `cublas64_*.dll` files sit side by side.
3. Check it: open a command prompt in that folder (type `cmd` in Explorer's address bar)
   and run

   ```
   llama-server.exe --version
   ```

   It prints the version and, for CUDA, the card it found (`found 1 CUDA devices: … RTX …`).
   An error about a missing DLL means the cudart zip is not in the same folder.

4. In **Settings → Prompt Vault (Qwen / llama-server)**, paste the full path and press
   **Apply settings**:

   ```
   llama-server executable   H:\AI\llama.cpp\llama-server.exe
   ```

To update llama.cpp later, unzip the new release over the old folder.

Qwen3-VL needs a build from November 2025 or later. If the server starts and then says it
does not know the model's architecture, your llama.cpp is older than the model: download
the newest release.

**Run one model at a time** (on by default): starting Qwen stops TIPO and the other way
round, so they never sit in VRAM together. Switching costs a few seconds.

## 2. Qwen-VL

Qwen needs **two files from the same repository**: the model, and its projector
(`mmproj-…gguf`, the part that sees images). A model and a projector of different sizes
(a 4B model with the 8B projector) do not work together.

### Choose a size

| Your VRAM | Repository | Model file | Projector file |
|---|---|---|---|
| 6–8 GB | [Qwen3-VL-4B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/tree/main) | `Qwen3VL-4B-Instruct-Q4_K_M.gguf` (2.5 GB) | `mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf` (454 MB) |
| **10–12 GB** | [Qwen3-VL-4B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct-GGUF/tree/main) | **`Qwen3VL-4B-Instruct-Q8_0.gguf` (4.28 GB)** | `mmproj-Qwen3VL-4B-Instruct-F16.gguf` (836 MB) or `…-Q8_0.gguf` (454 MB) |
| 16 GB and more | [Qwen3-VL-8B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct-GGUF/tree/main) | `Qwen3VL-8B-Instruct-Q4_K_M.gguf` (5.03 GB) | `mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf` (752 MB) |
| 4 GB, or on the CPU | [Qwen3-VL-2B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF/tree/main) | `Qwen3VL-2B-Instruct-Q4_K_M.gguf` (1.11 GB) | `mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf` (445 MB) |

The model needs about its file size in VRAM, plus the projector, plus half a gigabyte to
a gigabyte for the context. The checkpoint leaves VRAM while Qwen loads (see below), so the
two do not have to fit together.

Take the **Instruct** repositories, not **Thinking**: Thinking writes a long block of
reasoning before every answer. The F16 model files are too big to be worth it here.

### Download

On the repository page (**Files and versions**), the ↓ icon next to a file downloads
it. A download manager takes the same links. Put both files in one folder, e.g.
`models\VLM\` of your WebUI, or anywhere else.

### Settings

In **Settings → Prompt Vault (Qwen / llama-server)**, the full paths of both files, then
**Apply settings**:

```
Qwen-VL model .gguf               H:\AI\models\VLM\Qwen3VL-4B-Instruct-Q8_0.gguf
Vision projector (mmproj) .gguf   H:\AI\models\VLM\mmproj-Qwen3VL-4B-Instruct-F16.gguf
```

Paths with quotes around them, the way Explorer's *Copy as path* gives them, are fine.

### Check it

In the Prompt Vault tab, press **ℹ️ AI model status**: it says `Qwen: stopped` when
everything is found, or names what is missing. Then open **✍️ Rewrite with Qwen**, type
a few tags and press **Rewrite**. The first press starts the server and loads the model
(as long as loading a checkpoint); the next ones answer in a second or two.

When the server refuses to start, turn on **Print the servers' own log to the console**
and press again: llama-server's own messages name the problem.

**Free the checkpoint's VRAM while Qwen runs** (on by default, recommended below 16 GB):
the checkpoint leaves VRAM while the Qwen server starts and comes back afterwards. Once
the server runs, later requests leave the checkpoint alone.

The same model serves both **🏞️ Image → Prompt** and **✍️ Rewrite with Qwen**:

- *Tags → sentence*: a tag list becomes a paragraph, for SDXL, Flux and other models
  that read plain English.
- *Sentence → tags*: the other way.
- *Translate to English*: write the idea in Vietnamese (or any language), get an English prompt.
- *Follow my instruction*: "make it night time", "change the outfit to a kimono"...

LoRAs, embeddings, weighted pieces such as `(red hair:1.2)` and `BREAK` never go through
the model: they are kept aside and put back in front of the answer.

## 3. TIPO

Download **one** file and put it in `models/prompt_vault/tipo/` of your WebUI folder
(create the folders if they are not there):

| Model | Download | Size | Notes |
|---|---|---|---|
| **TIPO-500M-ft** | [TIPO-500M-ft-F16.gguf](https://huggingface.co/KBlueLeaf/TIPO-500M-ft/resolve/main/TIPO-500M-ft-F16.gguf) | ~1 GB | the default, the best-tested one |
| TIPO-200M-ft2 | [TIPO-200M-ft2-F16.gguf](https://huggingface.co/KBlueLeaf/TIPO-200M-ft2/resolve/main/TIPO-200M-ft2-F16.gguf) | ~0.4 GB | fastest; fine on the CPU |
| TIPO-v2.1-1B-A200M | [TIPO-v2.1-1B-A200M-f16.gguf](https://huggingface.co/KBlueLeaf/TIPO-v2.1-1B-A200M/resolve/main/TIPO-v2.1-1B-A200M-f16.gguf) | ~2 GB | newer; if llama-server refuses it, update llama.cpp |

```
models/prompt_vault/tipo/TIPO-500M-ft-F16.gguf
```

Then pick the same model in **Settings → Prompt Vault (TIPO)**. Keep the file name as it
downloads: the extension finds the file by its name. A .gguf somewhere else works too:
choose **Custom .gguf** and paste its path.

If you use **z-tipo-extension**, the models it already downloaded (`models/kgen`) are
used as they are: nothing to download.

With **GPU layers** at 0, TIPO runs on the CPU and leaves the VRAM alone; a 200M or 500M
model is still quick there.

In the tab:

- **Output**: *Tags*, *Natural language*, or *Tags + natural language*.
- **Length**: how much TIPO adds.
- **Never add**: tags TIPO must not produce; `*` works as a wildcard (`*hat`, `text*`).
- **Seed**: the same seed and the same prompt give the same result.

Your own tags stay in the result, so *Replace* loses nothing. LoRAs, weights and `BREAK`
are kept aside, as with Qwen.

TIPO is trained on Danbooru-style prompts: it shines with anime and illustration
checkpoints (Illustrious, NoobAI, Pony, Animagine). For photographic prompts, Qwen's
rewriting is usually the better tool.

## 4. WD14

Download **two** files of one model, `model.onnx` and `selected_tags.csv`, and put them
in a folder named after the model, in `models/prompt_vault/wd14/`:

| Model | model.onnx | selected_tags.csv | Size | Notes |
|---|---|---|---|---|
| **wd-swinv2-tagger-v3** | [download](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/model.onnx) | [download](https://huggingface.co/SmilingWolf/wd-swinv2-tagger-v3/resolve/main/selected_tags.csv) | ~470 MB | the default: accurate and light |
| wd-eva02-large-tagger-v3 | [download](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3/resolve/main/model.onnx) | [download](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3/resolve/main/selected_tags.csv) | ~1.26 GB | the most accurate |
| wd-vit-large-tagger-v3 | [download](https://huggingface.co/SmilingWolf/wd-vit-large-tagger-v3/resolve/main/model.onnx) | [download](https://huggingface.co/SmilingWolf/wd-vit-large-tagger-v3/resolve/main/selected_tags.csv) | ~1.26 GB | |
| wd-vit-tagger-v3 | [download](https://huggingface.co/SmilingWolf/wd-vit-tagger-v3/resolve/main/model.onnx) | [download](https://huggingface.co/SmilingWolf/wd-vit-tagger-v3/resolve/main/selected_tags.csv) | ~380 MB | small and fast |
| wd-convnext-tagger-v3 | [download](https://huggingface.co/SmilingWolf/wd-convnext-tagger-v3/resolve/main/model.onnx) | [download](https://huggingface.co/SmilingWolf/wd-convnext-tagger-v3/resolve/main/selected_tags.csv) | ~400 MB | |

```
models/prompt_vault/wd14/wd-swinv2-tagger-v3/model.onnx
models/prompt_vault/wd14/wd-swinv2-tagger-v3/selected_tags.csv
```

The folder name is the model's name exactly as in the table; every model's files are
called `model.onnx` and `selected_tags.csv`, so they must not share a folder. Then pick the
same model in **Settings → Prompt Vault (WD14 tagger)**.

It runs on the CPU with onnxruntime (installed with the extension when missing): one or
two seconds per image, no VRAM. With onnxruntime-gpu installed, **Run WD14 on the GPU** uses it.

- **Tag threshold** / **Character threshold** in the tab: lower finds more, with more mistakes.
- **Escape brackets** (on): `ganyu \(genshin impact\)`, so the WebUI does not read the
  brackets as emphasis.

Its tag list (about 10,000 Danbooru tags) also feeds the suggestions while you type and
**🔍 Check tags**.

**WD14 tags + Qwen description** gives both: exact tags from WD14, and a description from
Qwen that is told which tags WD14 found.

## Why download by hand

The extension can download TIPO and WD14 by itself the first time a button needs them,
but it does so over one slow connection while the button waits, and a 1 GB file can take
many minutes. A browser or a download manager (IDM, aria2, Free Download Manager) is
usually much faster, can resume a broken download, and you download once for all your
WebUIs.

If you let the extension do it anyway:

- the console shows the progress (`model.onnx: 40% of 470 MB`);
- a download that breaks leaves nothing behind, and the next press starts it again;
- a mirror works: set the `HF_ENDPOINT` environment variable before starting the WebUI.

## When something goes wrong

The line under each button carries the real error:

- *not set up yet: …*: a path in Settings is empty or wrong.
- *llama-server exited with code N*, followed by the server's last lines: they usually
  name the problem (unknown architecture, wrong mmproj, out of memory).
- *did not become ready in time*: a big model on a cold disk. Raise the startup timeout,
  or turn on **Print the servers' own log** and watch the console.
- *could not download …*: download the file by hand (sections 3 and 4); the message names
  the address and the place it belongs.

**ℹ️ AI model status** shows what is running; **⏹️ Stop all AI models** frees everything at
once. A server left running by a WebUI that crashed is stopped the next time the WebUI starts.
