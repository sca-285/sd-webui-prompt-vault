"""Qwen-VL through llama-server: read an image, or rewrite a prompt.

The server speaks the OpenAI chat-completions shape (so do LM Studio, Ollama and
KoboldCpp). Qwen-VL is a full chat model, so the same server that reads images
also rewrites and translates prompts: no second model to download.
"""

from __future__ import annotations

import base64
import io
import os
import re
import time

from . import gguf, llama, settings, text, vram
from . import qwen_prompts as prompts


def _missing():
    problems = llama.server_missing()
    for label, key in (("Qwen model .gguf", "pv_vlm_model_path"), ("mmproj .gguf", "pv_vlm_mmproj_path")):
        value = settings.clean_path(settings.opt(key))
        if not value:
            problems.append(f"{label} is not set")
        elif not os.path.isfile(value):
            problems.append(f"{label} not found: {value}")
    return problems


MEMORY_MODES = ("Auto", "All on GPU", "KV cache in RAM", "Low VRAM", "RAM only")
MEMORY = {"note": ""}  # how the running server was placed, for the status line


def _free_vram_gb():
    try:
        import torch

        if torch.cuda.is_available():
            free, _total = torch.cuda.mem_get_info()
            return free / 1024 ** 3
    except Exception:
        pass
    return None


def _memory_args(model, mmproj):
    """llama-server's placement flags: what goes on the GPU, what stays in RAM."""
    mode = settings.opt("pv_vlm_memory") if settings.opt("pv_vlm_memory") in MEMORY_MODES else "Auto"
    layers_opt = int(settings.opt("pv_vlm_gpu_layers"))
    meta = gguf.info(model)
    layers, experts = meta["layers"], meta["experts"]
    size = os.path.getsize(model) / 1024 ** 3 if os.path.isfile(model) else 0
    mm_size = os.path.getsize(mmproj) / 1024 ** 3 if mmproj and os.path.isfile(mmproj) else 0
    if mode == "All on GPU":
        MEMORY["note"] = f"{layers_opt} layers on the GPU"
        return ["-ngl", str(layers_opt)]
    if mode == "KV cache in RAM":
        MEMORY["note"] = f"{layers_opt} layers on the GPU, the context in RAM"
        return ["-ngl", str(layers_opt), "--no-kv-offload"]
    if mode == "RAM only":
        MEMORY["note"] = "everything in RAM (slow, no VRAM)"
        return ["-ngl", "0", "--no-kv-offload", "--no-mmproj-offload"]
    if mode == "Low VRAM":
        if experts:  # a mixture of experts: the experts (most of the weights) in RAM, the rest on the GPU
            MEMORY["note"] = "experts in RAM, attention on the GPU, the context and vision in RAM"
            return ["-ngl", "99", "--cpu-moe", "--no-kv-offload", "--no-mmproj-offload"]
        n = max(1, (layers or 40) // 2)
        MEMORY["note"] = f"{n} of {layers or '?'} layers on the GPU, the rest, the context and vision in RAM"
        return ["-ngl", str(n), "--no-kv-offload", "--no-mmproj-offload"]
    # Auto: as much as fits in the free VRAM, less what Stable Diffusion needs back
    free = _free_vram_gb()
    if free is None or not size:
        MEMORY["note"] = f"{layers_opt} layers on the GPU (free VRAM unknown)"
        return ["-ngl", str(layers_opt)]
    context_gb = int(settings.opt("pv_vlm_context")) / 1024 * 0.14
    budget = free - float(settings.opt("pv_vlm_vram_reserve")) - 0.6
    if budget >= size + mm_size + context_gb:
        MEMORY["note"] = f"all on the GPU ({free:.1f} GB free)"
        return ["-ngl", "99"]
    flags = ["--no-kv-offload"]
    if budget < size + mm_size:
        flags.append("--no-mmproj-offload")  # the vision part in RAM: the layers come first
    else:
        budget -= mm_size
    if experts and budget >= size * 0.15:
        MEMORY["note"] = f"experts in RAM, the rest on the GPU ({free:.1f} GB free)"
        return ["-ngl", "99", "--cpu-moe"] + flags
    n = max(0, int((layers or 40) * max(0.0, budget) / size))
    MEMORY["note"] = f"{n} of {layers or '?'} layers on the GPU, the rest and the context in RAM ({free:.1f} GB free)"
    return ["-ngl", str(n)] + flags


def _model_args():
    model = settings.clean_path(settings.opt("pv_vlm_model_path"))
    mmproj = settings.clean_path(settings.opt("pv_vlm_mmproj_path"))
    return ["-m", model, "--mmproj", mmproj, "-c", str(int(settings.opt("pv_vlm_context")))] + _memory_args(model, mmproj)


def _placement():
    """What the server was started with that a change in Settings should restart it for."""
    return (settings.clean_path(settings.opt("pv_vlm_model_path")), settings.opt("pv_vlm_memory"),
            float(settings.opt("pv_vlm_vram_reserve")), int(settings.opt("pv_vlm_gpu_layers")), int(settings.opt("pv_vlm_context")))


SERVER = llama.LlamaServer("Qwen", "pv_vlm_port", "pv_vlm_idle_minutes", _model_args, _missing,
                           "pv_vlm_extra_args", "pv_vlm_gpu_layers")


def _encode(image, max_side):
    """PIL image -> data: URL, shrunk so the vision tower is not handed pixels it does not use."""
    from PIL import Image

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    longest = max(image.size)
    if max_side and longest > max_side:
        scale = max_side / float(longest)
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}", image.size


