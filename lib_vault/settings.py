"""Settings, and where things are kept on disk.

Machine-level things (paths, ports, GPU use) live in Settings, not in the tab.
The keys of the old vision settings (pv_llama_server_path, pv_vlm_*) are kept as
they were, so an existing setup carries over.
"""

from __future__ import annotations

import os
import re

from modules import shared

SECTION_MAIN = ("prompt_vault", "Prompt Vault")
SECTION_QWEN = ("prompt_vault_vision", "Prompt Vault (Qwen / llama-server)")
SECTION_TIPO = ("prompt_vault_tipo", "Prompt Vault (TIPO)")
SECTION_WD14 = ("prompt_vault_wd14", "Prompt Vault (WD14 tagger)")

TIPO_MODELS = {
    # label: (Hugging Face repo, file)
    "TIPO-500M-ft (recommended)": ("KBlueLeaf/TIPO-500M-ft", "TIPO-500M-ft-F16.gguf"),
    "TIPO-200M-ft2 (fastest)": ("KBlueLeaf/TIPO-200M-ft2", "TIPO-200M-ft2-F16.gguf"),
    "TIPO-v2.1-1B-A200M": ("KBlueLeaf/TIPO-v2.1-1B-A200M", "TIPO-v2.1-1B-A200M-f16.gguf"),
    "TIPOv2-1B-A200M": ("KBlueLeaf/TIPOv2-1B-A200M", "TIPOv2-1B-A200M-f16.gguf"),
}
TIPO_CUSTOM = "Custom .gguf (path below)"

WD14_MODELS = {
    # label: Hugging Face repo (model.onnx + selected_tags.csv)
    "wd-eva02-large-tagger-v3 (most accurate)": "SmilingWolf/wd-eva02-large-tagger-v3",
    "wd-vit-large-tagger-v3": "SmilingWolf/wd-vit-large-tagger-v3",
    "wd-swinv2-tagger-v3": "SmilingWolf/wd-swinv2-tagger-v3",
    "wd-vit-tagger-v3 (small, fast)": "SmilingWolf/wd-vit-tagger-v3",
    "wd-convnext-tagger-v3": "SmilingWolf/wd-convnext-tagger-v3",
}

DEFAULTS = {
    # main
    "pv_data_dir": "",
    "pv_models_dir": "",
    "pv_autocomplete": True,
    "pv_autocomplete_webui": False,
    "pv_history": True,
    "pv_history_size": 100,
    "pv_hide_nsfw": False,
    "pv_muse": True,
    # llama-server, shared
    "pv_llama_server_path": "",
    "pv_llm_one_at_a_time": True,
    # Qwen (the old vision keys)
    "pv_vlm_models_dir": "",
    "pv_vlm_model_path": "",
    "pv_vlm_mmproj_path": "",
    "pv_vlm_port": 8079,
    "pv_vlm_gpu_layers": 99,
    "pv_vlm_memory": "Auto",
    "pv_vlm_vram_reserve": 4.0,
    "pv_vlm_context": 8192,
    "pv_vlm_extra_args": "",
    "pv_vlm_idle_minutes": 10,
    "pv_vlm_startup_timeout": 180,
    "pv_vlm_max_image_side": 1024,
    "pv_vlm_max_tokens": 320,
    "pv_vlm_temperature": 0.2,
    "pv_vlm_unload_sd": True,
    "pv_vlm_verbose": False,
    # Qwen Chat
    "pv_chat_system": "",
    "pv_chat_max_tokens": 1024,
    "pv_chat_temperature": 0.7,
    "pv_chat_think": False,
    "pv_chat_banned": "",
    # TIPO
    "pv_tipo_model": "TIPO-500M-ft (recommended)",
    "pv_tipo_model_path": "",
    "pv_tipo_port": 8078,
    "pv_tipo_gpu_layers": 99,
    "pv_tipo_idle_minutes": 5,
    "pv_tipo_extra_args": "",
    # WD14
    "pv_wd14_model": "wd-eva02-large-tagger-v3 (most accurate)",
    "pv_wd14_gpu": False,
    "pv_wd14_escape": True,
    "pv_wd14_underscores": False,
    "pv_wd14_exclude": "",
    "pv_wd14_idle_minutes": 5,
}


def opt(name):
    """A setting, falling back to the default when it is not registered (yet)."""
    value = getattr(shared.opts, name, None)
    return DEFAULTS[name] if value is None else value


def clean_path(value):
    return str(value or "").strip().strip('"').strip("'")


# ------------------------------------------------------------------ places


def _webui_paths():
    try:
        from modules import paths_internal

        return paths_internal.data_path, paths_internal.models_path
    except Exception:
        root = os.getcwd()
        return root, os.path.join(root, "models")


def data_dir():
    """Where the library, saved prompts and history live: outside the extension, so
    updating or reinstalling the extension never touches them."""
    custom = clean_path(opt("pv_data_dir"))
    path = custom or os.path.join(_webui_paths()[0], "prompt_vault")
    os.makedirs(path, exist_ok=True)
    return path


