"""TIPO prompt expansion, run by llama-server.

TIPO (KohakuBlueLeaf, https://github.com/KohakuBlueleaf/KGen) is a small model
trained to turn a few tags or a short sentence into a full prompt: more tags,
natural-language sentences, or both. The request format, the parsing of the
answer and the retry rules below follow KGen's TIPO executor (Apache-2.0, see
NOTICE.md); only the generation goes to llama-server's /completion instead of
llama-cpp-python or transformers, so nothing has to be installed or compiled.
"""

from __future__ import annotations

import fnmatch
import glob
import importlib.util
import os
import random
import re
import time

from . import TAG, download, llama, settings, text

EXT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUTS = ["Tags", "Natural language", "Tags + natural language"]
LENGTHS = ["very short", "short", "long", "very long"]

SPECIAL = ["1girl", "2girls", "3girls", "4girls", "5girls", "6+girls", "multiple girls", "1boy", "2boys", "3boys",
           "4boys", "5boys", "6+boys", "multiple boys", "male focus", "1other", "2others", "3others", "4others",
           "5others", "6+others", "multiple others"]
QUALITY = ["masterpiece", "best quality", "great quality", "good quality", "normal quality", "low quality",
           "worse quality", "very aesthetic", "aesthetic", "displeasing", "very displeasing", "newest", "recent",
           "mid", "early", "old", "score_9", "score_8_up", "score_7_up", "score_6_up", "score_5_up", "score_4_up",
           "source_anime", "source_cartoon", "source_furry", "source_pony"]
RATING = ["safe", "general", "sfw", "sensitive", "nsfw", "explicit"]

TARGET_TIPO = {"very_short": 6, "short": 18, "long": 36, "very_long": 54}
TARGET_TIPO_MAX = {"very_short": 18, "short": 36, "long": 54, "very_long": 72}
TARGET_TIPO_NL = {"very_short": 1, "short": 2, "long": 4, "very_long": 8}
TARGET_TIPO_NL_MAX = {"very_short": 2, "short": 4, "long": 8, "very_long": 10000}

FORMATS = {
    "Tags": "<|special|>, <|characters|>, <|copyrights|>,\n<|artist|>,\n\n<|general|>,\n\n<|quality|>, <|meta|>, <|rating|>",
    "Natural language": "<|extended|>.",
    "Tags + natural language": "<|special|>, <|characters|>, <|copyrights|>,\n<|artist|>,\n\n<|general|>,\n\n"
                               "<|extended|>.\n\n<|quality|>, <|meta|>, <|rating|>",
}

# ------------------------------------------------------------------ tag categories

_lists = None


def _tag_lists():
    """Which tags are characters, artists, copyrights or meta. KGen's full lists when
    tipo-kgen is installed (z-tipo-extension brings it), otherwise the meta list that
    ships here and the character tags of a downloaded WD14 model. Unknown tags count as
    general, which only changes where they land in the output."""
    global _lists
    if _lists is not None:
        return _lists
    lists = {}
    try:
        spec = importlib.util.find_spec("kgen")
        folder = os.path.join(os.path.dirname(spec.origin), "tag-list") if spec and spec.origin else None
        if folder and os.path.isdir(folder):
            for f in os.listdir(folder):
                if f.endswith(".txt"):
                    with open(os.path.join(folder, f), encoding="utf-8") as fh:
                        lists[os.path.splitext(f)[0]] = set(fh.read().strip().split("\n"))
    except Exception:
        pass
    if "meta" not in lists:
        try:
            with open(os.path.join(EXT_ROOT, "data", "tipo_meta_tags.txt"), encoding="utf-8") as fh:
                lists["meta"] = set(fh.read().strip().split("\n"))
        except Exception:
            lists["meta"] = set()
    if "characters" not in lists:
        try:
            from . import wd14

            lists["characters"] = {t for t, cat, _ in wd14.vocabulary() if cat == "character"}
        except Exception:
            pass
    lists["special"] = set(SPECIAL)
    lists["quality"] = set(QUALITY)
    lists["rating"] = set(RATING)
    _lists = lists
    return lists


def separate_tags(all_tags):
    lists = _tag_lists()
    tag_map = {cat: [] for cat in lists}
    tag_map["general"] = []
    for tag in (t.strip() for t in all_tags):
        if not tag:
            continue
        for cat, names in lists.items():
            if tag in names:
                tag_map[cat].append(tag)
                break
            if tag.replace("_", " ") in names:
                tag_map[cat].append(tag.replace("_", " "))
                break
        else:
            tag_map["general"].append(tag if len(tag) < 4 else tag.replace("_", " "))
    return tag_map


