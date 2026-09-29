"""The library, saved prompts and history, on disk.

Everything lives in the data folder (Settings > Prompt Vault), never inside the
extension: updating or reinstalling the extension cannot touch it.

  library.json    categories > groups > tags
  prompts.json    saved prompts (name, positive, negative, a small thumbnail)
  history.json    the prompts of recent generations
  backups/        the library as it was before changes, the last 20

Every write goes to a temporary file first and then replaces the real one, so a
crash or a closed WebUI in the middle of a save leaves the old file whole.
"""

from __future__ import annotations

import copy
import glob
import json
import os
import shutil
import threading
import time
import uuid

from . import TAG, settings, text

EXT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LIBRARY = os.path.join(EXT_ROOT, "data", "default_library.json")
FORMAT = "prompt-vault-library"
KEEP_BACKUPS = 20
BACKUP_EVERY = 300  # seconds: a burst of edits makes one backup, not twenty

_lock = threading.RLock()
_cache = {}


class VaultError(ValueError):
    """A request the library cannot carry out; the message is shown to the user."""


# ------------------------------------------------------------------ files


def _path(name):
    return os.path.join(settings.data_dir(), name)


def _read(path, fallback):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return fallback
    except Exception as exc:
        # keep the unreadable file for the user, never overwrite it silently
        bad = f"{path}.unreadable-{time.strftime('%Y%m%d-%H%M%S')}"
        try:
            shutil.copy2(path, bad)
        except Exception:
            pass
        print(f"{TAG} {os.path.basename(path)} could not be read ({exc}); a copy was kept as {bad}")
        return fallback


