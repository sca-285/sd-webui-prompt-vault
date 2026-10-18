"""🔎 Verify: the model drafts an answer, picks what in it could be wrong (and the checkpoints or LoRAs it names), that
is looked up (the web, the pages themselves, Civitai, Danbooru for the tags of its prompts), and the answer the user
reads is written again from what was found, citing it."""

from __future__ import annotations

import json
import re

from . import chat, settings, websearch

ROOM = 3600        # tokens kept free for the draft and what was found
EVIDENCE = 7000    # characters of what was found that go to the model
PLAN_SYSTEM = (
    "You check an answer before it is given. Read the user's message and the draft answer, and pick what in the draft "
    "could be wrong, made up or out of date and can be checked on the web: names, numbers, dates, versions, model and "
    "software settings, facts about people, places, works and events. Reply with JSON only, no other words: "
    "{\"queries\": [\"...\"], \"models\": [\"...\"]}. queries: at most 3 short web search queries in English, the "
    "most doubtful first, each about one point and with the names spelled out (\"Illustrious XL recommended CFG\", "
    "not \"best settings\"). models: at most 2 names of checkpoints or LoRAs to look up on Civitai, as they are called "
    "(\"Illustrious XL\", \"Pony Diffusion V6 XL\"). Leave both empty when nothing needs checking: opinions, fiction, "
    "a plain prompt, small talk."
)
REVISE = (
    "Before your answer reaches the user, it was checked. Below is what the web says about it (passages of the pages "
    "themselves, and Civitai's pages of the models), and which of its tags are not Danbooru tags. Now write the answer "
    "the user will read. Where the sources and your answer disagree, the sources win: correct the point, and drop "
    "what they show is made up. Keep what they confirm or do not touch, add what they add when it matters, replace a "
    "tag that does not exist with a suggested one or leave it out. When the sources do not settle a point, say it is "
    "uncertain rather than guess. Cite a source as [n] where you used it. Answer the user's last message directly, in "
    "the same language and form as your draft; do not mention a draft, a check or this message.\n\n"
)
# signs that a question asks for facts, so it is looked up even when a small model plans nothing
FACTUAL = re.compile(
    r"\d|\b(v\d|xl|sdxl|sd ?1\.5|flux|pony|illustrious|noobai|lora|lycoris|checkpoint|model|sampler|scheduler|cfg|"
    r"steps|denois\w*|upscal\w*|hires|controlnet|vae|version|release\w*|who|what|which|when|where|how many|how much|"
    r"latest|newest|recommend\w*|best|vs|versus|difference)\b", re.I)


def code_tags(text):
    """The tags of the prompts (code blocks of comma-separated words) in an answer."""
    tags = []
    for block in re.findall(r"```[\w-]*\n?(.*?)```", str(text or ""), re.S):
        if block.count(",") < 2:
            continue
        for tag in re.split(r"[,\n]+", block):
            tag = tag.strip()
            if tag and tag not in tags:
                tags.append(tag)
    return tags[:80]


def _plan(plan):
    """(queries, models) from the plan's JSON."""
    found = re.search(r"\{.*\}", plan or "", re.S)
    try:
        data = json.loads(found.group(0)) if found else {}
    except Exception:
        data = {}
    def clean(items, n):
        items = items if isinstance(items, list) else []
        return [str(q).strip()[:120] for q in items if str(q).strip()][:n]
    return clean(data.get("queries"), 3), clean(data.get("models"), 2)


def _question_query(question):
    """The question itself as a search, when it asks for facts: its first line, without greetings and markup."""
    line = re.sub(r"```.*?```", " ", question or "", flags=re.S)
    line = re.sub(r"\s+", " ", line).strip()
    return line[:120] if line and FACTUAL.search(line) and len(line.split()) >= 2 else ""