def expand(path):
    """A folder as typed: quotes, ~ and %VARIABLES% / $VARIABLES taken care of."""
    path = clean_path(path)
    return os.path.expanduser(os.path.expandvars(path)) if path else ""


def folders(value):
    """Several folders in one box: separated by ; or new lines."""
    return [expand(p) for p in re.split(r"[;\n]+", str(value or "")) if clean_path(p)]


def models_base():
    """The folder of Prompt Vault's own models (WD14, TIPO; Qwen may live there too): Settings, or models/prompt_vault."""
    return expand(opt("pv_models_dir")) or os.path.join(_webui_paths()[1], "prompt_vault")


def models_dir(kind):
    path = os.path.join(models_base(), kind)
    os.makedirs(path, exist_ok=True)
    return path


def webui_models_dir():
    return _webui_paths()[1]


def extensions_dir():
    try:
        from modules import paths_internal

        return paths_internal.extensions_dir
    except Exception:
        return os.path.join(os.getcwd(), "extensions")


# ------------------------------------------------------------------ registration


def register():
    """Called from on_ui_settings."""
    import gradio as gr

    def add(section, options):
        for key, info in options.items():
            if key in getattr(shared.opts, "data_labels", {}):
                continue
            info.section = section
            if getattr(info, "category_id", None) is None:
                info.category_id = "sd"
            shared.opts.add_option(key, info)

    O = shared.OptionInfo
    add(SECTION_MAIN, {
        "pv_data_dir": O("", "Folder for the library, saved prompts and history", gr.Textbox)
        .info("empty: a prompt_vault folder in the WebUI folder. Kept apart from the extension, "
              "so updates never touch it"),
        "pv_models_dir": O("", "Folder for Prompt Vault's models (WD14, TIPO)", gr.Textbox)
        .info("empty: models/prompt_vault in the WebUI folder. Another drive is fine, e.g. D:\\AI\\prompt_vault_models; "
              "move what is already downloaded there yourself (its wd14 and tipo folders)"),
        "pv_autocomplete": O(True, "Suggest tags while typing in the editor")
        .info("from your library and, once a WD14 model is downloaded, about 10,000 Danbooru tags"),
        "pv_autocomplete_webui": O(False, "Also suggest tags in the txt2img and img2img prompts")
        .info("left off by itself when the tag autocomplete extension is installed; needs a reload of the page"),
        "pv_history": O(True, "Remember the prompts of every generation"),
        "pv_history_size": O(100, "How many to remember", gr.Slider, {"minimum": 10, "maximum": 1000, "step": 10}),
        "pv_hide_nsfw": O(False, "Hide the NSFW categories of the library by default")
        .info("categories with NSFW in their name; the tab has a switch too"),
        "pv_muse": O(True, "Show Muse, the floating idea button, on every tab")
        .info("its filters, timer and NSFW switch are on its own card; applies after a page reload"),
    })
    add(SECTION_QWEN, {
        "pv_llama_server_path": O("", "llama-server executable", gr.Textbox)
        .info(r"full path, e.g. H:\AI\llama.cpp\llama-server.exe. Used by Qwen and TIPO"),
        "pv_llm_one_at_a_time": O(True, "Run one model at a time")
        .info("starting Qwen stops TIPO and the other way round: less VRAM, a few seconds "
              "more when switching"),
        "pv_vlm_models_dir": O("", "Folders of Qwen .gguf files (for the lists on Muse's card)", gr.Textbox)
        .info("one or more, separated by ; e.g. D:\\AI\\VLM; E:\\LLM. Also looked through: models/VLM, models/LLM and "
              "the qwen folder of Prompt Vault's models. Muse's settings choose the model and its projector from "
              "what is there; the two paths below are what was chosen"),
        "pv_vlm_model_path": O("", "Qwen-VL model .gguf", gr.Textbox)
        .info("e.g. Qwen3VL-4B-Instruct-Q8_0.gguf"),
        "pv_vlm_mmproj_path": O("", "Vision projector (mmproj) .gguf", gr.Textbox)
        .info("the mmproj-*.gguf that ships beside the model; without it the model cannot see images"),
        "pv_vlm_port": O(8079, "Port for the Qwen server", gr.Number, {"precision": 0})
        .info("127.0.0.1 only. A busy port is skipped automatically"),
        "pv_vlm_memory": O("Auto", "Where Qwen lives: VRAM or RAM", gr.Radio,
                           {"choices": ["Auto", "All on GPU", "KV cache in RAM", "Low VRAM", "RAM only"]})
        .info("Auto: as many layers on the GPU as fit in the free VRAM (less the reserve below), the rest in RAM. "
              "KV cache in RAM: the conversation's memory in RAM. Low VRAM: half the layers (or a MoE model's experts), "
              "the context and the vision part in RAM. RAM only: no VRAM at all, slow. Needs a recent llama.cpp; "
              "an older one is started without these"),
        "pv_vlm_vram_reserve": O(4.0, "VRAM to leave for Stable Diffusion (GB), in Auto", gr.Slider,
                                 {"minimum": 0, "maximum": 24, "step": 0.5}),
        "pv_vlm_gpu_layers": O(99, "GPU layers (-ngl), in All on GPU and KV cache in RAM", gr.Slider,
                               {"minimum": 0, "maximum": 99, "step": 1})
        .info("99 puts the whole model on the GPU; lower it if VRAM is tight"),
        "pv_vlm_context": O(8192, "Context size", gr.Slider, {"minimum": 2048, "maximum": 32768, "step": 1024}),
        "pv_vlm_extra_args": O("", "Extra llama-server arguments", gr.Textbox)
        .info("appended as they are, e.g. -fa on --threads 8"),
        "pv_vlm_idle_minutes": O(10, "Stop the Qwen server after this many idle minutes", gr.Slider,
                                 {"minimum": 0, "maximum": 120, "step": 1})
        .info("0 keeps it running until the WebUI closes"),
        "pv_vlm_startup_timeout": O(180, "Seconds to wait for a server to come up", gr.Slider,
                                    {"minimum": 30, "maximum": 600, "step": 10}),
        "pv_vlm_max_image_side": O(1024, "Resize images so the longest side is at most", gr.Slider,
                                   {"minimum": 448, "maximum": 2048, "step": 64}),
        "pv_vlm_max_tokens": O(320, "Maximum tokens to generate", gr.Slider,
                               {"minimum": 64, "maximum": 2048, "step": 32}),
        "pv_vlm_temperature": O(0.2, "Temperature", gr.Slider, {"minimum": 0.0, "maximum": 1.5, "step": 0.05})
        .info("low is right for captions; rewriting uses a little more"),
        "pv_vlm_unload_sd": O(True, "Free the checkpoint's VRAM while Qwen runs")
        .info("recommended below 16GB"),
        "pv_vlm_verbose": O(False, "Print the servers' own log to the console")
        .info("turn on when a server refuses to start"),
        "pv_chat_system": O("", "Qwen Chat: default system prompt", gr.Textbox, {"lines": 3})
        .info("used when no preset is the default (★ in the chat's ⚙); each conversation can change its own. "
              "Empty: the Assistant preset"),
        "pv_chat_max_tokens": O(1024, "Qwen Chat: longest answer (tokens)", gr.Slider, {"minimum": 128, "maximum": 8192, "step": 64}),
        "pv_chat_temperature": O(0.7, "Qwen Chat: temperature", gr.Slider, {"minimum": 0.0, "maximum": 1.5, "step": 0.05}),
        "pv_chat_banned": O("", "Qwen Chat: banned words", gr.Textbox, {"lines": 4})
        .info("one word or phrase a line (or comma-separated): a single word is blocked while Qwen writes, a phrase is "
              "asked to be avoided; banned tags are also left out of the prompts an answer sends on"),
        "pv_chat_think": O(False, "Qwen Chat: let a thinking model think first")
        .info("for models that reason before answering (Qwen3.5, Qwen3.8...): better answers, much slower. Qwen3-VL "
              "Instruct does not think either way. Captions and rewriting never think"),
    })
    add(SECTION_TIPO, {
        "pv_tipo_model": O("TIPO-500M-ft (recommended)", "TIPO model", gr.Dropdown,
                           {"choices": list(TIPO_MODELS) + [TIPO_CUSTOM]})
        .info("downloaded from Hugging Face on first use into models/prompt_vault/tipo; "
              "files already downloaded by z-tipo-extension are used as they are"),
        "pv_tipo_model_path": O("", "Custom TIPO .gguf", gr.Textbox)
        .info("only with 'Custom .gguf' above"),
        "pv_tipo_port": O(8078, "Port for the TIPO server", gr.Number, {"precision": 0}),
        "pv_tipo_gpu_layers": O(99, "GPU layers (-ngl)", gr.Slider, {"minimum": 0, "maximum": 99, "step": 1})
        .info("TIPO is small (0.4-2 GB); 0 runs it on the CPU and leaves the VRAM alone"),
        "pv_tipo_idle_minutes": O(5, "Stop the TIPO server after this many idle minutes", gr.Slider,
                                  {"minimum": 0, "maximum": 120, "step": 1}),
        "pv_tipo_extra_args": O("", "Extra llama-server arguments for TIPO", gr.Textbox),
    })
    add(SECTION_WD14, {
        "pv_wd14_model": O("wd-eva02-large-tagger-v3 (most accurate)", "WD14 model", gr.Dropdown,
                           {"choices": list(WD14_MODELS)})
        .info("downloaded from Hugging Face on first use into models/prompt_vault/wd14"),
        "pv_wd14_gpu": O(False, "Run WD14 on the GPU")
        .info("needs onnxruntime-gpu; the CPU takes 1-2 seconds per image and no VRAM"),
        "pv_wd14_escape": O(True, "Escape brackets in tags")
        .info(r"ganyu \(genshin impact\): otherwise the WebUI reads the brackets as emphasis"),
        "pv_wd14_underscores": O(False, "Keep underscores in tags"),
        "pv_wd14_exclude": O("", "Never output these tags", gr.Textbox)
        .info("comma-separated"),
        "pv_wd14_idle_minutes": O(5, "Free the WD14 model after this many idle minutes", gr.Slider,
                                  {"minimum": 0, "maximum": 60, "step": 1}),
    })
