"""Get the checkpoint out of VRAM while the vision model is working.

Each fork spells this differently, and one spelling cannot be undone with the
same call:

  A1111 / reForge   unload_model_weights() moves the model to CPU,
                    reload_model_weights() brings it back
  Forge             unload_model_weights() IS memory_management.unload_all_models(),
                    and reload_model_weights() is an empty function
  Forge Classic     unload_model_weights() replaces shared.sd_model with a
  (Neo)             FakeInitialModel and there is no reload_model_weights at all

So on the Forge family this goes straight to the memory manager - the same thing
Forge's own unload does - which frees the VRAM and leaves shared.sd_model alone.
Nothing then has to be put back, and nothing downstream can trip over a
placeholder model while writing infotext.
"""

from __future__ import annotations

import importlib

from modules import shared

LOG = "[Prompt Vault]"


def _memory_manager():
    for path in ("backend.memory_management",              # Forge, Forge Classic
                 "ldm_patched.modules.model_management"):  # reForge
        try:
            return importlib.import_module(path)
        except Exception:
            continue
    return None


def _model_is_real():
    model = getattr(shared, "sd_model", None)
    if model is None:
        return False
    if type(model).__name__ == "FakeInitialModel":
        return False
    return hasattr(model, "use_distilled_cfg_scale") or hasattr(model, "forge_objects")


def release():
    """Free the checkpoint's VRAM. Returns a callable that restores it."""
    try:
        import modules.sd_models as sd_models
    except Exception:
        return lambda: None

    if getattr(shared, "sd_model", None) is None:
        return lambda: None

    try:
        if callable(getattr(sd_models, "reload_model_weights", None)):
            sd_models.unload_model_weights()
            return sd_models.reload_model_weights

        manager = _memory_manager()
        if manager is not None and callable(getattr(manager, "unload_all_models", None)):
            manager.unload_all_models()
            if callable(getattr(manager, "soft_empty_cache", None)):
                manager.soft_empty_cache()
            return restore

        sd_models.unload_model_weights()
        return restore
    except Exception as exc:
        print(f"{LOG} could not free the checkpoint's VRAM: {exc}")
        return restore


def restore():
    """Put a real checkpoint back if one went missing. Cheap when it did not."""
    if _model_is_real():
        return
    try:
        import modules.sd_models as sd_models
    except Exception:
        return
    for name in ("forge_model_reload", "reload_model_weights"):
        fn = getattr(sd_models, name, None)
        if not callable(fn):
            continue
        try:
            fn()
        except Exception as exc:
            print(f"{LOG} {name}() failed: {exc}")
            continue
        if _model_is_real():
            return
    print(f"{LOG} the checkpoint could not be put back; switch checkpoint once to recover.")


def collect():
    try:
        from modules import devices

        devices.torch_gc()
    except Exception:
        pass
