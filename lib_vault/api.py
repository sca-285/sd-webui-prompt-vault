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

    @app.post(f"{BASE}/prompts/save")
    def save_prompt(body: dict = Body(...)):
        return run(lambda: {"entry": store.save_prompt(str(body.get("name") or ""), str(body.get("positive") or ""),
                                                       str(body.get("negative") or ""))})

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

    # ---------------------------------------------------------------- Qwen: which model, where it lives
    @app.get(f"{BASE}/qwen/models")
    def qwen_models():
        from . import qwen

        return run(qwen.models)

    @app.post(f"{BASE}/qwen/models")
    def qwen_choose(body: dict = Body(...)):
        from . import qwen

        def go():
            try:
                return qwen.choose(body.get("model"), body.get("mmproj"), body.get("memory"), body.get("think"))
            except ValueError as exc:
                raise store.VaultError(str(exc))
        return run(go)

    @app.post(f"{BASE}/qwen/folders")
    def qwen_folders(body: dict = Body(...)):
        from . import qwen

        def go():
            try:
                return qwen.set_folders(body.get("qwen_dirs"), body.get("models_dir"))
            except ValueError as exc:
                raise store.VaultError(str(exc))
        return run(go)

    # ---------------------------------------------------------------- Qwen Chat
    from . import chat

    def stream(make):
        """The model's answer as it comes: one JSON object a line."""
        import json as _json

        from fastapi.responses import StreamingResponse

        try:
            events = make()
        except store.VaultError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        except Exception as exc:
            print(f"{TAG} {exc}")
            return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)
        return StreamingResponse((_json.dumps(e, ensure_ascii=False) + "\n" for e in events), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get(f"{BASE}/chat")
    def chat_list():
        return run(chat.listing)

    @app.get(f"{BASE}/chat/one")
    def chat_one(id: str = ""):
        return run(lambda: {"chat": chat.get(id)})

    @app.post(f"{BASE}/chat/new")
    def chat_new(body: dict = Body(None)):
        return run(lambda: {"chat": chat.new((body or {}).get("system"))})

    @app.post(f"{BASE}/chat/send")
    def chat_send(body: dict = Body(...)):
        return stream(lambda: chat.send(body.get("id"), body.get("text"), body.get("files"), body.get("context") or ""))

    @app.post(f"{BASE}/chat/regenerate")
    def chat_regenerate(body: dict = Body(...)):
        return stream(lambda: chat.send(body.get("id"), "", regenerate=True, again=body.get("message")))

    @app.post(f"{BASE}/chat/edit")
    def chat_edit(body: dict = Body(...)):
        return stream(lambda: chat.send(body.get("id"), body.get("text"), body.get("files"), edit=body.get("message")))

    @app.post(f"{BASE}/chat/version")
    def chat_version(body: dict = Body(...)):
        return run(lambda: {"chat": chat.switch(body.get("id"), body.get("message"), body.get("step") or 1)})

    @app.post(f"{BASE}/chat/stop")
    def chat_stop(body: dict = Body(...)):
        return run(lambda: chat.stop(body.get("id")))

    @app.post(f"{BASE}/chat/update")
    def chat_update(body: dict = Body(...)):
        return run(lambda: {"chat": chat.update(body.get("id"), body.get("title"), body.get("system"))})

    @app.post(f"{BASE}/chat/remove-message")
    def chat_remove_message(body: dict = Body(...)):
        return run(lambda: {"chat": chat.remove_message(body.get("id"), body.get("message"))})

    @app.post(f"{BASE}/chat/delete")
    def chat_delete(body: dict = Body(...)):
        return run(lambda: chat.delete(body.get("id")))

    @app.post(f"{BASE}/chat/save")
    def chat_save(body: dict = Body(...)):
        return run(lambda: {"chat": chat.save(body.get("id"))})

    @app.post(f"{BASE}/chat/unsave")
    def chat_unsave(body: dict = Body(...)):
        return run(lambda: {"chat": chat.unsave(body.get("id"))})

    @app.post(f"{BASE}/chat/open")
    def chat_open(body: dict = Body(...)):
        return run(lambda: {"chat": chat.open_saved(body.get("name"))})

    @app.post(f"{BASE}/chat/saved/delete")
    def chat_saved_delete(body: dict = Body(...)):
        return run(lambda: chat.delete_saved(body.get("name")))

    @app.post(f"{BASE}/chat/import")
    def chat_import(body: dict = Body(...)):
        return run(lambda: {"chat": chat.import_data(body.get("data"))})

    @app.get(f"{BASE}/chat/export")
    def chat_export(id: str = "", fmt: str = "md"):
        return run(lambda: chat.export(id, fmt))

    @app.post(f"{BASE}/muse/state")
    def muse_state(body: dict = Body(...)):
        return run(lambda: {"state": muse.save_state(body)})

    @app.post(f"{BASE}/muse/next")
    def muse_next(body: dict = Body(None)):
        b = body or {}
        return run(lambda: {"idea": muse.compose(scene_id=b.get("scene"), cast=b.get("cast"),
                                                 keep=b.get("keep"), roll=b.get("roll"),
                                                 size=b.get("size"), girls=b.get("girls"), avoid=b.get("avoid"))})

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