def run(messages, max_tokens, stop):
    """Steps for the page while the model drafts, the draft is looked up (the web, the pages read, Civitai) and the tags
    are checked. Returns (the messages to write the corrected answer from, or None when nothing was found to correct
    with, and what was done)."""
    done = {"queries": [], "models": [], "sources": [], "tags": [], "problems": []}
    yield {"step": "Writing a first draft…"}
    draft = chat._complete(messages, max_tokens)
    done["draft"] = draft
    if stop.is_set():
        return None, done
    yield {"step": "Choosing what to check…"}
    question = chat._words_of(messages[-1]["content"]) if messages else ""
    try:
        done["queries"], done["models"] = _plan(chat._complete(
            [{"role": "system", "content": PLAN_SYSTEM},
             {"role": "user", "content": f"The user's message:\n{question[:3000]}\n\nThe draft:\n{draft[:5000]}"}], 300))
    except Exception as exc:
        done["problems"].append(f"planning: {exc}")
    if not done["queries"] and not done["models"]:
        fallback = _question_query(question)
        if fallback:
            done["queries"] = [fallback]
    searching = str(settings.opt("pv_search_engine") or "Auto") != "Off"
    sources, seen, words = [], set(), websearch.terms(question, *done["queries"])

    def keep(items):
        for item in items:
            if item.get("url") and item["url"] not in seen:
                seen.add(item["url"])
                sources.append(item)

    found_web = []
    for query in done["queries"] if searching else []:
        if stop.is_set():
            break
        yield {"step": f"Searching: {query}"}
        found, problems = websearch.search_all(query, 5)
        done["problems"] += [p for p in problems if p not in done["problems"]]
        if not found:
            try:
                found = websearch.wikipedia(query, 2)
            except Exception as exc:
                done["problems"].append(f"Wikipedia: {exc}")
        found_web += [dict(f, rank=i) for i, f in enumerate(found) if f.get("url") not in {x.get("url") for x in found_web}]
    if found_web and settings.opt("pv_search_read_pages") and not stop.is_set():
        found_web.sort(key=lambda f: f["rank"])  # the best result of each search first, then the rest
        yield {"step": f"Reading {min(3, len(found_web))} pages…"}
        try:
            found_web = websearch.read_results(found_web, words, pages=3)
        except Exception as exc:
            done["problems"].append(f"reading pages: {exc}")
    keep(found_web)
    if searching and settings.opt("pv_search_civitai"):
        for name in done["models"]:
            if stop.is_set():
                break
            yield {"step": f"Looking up {name} on Civitai…"}
            try:
                keep(websearch.civitai(name, 2))
            except Exception as exc:
                done["problems"].append(f"Civitai: {exc}")
    sources = sorted(sources, key=lambda x: not x.get("read"))[:8]  # pages actually read before bare snippets
    tags = code_tags(draft) if settings.opt("pv_search_danbooru") else []
    if tags and not stop.is_set():
        yield {"step": f"Checking {len(tags)} tags on Danbooru…"}
        try:
            for tag, info in websearch.danbooru_tags(tags).items():
                if not info["exists"]:
                    done["tags"].append({"tag": tag, "suggest": info["suggest"]})
        except Exception as exc:
            done["problems"].append(f"Danbooru: {exc}")
    done["sources"] = [{"n": i + 1, "title": x["title"][:150], "url": x["url"], "read": bool(x.get("read"))}
                       for i, x in enumerate(sources)]
    if (not sources and not done["tags"]) or stop.is_set():
        return None, done
    share = EVIDENCE // max(1, len(sources))
    found = "".join(f"[{i + 1}] {x['title']} ({x['url']})\n{x['text'][:max(share, 400)]}\n\n" for i, x in enumerate(sources))[:EVIDENCE]
    if done["tags"]:
        found += "Not Danbooru tags: " + "; ".join(
            t["tag"] + (f" (instead: {', '.join(s.replace('_', ' ') for s in t['suggest'])})" if t["suggest"] else " (no close tag)")
            for t in done["tags"]) + "\n"
    yield {"step": "Correcting the answer with what was found…"}
    return messages + [{"role": "assistant", "content": draft},
                       {"role": "user", "content": REVISE + (found or "Nothing was found on the web.")}], done