def write_json(path, data):
    """Atomic: a temporary file next to the real one, flushed, then swapped in."""
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, f".{os.path.basename(path)}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _backup(path):
    if not os.path.isfile(path):
        return
    folder = os.path.join(os.path.dirname(path), "backups")
    os.makedirs(folder, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    existing = sorted(glob.glob(os.path.join(folder, f"{stem}-*.json")))
    if existing and time.time() - os.path.getmtime(existing[-1]) < BACKUP_EVERY:
        return
    shutil.copy2(path, os.path.join(folder, f"{stem}-{time.strftime('%Y%m%d-%H%M%S')}.json"))
    for old in existing[: max(0, len(existing) + 1 - KEEP_BACKUPS)]:
        try:
            os.remove(old)
        except Exception:
            pass


# ------------------------------------------------------------------ library shape


def normalise(data):
    """Any library we know of -> {category: {group: [tags]}}.

    Takes the current format, the old one (group values as one comma-separated
    string, the file of the first versions) and a bare {category: {group: [..]}}."""
    if isinstance(data, dict) and data.get("format") == FORMAT:
        data = data.get("library", {})
    if not isinstance(data, dict):
        raise VaultError("not a Prompt Vault library")
    out = {}
    for cat, groups in data.items():
        if not isinstance(groups, dict):
            raise VaultError(f"category {cat!r} is not a set of groups")
        out[str(cat).strip()] = {}
        for group, tags in groups.items():
            if isinstance(tags, str):
                tags = text.split(tags)
            elif not isinstance(tags, list):
                raise VaultError(f"group {group!r} holds neither a list nor a string")
            clean = [str(t).strip() for t in tags if str(t).strip()]
            out[str(cat).strip()][str(group).strip()] = list(dict.fromkeys(clean))
    return out


def _wrap(lib):
    return {"format": FORMAT, "version": 2, "library": lib}


def default_library():
    return normalise(_read(DEFAULT_LIBRARY, {}))


def _old_libraries():
    """prompt_vault.json files of the first versions, newest first: they lived inside the
    extension's own folder (sd-reforge-prompt-vault or whatever it was cloned as)."""
    found = glob.glob(os.path.join(settings.extensions_dir(), "*", "prompt_vault.json"))
    found += glob.glob(os.path.join(EXT_ROOT, "prompt_vault.json"))
    return sorted(set(found), key=os.path.getmtime, reverse=True)


def _first_library():
    for path in _old_libraries():
        try:
            lib = normalise(_read(path, None))
        except Exception:
            continue
        if lib:
            print(f"{TAG} library taken over from {path}; that file is left as it was")
            return lib, path
    return default_library(), None


def library():
    """The library, a copy the caller may change."""
    with _lock:
        if _cache.get("dir") != settings.data_dir():  # the folder was changed in Settings
            _cache.clear()
            _cache["dir"] = settings.data_dir()
        if "library" not in _cache:
            path = _path("library.json")
            data = _read(path, None)
            if data is None:
                lib, source = _first_library()
                write_json(path, _wrap(lib))
            else:
                try:
                    lib = normalise(data)
                except VaultError as exc:
                    print(f"{TAG} library.json: {exc}; starting from the default library")
                    lib = default_library()
            _cache["library"] = lib
        return copy.deepcopy(_cache["library"])


def save_library(lib):
    with _lock:
        path = _path("library.json")
        _backup(path)
        write_json(path, _wrap(lib))
        _cache["library"] = copy.deepcopy(lib)


def library_info():
    lib = library()
    cats = []
    for cat, groups in lib.items():
        low = cat.lower()
        cats.append({
            "name": cat,
            "nsfw": "nsfw" in low,
            "negative": "negative" in low,
            "groups": [{"name": g, "tags": tags} for g, tags in groups.items()],
        })
    return {"categories": cats, "count": sum(len(t) for g in lib.values() for t in g.values()),
            "folder": settings.data_dir()}


def all_tags():
    return [t for groups in library().values() for tags in groups.values() for t in tags]


# ------------------------------------------------------------------ library edits


def _need(value, what):
    value = str(value or "").strip()
    if not value:
        raise VaultError(f"{what} is empty")
    return value


def _cat(lib, cat):
    if cat not in lib:
        raise VaultError(f"no category {cat!r}")
    return lib[cat]


def _group(lib, cat, group):
    groups = _cat(lib, cat)
    if group not in groups:
        raise VaultError(f"no group {group!r} in {cat!r}")
    return groups[group]


def _renamed(d, old, new):
    """d with key old renamed to new, in the same place."""
    return {(new if k == old else k): v for k, v in d.items()}


def edit(op, a):
    """One change to the library. Returns what the tab needs to redraw."""
    with _lock:
        lib = library()
        cat, group = str(a.get("category", "")).strip(), str(a.get("group", "")).strip()

        if op == "add_tags":
            tags = _group(lib, cat, group)
            have = {text.key(t) for t in tags}
            added = [t for t in text.split(a.get("tags", "")) if text.key(t) not in have]
            added = list(dict.fromkeys(added))
            if not added:
                raise VaultError("those tags are already in the group")
            tags.extend(added)
        elif op == "remove_tag":
            tags = _group(lib, cat, group)
            tag = a.get("tag")
            if tag not in tags:
                raise VaultError(f"no tag {tag!r} in {group!r}")
            tags.remove(tag)
        elif op == "rename_tag":
            tags = _group(lib, cat, group)
            old, new = a.get("tag"), _need(a.get("new"), "the new tag")
            if old not in tags:
                raise VaultError(f"no tag {old!r} in {group!r}")
            if new != old and new in tags:
                raise VaultError(f"{new!r} is already in the group")
            tags[tags.index(old)] = new
        elif op == "move_tag":
            tags = _group(lib, cat, group)
            tag = a.get("tag")
            if tag not in tags:
                raise VaultError(f"no tag {tag!r} in {group!r}")
            to = _group(lib, str(a.get("to_category", "")).strip(), str(a.get("to_group", "")).strip())
            if to is tags:
                raise VaultError("that is the group it is in")
            tags.remove(tag)
            if tag not in to:
                to.append(tag)
        elif op == "add_group":
            groups = _cat(lib, cat)
            name = _need(a.get("new"), "the group's name")
            if name in groups:
                raise VaultError(f"{cat!r} already has a group {name!r}")
            groups[name] = []
        elif op == "rename_group":
            groups = _cat(lib, cat)
            _group(lib, cat, group)
            new = _need(a.get("new"), "the group's name")
            if new != group and new in groups:
                raise VaultError(f"{cat!r} already has a group {new!r}")
            lib[cat] = _renamed(groups, group, new)
        elif op == "move_group":
            tags = _group(lib, cat, group)
            to_cat = str(a.get("to_category", "")).strip()
            target = _cat(lib, to_cat)
            if to_cat == cat:
                raise VaultError("that is the category it is in")
            if group in target:
                target[group] = list(dict.fromkeys(target[group] + tags))
            else:
                target[group] = tags
            del lib[cat][group]
        elif op == "delete_group":
            _group(lib, cat, group)
            del lib[cat][group]
        elif op == "add_category":
            name = _need(a.get("new"), "the category's name")
            if name in lib:
                raise VaultError(f"there is already a category {name!r}")
            lib[name] = {"General": []}
        elif op == "rename_category":
            _cat(lib, cat)
            new = _need(a.get("new"), "the category's name")
            if new != cat and new in lib:
                raise VaultError(f"there is already a category {new!r}")
            lib = _renamed(lib, cat, new)
        elif op == "delete_category":
            _cat(lib, cat)
            del lib[cat]
        elif op == "move_category":
            _cat(lib, cat)
            names = list(lib)
            i = names.index(cat)
            j = max(0, min(len(names) - 1, i + (1 if a.get("direction") == "down" else -1)))
            names.insert(j, names.pop(i))
            lib = {n: lib[n] for n in names}
        else:
            raise VaultError(f"unknown change {op!r}")

        save_library(lib)
        return library_info()


def import_library(data, mode="merge"):
    incoming = normalise(data)
    with _lock:
        if mode == "replace":
            lib = incoming
        else:
            lib = library()
            _merge_into(lib, incoming)
        save_library(lib)
        return library_info()


def _merge_into(lib, incoming):
    added = 0
    for cat, groups in incoming.items():
        target = lib.setdefault(cat, {})
        for group, tags in groups.items():
            have = target.setdefault(group, [])
            keys = {text.key(t) for t in have}
            for t in tags:
                if text.key(t) not in keys:
                    have.append(t)
                    keys.add(text.key(t))
                    added += 1
    return added


def merge_defaults():
    """Adds what the default library has and yours does not. Removes nothing."""
    with _lock:
        lib = library()
        added = _merge_into(lib, default_library())
        if added:
            save_library(lib)
        info = library_info()
        info["added"] = added
        return info


def export_library():
    return _wrap(library())


# ------------------------------------------------------------------ saved prompts


def prompts():
    with _lock:
        data = _read(_path("prompts.json"), {"version": 1, "prompts": []})
        return list(data.get("prompts", []))


def _save_prompts(items):
    write_json(_path("prompts.json"), {"version": 1, "prompts": items})


def save_prompt(name, positive, negative, thumb=None):
    name = _need(name, "the name")
    if not (positive or "").strip() and not (negative or "").strip():
        raise VaultError("both prompts are empty")
    with _lock:
        items = prompts()
        entry = next((p for p in items if p.get("name") == name), None)
        if entry is None:
            entry = {"id": uuid.uuid4().hex[:12], "name": name, "created": time.time()}
            items.insert(0, entry)
        entry.update(positive=positive or "", negative=negative or "", updated=time.time())
        if thumb:
            entry["thumb"] = thumb
        _save_prompts(items)
        return entry


def prompt_edit(op, a):
    with _lock:
        items = prompts()
        entry = next((p for p in items if p.get("id") == a.get("id")), None)
        if entry is None:
            raise VaultError("that prompt is gone")
        if op == "delete":
            items.remove(entry)
        elif op == "rename":
            new = _need(a.get("new"), "the name")
            if any(p.get("name") == new and p is not entry for p in items):
                raise VaultError(f"there is already a prompt called {new!r}")
            entry["name"] = new
        elif op == "pin":
            items.remove(entry)
            items.insert(0, entry)
        else:
            raise VaultError(f"unknown change {op!r}")
        _save_prompts(items)
        return items


# ------------------------------------------------------------------ history


def history():
    with _lock:
        return list(_read(_path("history.json"), {"history": []}).get("history", []))


def add_history(positive, negative, extra=None):
    positive, negative = (positive or "").strip(), (negative or "").strip()
    if not positive and not negative:
        return
    with _lock:
        items = history()
        if items and items[0].get("positive") == positive and items[0].get("negative") == negative:
            items[0]["time"] = time.time()
            items[0]["count"] = items[0].get("count", 1) + 1
        else:
            entry = {"positive": positive, "negative": negative, "time": time.time(), "count": 1}
            entry.update(extra or {})
            items.insert(0, entry)
        del items[int(settings.opt("pv_history_size")):]
        write_json(_path("history.json"), {"version": 1, "history": items})


def clear_history():
    with _lock:
        write_json(_path("history.json"), {"version": 1, "history": []})