def apply_format(tag_map, form):
    if "<|extended|>" in form and not tag_map.get("extended", ""):
        form = form.replace("<|extended|>", "<|generated|>")
    for kind, value in tag_map.items():
        if f"<|{kind}|>" in form:
            if not value:
                form = form.replace(f"<|{kind}|>,", "").replace(f"<|{kind}|>", "")
            else:
                form = form.replace(f"<|{kind}|>", ", ".join(value) if isinstance(value, list) else value)
    form = re.sub(r"<\|(?:(?!<\|.*\|>).)*\|>", "", form)
    form = re.sub(r"\s*\n\s*", " ", form)
    form = re.sub(r"(?:,\s*)+,", ",", form)
    form = re.sub(r"\s{2,}", " ", form)
    return form.strip().strip(",").strip()


# ------------------------------------------------------------------ the TIPO request


def apply_tipo_prompt(meta, general, nl_prompt, mode, length, expand, gen_meta=False):
    content = {"tag": general}
    if nl_prompt and (mode is None or "short" not in mode):
        content["long"] = nl_prompt
    elif nl_prompt:
        content["short"] = nl_prompt
    prompt, target = "", ""
    for k, v in meta.items():
        if v:
            prompt += f"{k}: {v}\n"
    if length:
        target += f"<|{length}|>"
    if mode:
        order = mode.split("_to_")
        target += f" <|{mode}|>"
    else:
        order = ["tag"]
    if gen_meta:
        target += " <|gen_meta|>"
    prompt += f"target: {target.strip()}\n"
    k = "tag"
    for idx, k in enumerate(order):
        if k in content and content[k].strip():
            prompt += f"{k}: {content[k]}\n"
        elif idx < len(order) - 1:
            prompt += f"{k}: \n"
    return prompt.strip() if expand else prompt + f"{k}:"


_PARSE = re.compile(r"\n([^:\n]+):(.*(?:\n(?![^:\n]+:).*)*)")
_TYPE_MAP = {"short": "extended", "long": "generated"}


def parse_tipo_result(result):
    result = "\n" + result.replace("<s>", "").replace("</s>", "").strip()
    out = {}
    for kind, content in _PARSE.findall(result):
        kind, content = kind.strip(), content.strip()
        if _TYPE_MAP.get(kind, kind) in out:
            continue
        if kind == "tag":
            tags = [t.strip() for t in content.split(",") if t.strip()]
            for k, v in separate_tags(tags).items():
                v = [t for t in v if t]
                if k in out:
                    if not isinstance(out[k], list):
                        out[k] = [out[k]]
                    out[k].extend(v)
                else:
                    out[k] = v
            out["tag"] = tags
        elif kind not in {"short", "long"}:
            out[_TYPE_MAP.get(kind, kind)] = [t.strip() for t in content.split(",") if t.strip()]
        elif content and content != "<|empty|>":
            out[_TYPE_MAP.get(kind, kind)] = content
    return out


def parse_request(tag_map, nl_prompt, expand_tags, expand_prompt, extra_nl, tag_length, nl_length):
    general = ", ".join(tag_map.get("special", []) + tag_map.get("general", [])).strip().strip(",")
    meta = {
        "meta": ", ".join(tag_map.get("meta", [])),
        "rating": ", ".join(tag_map.get("rating", [])) or None,
        "artist": ", ".join(tag_map.get("artist", [])).strip() or None,
        "characters": ", ".join(tag_map.get("characters", [])).strip() or None,
        "copyrights": ", ".join(tag_map.get("copyrights", [])).strip() or None,
        "quality": ", ".join(tag_map.get("quality", [])),
    }
    ops, nl_op = [], None
    g, n = general.strip(), nl_prompt.strip()
    if not g and not n:
        ops, nl_op = [[None, tag_length, True]], ["tag_to_long", nl_length, True]
    elif not n:
        ops = [[None, tag_length, True]] if expand_tags else []
        nl_op = ["tag_to_long", nl_length, False]
    elif not g:
        ops, nl_op = [["long_to_tag", tag_length, expand_prompt]], ["short_to_tag_to_long", nl_length, False]
    elif not expand_tags and not expand_prompt:
        nl_op = ["short_to_tag_to_long", nl_length, False]
    elif expand_tags and not expand_prompt:
        ops = [["short_to_tag", tag_length, True], ["short_to_tag_to_long", nl_length, False]]
        nl_op = ["short_to_tag_to_long", nl_length, False]
    elif not expand_tags and expand_prompt:
        ops = [["tag_to_long", tag_length, True], ["tag_to_short_to_long", nl_length, False]]
        nl_op = ["tag_to_short_to_long", nl_length, False]
    else:
        ops = [["short_to_tag", tag_length, True], ["tag_to_long", nl_length, True]]
        nl_op = ["short_to_tag_to_long", nl_length, False]
    if extra_nl:
        ops.append(nl_op)
    return meta, ops, general, nl_prompt


