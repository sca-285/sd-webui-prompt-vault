"""What Prompt Vault holds in memory, told to Memory Keeper (or any extension that reads shared.memory_holders):
the Qwen and TIPO servers and the WD14 tagger, each with its size and a way to let go of it."""

from __future__ import annotations

import os

from . import gguf


def _gpu_estimate(argv):
    """Bytes of a llama-server's model on the GPU, from how it was started (the driver's own number is better,
    when nvidia-smi can give it)."""
    def arg(flag):
        return argv[argv.index(flag) + 1] if flag in argv[:-1] else None

    model, mmproj = arg("-m"), arg("--mmproj")
    try:
        size = os.path.getsize(model)
    except Exception:
        return None
    try:
        ngl = int(arg("-ngl") or 99)
    except ValueError:
        ngl = 99
    layers = gguf.info(model)["layers"] or 40
    share = 0.15 if "--cpu-moe" in argv else min(1.0, ngl / layers)
    gpu = size * share
    if mmproj and "--no-mmproj-offload" not in argv and ngl > 0:
        try:
            gpu += os.path.getsize(mmproj)
        except Exception:
            pass
    if "--no-kv-offload" not in argv and ngl > 0:
        gpu += int(arg("-c") or 4096) * 0.14 / 1024 * 1024 ** 3  # the context, roughly
    return int(gpu)


def _server(holder_id, name, server, what):
    def usage():
        if not server.running():
            return None
        return {"vram": _gpu_estimate(getattr(server, "argv", []) or []), "ram": None}

    def detail():
        model = os.path.basename(server.model or "") if server.running() else ""
        return f"{what}: {model}" + (", stopped when let go, started again when used" if model else "")

    return {"id": holder_id, "name": name, "category": "llm", "source": "Prompt Vault", "kind": "process", "usage": usage, "detail": detail,
            "pid": lambda: server.proc.pid if server.running() and server.proc is not None else None, "unload": server.stop}


def _wd14():
    from . import wd14

    def usage():
        session = wd14._state.get("session")
        if session is None:
            return None
        try:
            size = os.path.getsize(session._model_path) if getattr(session, "_model_path", None) else None
        except Exception:
            size = None
        on_gpu = any(p != "CPUExecutionProvider" for p in session.get_providers()[:1])
        return {"vram": size if on_gpu else 0, "ram": None if on_gpu else size}

    return {"id": "prompt_vault.wd14", "name": "WD14 tagger", "category": "tagger", "source": "Prompt Vault", "kind": "model",
            "usage": usage,
            "detail": "Image → Prompt's tagger, loaded again when used", "unload": wd14.unload}


def register():
    """Into shared.memory_holders; Memory Keeper reads it, whichever of the two the WebUI loads first."""
    try:
        from modules import shared
    except Exception:
        return
    from . import qwen, tipo

    holders = getattr(shared, "memory_holders", None)
    if not isinstance(holders, list):
        holders = shared.memory_holders = []
    mine = [_server("prompt_vault.qwen", "Qwen (llama-server)", qwen.SERVER, "Qwen chat and vision"),
            _server("prompt_vault.tipo", "TIPO (llama-server)", tipo.SERVER, "TIPO prompt writer"), _wd14()]
    holders[:] = [h for h in holders if not str(h.get("id", "")).startswith("prompt_vault.")] + mine
