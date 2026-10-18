"""Looking things up for an answer.

🔎 Verify: the model drafts an answer, picks what in it could be wrong (and the checkpoints or LoRAs it names), that is
looked up (the web, the pages themselves, Civitai, Danbooru for the tags of its prompts), and the answer the user reads
is written again from what was found, citing it.

🌐 Search (the Web search preset): the user's message is looked up first, and the model answers from the results."""

from __future__ import annotations

import json
import re
import time

from . import chat, settings, websearch

ROOM = 3600        # tokens kept free for the draft and what was found
EVIDENCE = 7000    # characters of what was found that go to the model
PLAN_SYSTEM = (
    "You plan web searches. You are given today's date, the end of the conversation, the user's last message and "
    "maybe a draft answer to it. Pick what needs looking up: in a draft, what could be wrong, made up or out of date "
    "(names, numbers, dates, versions, model and software settings, facts about people, places, works and events); "
    "with no draft, what the user's message asks. Reply with JSON only, no other words: "
    "{\"queries\": [\"...\"], \"models\": [\"...\"], \"pictures\": \"...\"}. queries: at most 3 web search queries, the most important "
    "first, each about one point, written as a person would type them into a search engine, with the names spelled "
    "out and what the conversation refers to made explicit (\"Illustrious XL recommended CFG\", not \"best "
    "settings for it\"). In English, plus one in the user's language when the subject is local to it. Add the year "
    "for anything that changes over time (latest, newest, price, release, version). models: at most 2 names of "
    "checkpoints or LoRAs to look up on Civitai, as they are called (\"Illustrious XL\", \"Pony Diffusion V6 XL\"). "
    "pictures: when the message is about a person, place, thing, creature, artwork or event that pictures would "
    "show well, a short image search for it (\"Henry Cavill\", \"Hagia Sophia interior\"); else \"\". Leave all "
    "empty when nothing needs looking up: opinions, fiction, a plain prompt, small talk."
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
FOUND = (
    "\n\n[Web search results for this message, found just now (today is {today}). Answer from them: what they say "
    "wins over what you remember, the newest first when they disagree. Cite a source as [n] where you use it. When "
    "they do not answer the question, say so and say what they do show; never make up facts, numbers or links that "
    "are not in them. Do not mention this note.]\n\n"
)
# a message that asks for pictures in so many words
ASKS_PICTURES = re.compile(r"\b(pictures?|photos?|pics?|show me|what does .* look like)\b|"  # not "image": every prompt is one
                           r"hình ảnh|(?<!\w)ảnh(?! hưởng)(?!\w)|cho (tôi |mình |em )?xem|trông (như thế nào|ra sao)|mặt mũi", re.I)
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
    """(queries, models, a search for pictures or "") from the plan's JSON."""
    found = re.search(r"\{.*\}", plan or "", re.S)
    try:
        data = json.loads(found.group(0)) if found else {}
    except Exception:
        data = {}
    def clean(items, n):
        items = items if isinstance(items, list) else []
        return [str(q).strip()[:120] for q in items if str(q).strip()][:n]
    pictures = data.get("pictures")
    return clean(data.get("queries"), 3), clean(data.get("models"), 2), str(pictures if isinstance(pictures, str) else "").strip()[:120]


def _question_query(question):
    """The question itself as a search, when it asks for facts: its first line, without greetings and markup."""
    line = re.sub(r"```.*?```", " ", question or "", flags=re.S)
    line = re.sub(r"\s+", " ", line).strip()
    return line[:120] if line and FACTUAL.search(line) and len(line.split()) >= 2 else ""


def _conversation(messages, chars=2400):
    """The end of the conversation before the last message, for the plan to know what "it" and "that" are."""
    lines = []
    for m in messages[-5:-1]:
        if m["role"] in ("user", "assistant"):
            lines.append(("User: " if m["role"] == "user" else "Assistant: ") + chat._words_of(m["content"])[:600])
    return "\n".join(lines)[-chars:]


def _with_results(messages, found):
    """The messages with the search results after the user's last message (one user turn, as every template wants)."""
    last = dict(messages[-1])
    if isinstance(last["content"], list):
        last["content"] = last["content"] + [{"type": "text", "text": found}]
    else:
        last["content"] = str(last["content"] or "") + found
    return messages[:-1] + [last]


def _shown_pictures(pictures):
    """What the model is told of the pictures shown beside its answer, so it neither describes nor invents them."""
    if not pictures:
        return ""
    return (f"\n{len(pictures)} pictures found for this are shown to the user beside your answer, from: "
            + "; ".join(p["title"] or p["page"] or p["src"] for p in pictures)
            + ". Do not put pictures, image links or Markdown images in your answer, and do not describe them.\n")


def run(messages, max_tokens, stop, search_first=False):
    """Steps for the page while the web is searched. Verify: the model drafts, the draft is looked up (the web, the
    pages read, Civitai) and its tags checked; returns (the messages to write the corrected answer from, or None when
    nothing was found to correct with, and what was done). Search (search_first): the user's message is looked up
    before any answer; returns (the messages with the results in them, and what was done)."""
    done = {"queries": [], "models": [], "sources": [], "tags": [], "problems": []}
    if search_first:
        done["mode"] = "search"
        draft = ""
    else:
        yield {"step": "Writing a first draft…"}
        draft = chat._complete(messages, max_tokens)
        done["draft"] = draft
        if stop.is_set():
            return None, done
    yield {"step": "Choosing what to search…" if search_first else "Choosing what to check…"}
    question = chat._words_of(messages[-1]["content"]) if messages else ""
    today = time.strftime("%Y-%m-%d")
    before = _conversation(messages)
    try:
        done["queries"], done["models"], picture_query = _plan(chat._complete(
            [{"role": "system", "content": PLAN_SYSTEM},
             {"role": "user", "content": f"Today: {today}\n\n"
                                         + (f"The conversation so far:\n{before}\n\n" if before else "")
                                         + f"The user's message:\n{question[:3000]}\n\n"
                                         + (f"The draft:\n{draft[:5000]}" if draft else "No draft: plan from the message.")}], 300))
    except Exception as exc:
        picture_query = ""
        done["problems"].append(f"planning: {exc}")
    if not done["queries"] and (search_first or not done["models"]):
        fallback = _question_query(question) if not search_first else re.sub(r"\s+", " ", question).strip()[:160]
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
    found_web.sort(key=lambda f: f["rank"])  # the best result of each search first, then the rest
    pages = 4 if search_first else 3
    if found_web and settings.opt("pv_search_read_pages") and websearch.to_read(found_web, pages) and not stop.is_set():
        yield {"step": f"Reading {len(websearch.to_read(found_web, pages))} pages…"}
        try:
            found_web = websearch.read_results(found_web, words, pages=pages)
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
    asked = bool(ASKS_PICTURES.search(question))
    if searching and settings.opt("pv_search_pictures") and (search_first or asked) and (picture_query or asked) \
            and not stop.is_set():
        yield {"step": "Finding pictures…"}
        pics, problems = websearch.pictures(picture_query or (done["queries"] or [question])[0], found_web)
        done["pictures"] = pics
        done["problems"] += [p for p in problems if p not in done["problems"]]
    sources = sorted(sources, key=lambda x: not x.get("read"))[:8]  # pages actually read before bare snippets
    tags = code_tags(draft) if draft and settings.opt("pv_search_danbooru") else []
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
    share = EVIDENCE // max(1, len(sources))
    found = "".join(f"[{i + 1}] {x['title']} ({x['url']})\n{x['text'][:max(share, 400)]}\n\n" for i, x in enumerate(sources))[:EVIDENCE]
    if search_first:
        if stop.is_set():
            return messages, done
        yield {"step": "Answering from what was found…" if sources else "Nothing found: answering without sources…"}
        return _with_results(messages, FOUND.format(today=today) + (found or "Nothing was found on the web.")
                             + _shown_pictures(done.get("pictures"))), done
    if (not sources and not done["tags"]) or stop.is_set():
        return None, done
    if done["tags"]:
        found += "Not Danbooru tags: " + "; ".join(
            t["tag"] + (f" (instead: {', '.join(s.replace('_', ' ') for s in t['suggest'])})" if t["suggest"] else " (no close tag)")
            for t in done["tags"]) + "\n"
    yield {"step": "Correcting the answer with what was found…"}
    return messages + [{"role": "assistant", "content": draft},
                       {"role": "user", "content": REVISE + (found or "Nothing was found on the web.")
                        + _shown_pictures(done.get("pictures"))}], done
