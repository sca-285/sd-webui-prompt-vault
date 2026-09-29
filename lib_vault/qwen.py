"""Qwen-VL through llama-server: read an image, or rewrite a prompt.

The server speaks the OpenAI chat-completions shape (so do LM Studio, Ollama and
KoboldCpp). Qwen-VL is a full chat model, so the same server that reads images
also rewrites and translates prompts: no second model to download.
"""

from __future__ import annotations

import base64
import io
import os
import time

from . import llama, settings, text, vram
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


def _model_args():
    return ["-m", settings.clean_path(settings.opt("pv_vlm_model_path")),
            "--mmproj", settings.clean_path(settings.opt("pv_vlm_mmproj_path")),
            "-c", str(int(settings.opt("pv_vlm_context")))]


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
    SERVER.restart_if_model_changed(settings.clean_path(settings.opt("pv_vlm_model_path")))
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
