"""Looking things up for Qwen Chat's Verify: web pages (DuckDuckGo, or your own SearXNG), Wikipedia, and Danbooru
for whether a tag exists. Only search words and tag names leave the computer, never the conversation.

Each source can be pointed elsewhere (PV_DDG_URL, PV_WIKIPEDIA_URL, PV_DANBOORU_URL), which the checks use."""

from __future__ import annotations

import html
import os
import re
import urllib.parse

from . import settings

ENGINES = ("DuckDuckGo", "SearXNG", "Off")
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PromptVault/1.1 (Stable Diffusion WebUI extension)"
TIMEOUT = 12


def _get(url, params=None, json_answer=True):
    import requests

    res = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": AGENT, "Accept-Language": "en"})
    res.raise_for_status()
    res.encoding = res.encoding if "charset" in res.headers.get("Content-Type", "") else "utf-8"
    return res.json() if json_answer else res.text


def _text(fragment):
    """Words of an HTML fragment."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment or ""))).strip()


# ------------------------------------------------------------------ web pages


def _duckduckgo(query, n):
    base = os.environ.get("PV_DDG_URL", "https://html.duckduckgo.com").rstrip("/")
    page = _get(f"{base}/html/", {"q": query, "kl": "wt-wt"}, json_answer=False)
    out = []
    for block in re.split(r'<div[^>]+class="[^"]*\bresult\b', page)[1:]:
        link = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        href = html.unescape(link.group(1))
        if "uddg=" in href:  # DuckDuckGo's redirect: the real address is in uddg
            href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0])
        if href.startswith("//"):
            href = "https:" + href
        if "duckduckgo.com/y.js" in href or not href.startswith("http"):
            continue  # an advert
        snippet = re.search(r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|div|td)>', block, re.S)
        out.append({"title": _text(link.group(2)), "url": href, "text": _text(snippet.group(1) if snippet else "")})
        if len(out) >= n:
            break
    return out


def _searxng(query, n):
    base = str(settings.opt("pv_searxng_url") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("SearXNG is chosen but its address is empty (Settings → Prompt Vault)")
    data = _get(f"{base}/search", {"q": query, "format": "json", "safesearch": 0})
    return [{"title": r.get("title") or "", "url": r.get("url") or "", "text": r.get("content") or ""}
            for r in (data.get("results") or [])[:n] if r.get("url")]


def wikipedia(query, n=2):
    base = os.environ.get("PV_WIKIPEDIA_URL", "https://en.wikipedia.org").rstrip("/")
    data = _get(f"{base}/w/rest.php/v1/search/page", {"q": query, "limit": n})
    return [{"title": p.get("title") or "", "url": f"{base}/wiki/{urllib.parse.quote(p.get('key') or p.get('title') or '')}",
             "text": _text((p.get("description") or "") + ". " + (p.get("excerpt") or ""))}
            for p in data.get("pages") or []]


def search(query, n=4):
    """[{"title", "url", "text"}] from the web search chosen in Settings."""
    engine = str(settings.opt("pv_search_engine") or "DuckDuckGo")
    if engine == "Off":
        return []
    return (_searxng if engine == "SearXNG" else _duckduckgo)(query, n)


# ------------------------------------------------------------------ Danbooru tags

def _danbooru():
    return os.environ.get("PV_DANBOORU_URL", "https://danbooru.donmai.us").rstrip("/")


# what prompts use that is no Danbooru tag, and is not wrong for it
CONVENTIONS = re.compile(r"^(masterpiece|best[ _]quality|(high|amazing|great|good|normal|low|worst|bad)[ _]quality|very[ _]aesthetic|"
                         r"aesthetic|newest|recent|early|mid|old|year[ _]\d{4}|\d+k|uhd|hdr|hd|"
                         r"(score|source|rating)_\w+|(sfw|nsfw|safe|sensitive|questionable|explicit))$", re.I)


def tag_name(tag):
    """A prompt's tag as Danbooru writes it, or "" for what is no tag: (tag:1.2) -> tag, miku \\(cosplay\\) -> miku_(cosplay)."""
    t = str(tag).strip()
    weighted = re.match(r"^[(\[]+(.+?)(:[\d.]+)?[)\]]+$", t)
    if weighted and not re.search(r"\\[()]", t):
        t = weighted.group(1)
    t = t.replace("\\(", "(").replace("\\)", ")").strip()
    if not t or re.search(r"[<>{}|]|^(AND|BREAK)$", t) or len(t.split()) > 5 or CONVENTIONS.match(t):
        return ""
    return t.lower().replace(" ", "_")


def danbooru_tags(tags):
    """{tag: {"exists", "posts", "suggest": [close tags]}} for each tag (written with spaces or underscores)."""
    names = {}
    for tag in tags:
        name = tag_name(tag)
        if name:
            names[tag] = name
    if not names:
        return {}
    found = {}
    wanted = sorted(set(names.values()))
    for i in range(0, len(wanted), 40):
        for t in _get(f"{_danbooru()}/tags.json", {"search[name_comma]": ",".join(wanted[i:i + 40]),
                                                   "only": "name,post_count", "limit": 100}) or []:
            found[t.get("name")] = int(t.get("post_count") or 0)
    out = {}
    for tag, name in names.items():
        posts = found.get(name, 0)
        item = {"exists": posts > 0, "posts": posts, "suggest": []}
        if not posts:
            try:
                item["suggest"] = [s.get("value") or s.get("label") for s in
                                   _get(f"{_danbooru()}/autocomplete.json", {"search[query]": name, "search[type]": "tag_query",
                                                                            "limit": 3}) or [] if s.get("value") or s.get("label")]
            except Exception:
                pass
        out[tag] = item
    return out
