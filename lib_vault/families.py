"""Which family a .gguf belongs to (Qwen, Gemma, Mistral, GLM, Llama, Phi), told by what the file says about itself, and
what each family is best run with. The Vault tab's chat and vision model can be any of them; llama-server reads each
one's own chat template from the file.

The sampling values are the ones the families' model cards recommend; Settings → Prompt Vault → Sampling can use
your own instead."""

from __future__ import annotations

import os
import re

from . import gguf

# key, label, the words that tell it (in the architecture, the projector kind, the model's name or the file's name),
# its recommended sampling, and whether its template takes enable_thinking
FAMILIES = (
    ("qwen", "Qwen", ("qwen",), {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0}, True),
    ("gemma", "Gemma", ("gemma",), {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "min_p": 0.0}, False),
    ("mistral", "Mistral", ("mistral", "pixtral", "ministral", "magistral", "devstral"), {"temperature": 0.15, "top_p": 1.0, "min_p": 0.0}, False),
    ("glm", "GLM", ("glm",), {"temperature": 0.6, "top_p": 0.95, "min_p": 0.0}, True),
    ("llama", "Llama", ("llama",), {"temperature": 0.6, "top_p": 0.9, "min_p": 0.0}, False),
    ("phi", "Phi", ("phi",), {"temperature": 0.7, "top_p": 0.95, "min_p": 0.0}, False),
)
KEYS = tuple(f[0] for f in FAMILIES)


def _tell(*texts):
    words = " ".join(str(t or "").lower() for t in texts)
    for key, _label, marks, _sampling, _think in FAMILIES:  # Mistral before Llama: Mistral Small's text part is a "llama"
        if any(re.search(r"(?<![a-z])" + m, words) for m in marks):
            return key
    return ""


def of_model(path):
    """The family of a model file, or "" when it cannot be told."""
    info = gguf.info(path) if path and os.path.isfile(path) else {}
    return _tell(info.get("name"), info.get("basename"), os.path.basename(path or ""), info.get("arch"))


def of_projector(path):
    """The family a vision projector (mmproj) was made for, from its projector kind, else its name."""
    info = gguf.info(path) if path and os.path.isfile(path) else {}
    return _tell(info.get("projector")) or _tell(info.get("name"), os.path.basename(path or ""))


def label(key):
    return next((f[1] for f in FAMILIES if f[0] == key), "")


def sampling(key):
    """The recommended sampling of a family ({} for one not known)."""
    return dict(next((f[3] for f in FAMILIES if f[0] == key), {}))


def thinks(key):
    """Whether the family's chat template takes enable_thinking (Qwen3, GLM-4.5…); the others ignore it."""
    return next((f[4] for f in FAMILIES if f[0] == key), False)


def model_name(path):
    """A short name for the model, as it calls itself: Gemma 3 12B It Abliterated, else from the file name."""
    info = gguf.info(path) if path and os.path.isfile(path) else {}
    name = (info.get("name") or info.get("basename") or "").strip()
    if not name:
        stem = os.path.splitext(os.path.basename(path or ""))[0]
        name = re.sub(r"[-_.](i?q\d\w*|f16|bf16|f32|gguf)$", "", stem, flags=re.I)
    return re.sub(r"[-_]+", " ", name)[:60]