def _dedupe(items):
    return list(dict.fromkeys(items))


def post_process(parsed, general, nl_prompt, mode, length, banned, rng):
    if mode is None:
        parsed.pop("extended", None)
        parsed.pop("generated", None)
    else:
        if "long" not in mode:
            parsed.pop("generated", None)
        if "short" not in mode:
            parsed.pop("extended", None)
    if "generated" in parsed and nl_prompt and not parsed.get("extended", "").strip():
        parsed["extended"] = parsed.pop("generated")
    input_tags = [t.strip() for t in general.split(",")]
    input_nl = [t.strip() for t in nl_prompt.split(".") if t.strip()]

    for k, v in list(parsed.items()):
        if isinstance(v, list):
            parsed[k] = [t for t in v if not banned(t)]

    in_general = [t for t in parsed.get("general", []) if t in input_tags]
    out_general = [t for t in parsed.get("general", []) if t not in input_tags]
    rng.shuffle(out_general)
    out_nl = [t.strip() for t in parsed.get("extended", "").split(".") if t.strip() and t.strip() not in input_nl]
    if out_nl and input_nl and input_nl[-1] in out_nl[0]:
        input_nl[-1] = out_nl.pop(0)
    if out_nl:
        head = out_nl[:-1]
        rng.shuffle(head)
        out_nl = head + [out_nl[-1]]

    if len(in_general) + len(out_general) > TARGET_TIPO_MAX[length]:
        out_general = out_general[: max(TARGET_TIPO_MAX[length] - len(in_general), 0)]
    if len(input_nl) + len(out_nl) > TARGET_TIPO_NL_MAX[length]:
        out_nl = out_nl[: max(TARGET_TIPO_NL_MAX[length] - len(input_nl), 0)]
    generated = []
    if "generated" in parsed:
        generated = [t.strip() for t in parsed["generated"].split(".") if t.strip() and t.strip() not in input_nl]
        generated = generated[: TARGET_TIPO_NL_MAX[length]]

    parsed["general"] = _dedupe(in_general + out_general)
    parsed["extended"] = ". ".join(_dedupe(input_nl + out_nl))
    if generated:
        parsed["generated"] = ". ".join(_dedupe(generated))
    return parsed


def _long_enough(parsed, target, length):
    checks = {
        "tag": len(parsed.get("special", []) + parsed.get("general", [])) >= TARGET_TIPO[length],
        "short": len(parsed.get("extended", "").split(".")) >= TARGET_TIPO_NL[length],
        "long": len(parsed.get("generated", "").split(".")) >= TARGET_TIPO_NL[length],
    }
    return checks.get(target, all(checks.values()))


# ------------------------------------------------------------------ model and server


def _kgen_model_dirs():
    dirs = [os.path.join(settings.webui_models_dir(), "kgen")]
    try:
        spec = importlib.util.find_spec("kgen")
        if spec and spec.origin:
            dirs.append(os.path.join(os.path.dirname(spec.origin), "models"))
    except Exception:
        pass
    return dirs


def model_path(fetch=True):
    """The .gguf to run: the custom one, one already downloaded (by this extension or by
    z-tipo-extension), or a fresh download."""
    choice = settings.opt("pv_tipo_model")
    if choice == settings.TIPO_CUSTOM or choice not in settings.TIPO_MODELS:
        return settings.clean_path(settings.opt("pv_tipo_model_path")) or None
    repo, filename = settings.TIPO_MODELS[choice]
    ours = os.path.join(settings.models_dir("tipo"), filename)
    if os.path.isfile(ours):
        return ours
    for folder in _kgen_model_dirs():
        candidate = os.path.join(folder, f"{repo.split('/')[-1]}_{filename}")
        if os.path.isfile(candidate):
            return candidate
    for candidate in glob.glob(os.path.join(settings.models_dir("tipo"), "**", filename), recursive=True):
        return candidate
    if not fetch:
        return None
    return download.fetch(repo, filename, ours)


def _missing():
    problems = llama.server_missing()
    if settings.opt("pv_tipo_model") == settings.TIPO_CUSTOM:
        path = settings.clean_path(settings.opt("pv_tipo_model_path"))
        if not path:
            problems.append("the custom TIPO .gguf is not set")
        elif not os.path.isfile(path):
            problems.append(f"TIPO model not found: {path}")
    return problems


