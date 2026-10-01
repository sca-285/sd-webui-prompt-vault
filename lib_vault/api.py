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

    try:
        danbooru = wd14.vocabulary()
    except Exception:
        danbooru = []
    key = (store.revision(), len(danbooru), id(danbooru))
    if _vocab_cache["key"] != key:
        lib = store.all_tags()
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

    # ------------------------------------------------------------------ prompt tools, for the editor and Muse

    def tool(fn):
        result, note = fn()
        if not result:
            raise store.VaultError(note or "nothing came back")
        return {"result": result, "note": note}

    @app.post(f"{BASE}/prompt/arrange")
    def prompt_arrange(body: dict = Body(...)):
        from . import arrange

        parts = body.get("parts") if isinstance(body.get("parts"), list) else None
        return run(lambda: tool(lambda: arrange.arrange(str(body.get("prompt") or ""), parts)))

    @app.post(f"{BASE}/prompt/qwen")
    def prompt_qwen(body: dict = Body(...)):
        from . import qwen

        return run(lambda: tool(lambda: qwen.rewrite(str(body.get("prompt") or ""), str(body.get("task") or ""),
                                                     str(body.get("instruction") or ""))))

    # ------------------------------------------------------------------ Muse

    from . import muse

    @app.get(f"{BASE}/muse")
    def muse_snapshot():
        return run(muse.snapshot)

    @app.post(f"{BASE}/muse/state")
    def muse_state(body: dict = Body(...)):
        return run(lambda: {"state": muse.save_state(body)})

    @app.post(f"{BASE}/muse/next")
    def muse_next(body: dict = Body(None)):
        b = body or {}
        return run(lambda: {"idea": muse.compose(scene_id=b.get("scene"), cast=b.get("cast"),
                                                 keep=b.get("keep"), roll=b.get("roll"))})

    @app.post(f"{BASE}/muse/tipo")
    def muse_tipo(body: dict = Body(...)):
        return run(lambda: muse.expand_with_tipo(str(body.get("positive") or "")))

    @app.get(f"{BASE}/muse/avatar")
    def muse_avatar():
        from fastapi.responses import FileResponse

        path = muse.avatar_file()
        if not path:
            return Response(status_code=404)
        return FileResponse(path, headers={"Cache-Control": "max-age=31536000"})

    @app.post(f"{BASE}/muse/avatar")
    def muse_avatar_set(body: dict = Body(...)):
        return run(lambda: {"avatar": muse.save_avatar(body.get("data"))})

    @app.post(f"{BASE}/muse/avatar/clear")
    def muse_avatar_clear():
        return run(lambda: {"avatar": muse.clear_avatar()})