def chat(content, *, max_tokens=None, temperature=None, timeout=300):
    SERVER.restart_if_changed(_placement())
    body = {
        "messages": [{"role": "user", "content": content}],
        "max_tokens": int(max_tokens if max_tokens is not None else settings.opt("pv_vlm_max_tokens")),
        "temperature": float(temperature if temperature is not None else settings.opt("pv_vlm_temperature")),
        "stream": False,
    }
    answer = SERVER.post("/v1/chat/completions", body, timeout=timeout)
    try:
        reply = answer["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"unexpected answer from the Qwen server: {str(answer)[:300]}") from None
    if isinstance(reply, list):
        reply = "".join(part.get("text", "") for part in reply if isinstance(part, dict))
    return str(reply or "")


class _SdAside:
    """Takes the checkpoint out of VRAM while Qwen loads, when the setting says so.

    Only when the Qwen server is not running yet: once it runs, its weights already have
    their place and a request needs little more. A checkpoint is put back only if one was
    loaded before (Forge Neo loads it lazily; nothing is loaded just for this)."""

    def __enter__(self):
        self.put_back = None
        self.was_real = False
        if bool(settings.opt("pv_vlm_unload_sd")) and not SERVER.running():
            self.was_real = vram._model_is_real()
            if self.was_real:
                self.put_back = vram.release()
                vram.collect()
        return self

    def __exit__(self, *exc):
        if self.put_back is not None:
            try:
                self.put_back()
            except Exception as e:
                print(f"[Prompt Vault] restoring the checkpoint failed: {e}")
            if self.was_real:
                vram.restore()
            vram.collect()


def read_image(image, mode="tags", hint_tags=""):
    """(text, note). mode: tags | description. hint_tags: WD14's tags, to steer a description."""
    if image is None:
        return "", "Load an image first."
    started = time.time()
    try:
        with _SdAside():
            data_url, size = _encode(image, int(settings.opt("pv_vlm_max_image_side")))
            if mode == "description":
                instruction = prompts.TAGGED_DESCRIPTION_PROMPT.format(tags=hint_tags) if hint_tags \
                    else prompts.DESCRIPTION_PROMPT
            else:
                instruction = prompts.TAG_PROMPT
            raw = chat([{"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": instruction}])
        result = prompts.clean_description(raw) if mode == "description" else prompts.clean_tags(raw)
        if not result.strip():
            return "", f"Qwen answered, but nothing usable came back: {raw[:120]!r}"
        what = f"{len(text.split(result))} tags" if mode == "tags" else f"{len(result.split())} words"
        return result, f"Qwen: {what} from a {size[0]}x{size[1]} image in {time.time() - started:.1f}s"
    except Exception as exc:
        return "", f"Qwen: {exc}"


def rewrite(prompt, task, instruction=""):
    """(text, note): one of prompts.TEXT_TASKS applied to prompt."""
    prompt = (prompt or "").strip()
    if not prompt:
        return "", "The editor is empty."
    if task not in prompts.TEXT_TASKS:
        return "", f"Unknown task {task!r}"
    if task == "Follow my instruction" and not (instruction or "").strip():
        return "", "Write the instruction first."
    template, form = prompts.TEXT_TASKS[task]

    # LoRAs, embeddings, weights, BREAK: never through the model, put back in front afterwards
    kept = []
    if task != "Translate to English":
        pieces = text.split(prompt)
        kept = [p for p in pieces if text.is_special(p)]
        if kept and len(kept) < len(pieces):
            prompt = text.join(p for p in pieces if not text.is_special(p))
        else:
            kept = []

    started = time.time()
    try:
        with _SdAside():
            raw = chat(template.format(prompt=prompt, instruction=(instruction or "").strip()),
                       max_tokens=max(int(settings.opt("pv_vlm_max_tokens")), 512),
                       temperature=max(float(settings.opt("pv_vlm_temperature")), 0.3))
    except Exception as exc:
        return "", f"Qwen: {exc}"

    if form == "tags":
        result = prompts.clean_tags(raw)
    elif form == "description":
        result = prompts.clean_description(raw)
    else:
        result = prompts._strip_preamble(prompts._strip_wrapper(raw)).strip().strip('"')
    if not result:
        return "", f"Qwen answered, but nothing usable came back: {raw[:120]!r}"
    if kept:
        result = f"{text.join(kept)}, {result}"
    return result, f"Qwen: {task.lower()} in {time.time() - started:.1f}s"


# ------------------------------------------------------------------ choosing the model from a list
MODEL_DIRS = ("VLM", "LLM", "llm", "Qwen", "qwen", os.path.join("prompt_vault", "qwen"))


def _model_dirs():
    """Where .gguf files for Qwen are looked for: models/VLM and the like, the folder in Settings, and the
    folders of the files already chosen."""
    base = settings.webui_models_dir()
    dirs = [os.path.join(base, d) for d in MODEL_DIRS]
    extra = settings.clean_path(settings.opt("pv_vlm_models_dir"))
    if extra:
        dirs.insert(0, extra)
    for key in ("pv_vlm_model_path", "pv_vlm_mmproj_path"):
        p = settings.clean_path(settings.opt(key))
        if p:
            dirs.append(os.path.dirname(p))
    seen, out = [], []
    for d in dirs:
        k = os.path.normcase(os.path.abspath(d))
        inside = any(k == s or k.startswith(s + os.sep) for s in seen)  # a folder already looked through
        if not inside and os.path.isdir(d):
            seen.append(k)
            out.append(d)
    return out


def _tokens_of(name):
    stem = os.path.splitext(os.path.basename(name))[0].lower()
    stem = stem.replace("mmproj", " ").replace("qwen3vl", "qwen3-vl")
    return {t for t in re.split(r"[^a-z0-9]+", stem) if t and t not in ("gguf", "f16", "f32", "bf16", "q8", "0", "model")}


def models():
    """{"models", "mmprojs", "model", "mmproj", "memory", "memory_modes", "dirs", "running", "note"}."""
    found = {}
    for d in _model_dirs():
        for root, _subdirs, files in os.walk(d):
            if root[len(d):].count(os.sep) > 2:
                continue
            for f in files:
                if f.lower().endswith(".gguf"):
                    p = os.path.join(root, f)
                    found.setdefault(os.path.normcase(os.path.abspath(p)), p)
    items = []
    for p in sorted(found.values(), key=lambda x: os.path.basename(x).lower()):
        try:
            size = os.path.getsize(p)
        except OSError:
            continue
        items.append({"path": p, "name": os.path.basename(p), "folder": os.path.basename(os.path.dirname(p)),
                      "gb": round(size / 1024 ** 3, 2), "mmproj": "mmproj" in os.path.basename(p).lower()})
    model = settings.clean_path(settings.opt("pv_vlm_model_path"))
    mmproj = settings.clean_path(settings.opt("pv_vlm_mmproj_path"))
    return {"models": [i for i in items if not i["mmproj"]], "mmprojs": [i for i in items if i["mmproj"]],
            "model": model, "mmproj": mmproj,
            "memory": settings.opt("pv_vlm_memory") if settings.opt("pv_vlm_memory") in MEMORY_MODES else "Auto",
            "memory_modes": list(MEMORY_MODES), "dirs": _model_dirs(), "running": SERVER.running(), "note": MEMORY.get("note", "")}


def mmproj_for(model_path, mmprojs):
    """The vision projector that belongs to a model: the one in its folder whose name shares the most with it."""
    if not model_path:
        return ""
    folder = os.path.normcase(os.path.dirname(os.path.abspath(model_path)))
    mine = _tokens_of(model_path)
    sizes = lambda tokens: {t for t in tokens if re.fullmatch(r"\d+(\.\d+)?b|a\d+b", t)}
    my_size = sizes(mine)
    best, score = "", None
    for m in mmprojs:
        theirs = _tokens_of(m["path"])
        s = len(mine & theirs)
        if os.path.normcase(os.path.dirname(os.path.abspath(m["path"]))) == folder:
            s += 10  # beside the model: what its download came with
        if my_size and sizes(theirs) and not my_size & sizes(theirs):
            s -= 20  # a 4B projector does not fit an 8B model
        if score is None or s > score:
            best, score = m["path"], s
    return best


def _set_opt(key, value):
    from modules import shared

    try:
        shared.opts.set(key, value)
    except Exception:
        setattr(shared.opts, key, value)
    try:
        shared.opts.save(shared.config_filename)
    except Exception:
        pass


def choose(model=None, mmproj=None, memory=None):
    """Settings from Muse's card: the model and its projector (picked for it when not given), where it lives.
    The server starts again with them at its next use."""
    listing = models()
    known = {os.path.normcase(os.path.abspath(i["path"])) for i in listing["models"] + listing["mmprojs"]}
    if model is not None:
        model = str(model)
        if model and os.path.normcase(os.path.abspath(model)) not in known:
            raise ValueError("That model file is not in the list any more: refresh it.")
        _set_opt("pv_vlm_model_path", model)
        if mmproj is None:
            mmproj = mmproj_for(model, listing["mmprojs"])
    if mmproj is not None:
        mmproj = str(mmproj)
        if mmproj and os.path.normcase(os.path.abspath(mmproj)) not in known:
            raise ValueError("That projector file is not in the list any more: refresh it.")
        _set_opt("pv_vlm_mmproj_path", mmproj)
    if memory is not None:
        if memory not in MEMORY_MODES:
            raise ValueError(f"Unknown memory mode {memory!r}")
        _set_opt("pv_vlm_memory", memory)
    if SERVER.running() and getattr(SERVER, "placed", None) != _placement():
        SERVER.stop()  # started again with the new choice when Qwen is next used
    return models()