def _model_args():
    return ["-m", model_path(fetch=True), "-c", "2048"]


SERVER = llama.LlamaServer("TIPO", "pv_tipo_port", "pv_tipo_idle_minutes", _model_args, _missing,
                           "pv_tipo_extra_args", "pv_tipo_gpu_layers")


def _generate(prompt, seed, temperature):
    answer = SERVER.post("/completion", {
        "prompt": prompt,
        "n_predict": 512,
        "temperature": float(temperature),
        "top_p": 0.95,
        "top_k": 60,
        "min_p": 0.1,
        "repeat_penalty": 1.17,
        "seed": int(seed) % (2 ** 32),
        "cache_prompt": False,
    }, timeout=180)
    return prompt + str(answer.get("content", ""))


# ------------------------------------------------------------------ public


def _banned_test(ban):
    rules = [b.strip().lower() for b in text.split(ban or "") if b.strip()]

    def banned(tag):
        t = tag.lower()
        return any((fnmatch.fnmatch(t, r) if any(c in r for c in "*?[") else r in t) for r in rules)

    return banned


def expand(prompt, output="Tags + natural language", length="long", ban="", seed=-1, temperature=0.35):
    """(new prompt, note). The prompt may be tags, sentences or both; LoRAs, weights and
    BREAK are kept aside and put back in front."""
    started = time.time()
    try:
        pieces = text.split(prompt or "")
        kept = [p for p in pieces if text.is_special(p)]
        rest = [p for p in pieces if not text.is_special(p)]
        sentences = [p.strip().rstrip(".") for p in rest if text.looks_like_sentence(p)]
        tags = [p for p in rest if not text.looks_like_sentence(p)]
        nl_prompt = ". ".join(sentences)
        length = str(length or "long").replace(" ", "_")
        if length not in TARGET_TIPO:
            length = "long"
        if output not in FORMATS:
            output = "Tags + natural language"
        seed = int(seed) if seed is not None and int(seed) >= 0 else random.randint(0, 2 ** 31)
        rng = random.Random(seed)
        banned = _banned_test(ban)

        SERVER.restart_if_model_changed(model_path(fetch=False))
        tag_map = separate_tags(tags)
        want_nl = output != "Tags"
        meta, ops, general, nl = parse_request(
            tag_map, nl_prompt, expand_tags=True, expand_prompt=want_nl, extra_nl=want_nl,
            tag_length=length, nl_length=length if length != "very_long" else "long",
        )
        passes, parsed = 0, {}
        for idx, (mode, op_length, do_expand) in enumerate(ops):
            target = mode.split("_to_")[-1] if mode else "tag"
            attempt_general, attempt_nl = general, nl
            seen, same = set(), 0
            for attempt in range(4):
                request = apply_tipo_prompt(meta, attempt_general, attempt_nl, mode, op_length, do_expand)
                result = _generate(request, seed + passes, temperature)
                passes += 1
                parsed = post_process(parse_tipo_result(result), attempt_general, attempt_nl, mode, op_length,
                                      banned, rng)
                if target == "long" and "generated" not in parsed:
                    target = "short"
                if _long_enough(parsed, target, op_length):
                    break
                same = same + 1 if result in seen else 0
                seen.add(result)
                if same >= 2:
                    break
                attempt_nl = (parsed.get("extended") or parsed.get("generated") or attempt_nl).strip()
                attempt_general = ", ".join(parsed.get("special", []) + parsed.get("general", []))
            if idx < len(ops) - 1:
                if "generated" in parsed and nl:
                    parsed["extended"] = parsed.pop("generated")
                nl = (parsed.get("generated") or parsed.get("extended") or nl).strip()
                general = ", ".join(parsed.get("special", []) + parsed.get("general", []))

        # the input's own tags that TIPO does not echo (quality, rating...) stay in
        for k in ("quality", "meta", "rating", "characters", "copyrights", "artist"):
            if tag_map.get(k) and not parsed.get(k):
                parsed[k] = tag_map[k]
        result = apply_format(parsed, FORMATS[output])
        if output == "Tags" and sentences:
            # tags were asked for, but the user's own sentences are not TIPO's to drop
            result = f"{result}, {'. '.join(sentences)}." if result else f"{'. '.join(sentences)}."
        if not result:
            return "", "TIPO: nothing usable came back"
        if kept:
            result = f"{text.join(kept)}, {result}"
        return result, f"TIPO: seed {seed}, {passes} passes, {time.time() - started:.1f}s"
    except Exception as exc:
        print(f"{TAG} TIPO failed: {exc}")
        return "", f"TIPO: {exc}"
