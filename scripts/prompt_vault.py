"""Prompt Vault: registers the tab, its settings and the routes its page talks to."""

import os
import sys

from modules import script_callbacks

# lib_vault sits next to scripts/. The WebUI puts the extension on sys.path only while it
# loads this file; the tab's callbacks run long after, so pin it.
EXTENSION_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if EXTENSION_ROOT not in sys.path:
    sys.path.insert(0, EXTENSION_ROOT)

from lib_vault import TAG, api, settings, ui  # noqa: E402

_routes_added = set()


def on_ui_tabs():
    return [(ui.build(), "Prompt Vault", "prompt_vault_tab")]


def on_app_started(_demo, app):
    if id(app) in _routes_added:
        return
    _routes_added.add(id(app))
    try:
        from lib_vault import llama

        llama.reap_leftovers()
    except Exception:
        pass
    try:
        api.register(app)
    except Exception as exc:
        print(f"{TAG} the library routes could not be added: {exc}")


script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(settings.register)
script_callbacks.on_app_started(on_app_started)
