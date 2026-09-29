"""HTTP routes for the tab's JavaScript: the library, saved prompts, history, suggestions.

The tag picker runs in the browser, so the page does not carry thousands of
Gradio components; it reads and changes the library through these routes.
"""

from __future__ import annotations

import time

from . import TAG, store

BASE = "/prompt-vault/api"
_vocab_cache = {"key": None, "data": None}


def _vocab():
    from . import wd14

    lib = store.all_tags()
    try:
        danbooru = wd14.vocabulary()
    except Exception:
        danbooru = []
    key = (len(lib), hash(tuple(lib)), len(danbooru), id(danbooru))
    if _vocab_cache["key"] != key:
        seen, items = set(), []
        for t in lib:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                items.append([t, "vault", 0])
        for t, cat, count in danbooru:
            if t.lower() not in seen:
                seen.add(t.lower())
                items.append([t, cat, count])
        _vocab_cache.update(key=key, data=items)
    return _vocab_cache["data"]


def register(app):
    from fastapi import Body
    from fastapi.responses import JSONResponse, Response

    def run(fn):
        try:
            return JSONResponse(fn())
        except store.VaultError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception as exc:
            print(f"{TAG} {exc}")
            return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)

    @app.get(f"{BASE}/library")
    def get_library():
        return run(store.library_info)

    @app.post(f"{BASE}/library/edit")
    def edit_library(body: dict = Body(...)):
        return run(lambda: store.edit(str(body.get("op", "")), body))

    @app.post(f"{BASE}/library/import")
    def import_library(body: dict = Body(...)):
        return run(lambda: store.import_library(body.get("data"), body.get("mode", "merge")))

    @app.post(f"{BASE}/library/merge-defaults")
    def merge_defaults():
        return run(store.merge_defaults)

    @app.get(f"{BASE}/library/export")
    def export_library():
        import json

        data = json.dumps(store.export_library(), ensure_ascii=False, indent=1)
        name = f"prompt-vault-library-{time.strftime('%Y%m%d')}.json"
        return Response(data, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.get(f"{BASE}/vocab")
    def vocab():
        return run(lambda: {"tags": _vocab()})

    @app.get(f"{BASE}/prompts")
    def get_prompts():
        return run(lambda: {"prompts": store.prompts()})

    @app.post(f"{BASE}/prompts/edit")
    def edit_prompts(body: dict = Body(...)):
        return run(lambda: {"prompts": store.prompt_edit(str(body.get("op", "")), body)})

    @app.get(f"{BASE}/history")
    def get_history():
        return run(lambda: {"history": store.history()})

    @app.post(f"{BASE}/history/add")
    def add_history(body: dict = Body(...)):
        from . import settings

        def add():
            if bool(settings.opt("pv_history")):
                store.add_history(body.get("positive", ""), body.get("negative", ""),
                                  {"tab": str(body.get("tab", ""))[:16]})
            return {"ok": True}

        return run(add)

    @app.post(f"{BASE}/history/clear")
    def clear_history():
        return run(lambda: (store.clear_history(), {"history": []})[1])
