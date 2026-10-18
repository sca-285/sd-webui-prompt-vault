"""Looking things up for the chat's Verify and Search: the web (Tavily or Brave Search with a key, your SearXNG,
DuckDuckGo), the pages
themselves (read, and their passages on the point picked out), Civitai for checkpoints and LoRAs, Wikipedia, and
Danbooru for whether a tag exists. Only search words, model names and tag names leave the computer, and the pages read.

Each source can be pointed elsewhere (PV_TAVILY_URL, PV_DDG_URL, PV_DDG_LITE_URL, PV_BRAVE_URL, PV_CIVITAI_URL, PV_WIKIPEDIA_URL,
PV_DANBOORU_URL), which the checks use."""

from __future__ import annotations

import html
import os
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from . import settings

ENGINES = ("Auto", "Tavily", "SearXNG", "Brave", "DuckDuckGo", "Off")
AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
TIMEOUT = 12
PAGE_BYTES = 2 * 1024 * 1024


class Blocked(RuntimeError):
    """A search engine answered with a captcha or a refusal instead of results."""


def _get(url, params=None, json_answer=True, headers=None):
    import requests

    res = requests.get(url, params=params, timeout=TIMEOUT,
                       headers=dict({"User-Agent": AGENT, "Accept-Language": "en-US,en;q=0.8"}, **(headers or {})))
    if res.status_code in (202, 403, 429):
        raise Blocked(f"refused the search (HTTP {res.status_code}, too many requests or a captcha)")
    res.raise_for_status()
    res.encoding = res.encoding if "charset" in res.headers.get("Content-Type", "") else "utf-8"
    return res.json() if json_answer else res.text


def _post(url, body, headers=None):
    import requests

    res = requests.post(url, json=body, timeout=TIMEOUT + 18, headers=dict({"User-Agent": AGENT}, **(headers or {})))
    if res.status_code in (401, 403):
        raise RuntimeError(f"refused the key (HTTP {res.status_code})")
    if res.status_code in (429, 432, 433):
        raise Blocked(f"out of searches for now (HTTP {res.status_code})")
    res.raise_for_status()
    return res.json()


def _text(fragment):
    """Words of an HTML fragment."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment or ""))).strip()


def _real_url(href):
    href = html.unescape(href or "")
    if "uddg=" in href:  # DuckDuckGo's redirect: the real address is in uddg
        href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0])
    if href.startswith("//"):
        href = "https:" + href
    return href


def _is_ad(href):
    return "duckduckgo.com/y.js" in href or "bing.com/aclick" in href or not href.startswith("http")


# ------------------------------------------------------------------ search engines


def _duckduckgo(query, n):
    base = os.environ.get("PV_DDG_URL", "https://html.duckduckgo.com").rstrip("/")
    page = _get(f"{base}/html/", {"q": query, "kl": "wt-wt"}, json_answer=False)
    if "anomaly-modal" in page or "bots use DuckDuckGo" in page:
        raise Blocked("asked for a captcha (too many searches from this computer)")
    out = []
    for block in re.split(r'<div[^>]+class="[^"]*\bresult\b', page)[1:]:
        link = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        href = _real_url(link.group(1))
        if _is_ad(href):
            continue
        snippet = re.search(r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|div|td)>', block, re.S)
        out.append({"title": _text(link.group(2)), "url": href, "text": _text(snippet.group(1) if snippet else "")})
        if len(out) >= n:
            break
    return out


def _duckduckgo_lite(query, n):
    """DuckDuckGo's lite page: plainer, and often still answering when the HTML one asks for a captcha."""
    base = os.environ.get("PV_DDG_LITE_URL", "https://lite.duckduckgo.com").rstrip("/")
    page = _get(f"{base}/lite/", {"q": query, "kl": "wt-wt"}, json_answer=False)
    if "anomaly-modal" in page or "bots use DuckDuckGo" in page:
        raise Blocked("asked for a captcha (too many searches from this computer)")
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*class=["\']result-link["\'][^>]*>(.*?)</a>', page, re.S)
    snippets = re.findall(r'class=["\']result-snippet["\'][^>]*>(.*?)</td>', page, re.S)
    out = []
    for i, (href, title) in enumerate(links):
        href = _real_url(href)
        if _is_ad(href):
            continue
        out.append({"title": _text(title), "url": href, "text": _text(snippets[i] if i < len(snippets) else "")})
        if len(out) >= n:
            break
    return out


def _tavily(query, n):
    """Tavily: a search made for language models. Its results come with the passages of each page on the query, so
    they count as read."""
    key = str(settings.opt("pv_tavily_key") or "").strip()
    if not key:
        raise RuntimeError("no Tavily key in Settings")
    base = os.environ.get("PV_TAVILY_URL", "https://api.tavily.com").rstrip("/")
    data = _post(f"{base}/search", {"query": query, "search_depth": "advanced", "max_results": n, "chunks_per_source": 3,
                                    "include_answer": False, "include_raw_content": False},
                 headers={"Authorization": f"Bearer {key}"})
    out = []
    for r in (data.get("results") or [])[:n]:
        text = _text(r.get("content"))
        if r.get("url"):
            out.append({"title": _text(r.get("title")) or r["url"], "url": r["url"], "text": text[:2000], "read": len(text) > 300})
    return out


def _brave(query, n):
    key = str(settings.opt("pv_brave_key") or "").strip()
    if not key:
        raise RuntimeError("no Brave Search key in Settings")
    base = os.environ.get("PV_BRAVE_URL", "https://api.search.brave.com").rstrip("/")
    data = _get(f"{base}/res/v1/web/search", {"q": query, "count": n, "safesearch": "off"},
                headers={"X-Subscription-Token": key, "Accept": "application/json"})
    return [{"title": _text(r.get("title")), "url": r.get("url") or "", "text": _text(r.get("description"))}
            for r in ((data.get("web") or {}).get("results") or [])[:n] if r.get("url")]


def _searxng(query, n):
    base = str(settings.opt("pv_searxng_url") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("no SearXNG address in Settings")
    data = _get(f"{base}/search", {"q": query, "format": "json", "safesearch": 0})
    return [{"title": r.get("title") or "", "url": r.get("url") or "", "text": r.get("content") or ""}
            for r in (data.get("results") or [])[:n] if r.get("url")]


def wikipedia(query, n=2):
    base = os.environ.get("PV_WIKIPEDIA_URL", "https://en.wikipedia.org").rstrip("/")
    data = _get(f"{base}/w/rest.php/v1/search/page", {"q": query, "limit": n})
    return [{"title": p.get("title") or "", "url": f"{base}/wiki/{urllib.parse.quote(p.get('key') or p.get('title') or '')}",
             "text": _text((p.get("description") or "") + ". " + (p.get("excerpt") or ""))}
            for p in data.get("pages") or []]


ENGINE_FUNCS = {"Tavily": _tavily, "SearXNG": _searxng, "Brave": _brave, "DuckDuckGo": _duckduckgo, "DuckDuckGo lite": _duckduckgo_lite}


def _chain():
    """The engines to try, in order: the one chosen, or (Auto) every one that is set up."""
    engine = str(settings.opt("pv_search_engine") or "Auto")
    if engine == "Off":
        return []
    if engine == "Auto":
        chain = []
        if str(settings.opt("pv_tavily_key") or "").strip():
            chain.append("Tavily")
        if str(settings.opt("pv_searxng_url") or "").strip():
            chain.append("SearXNG")
        if str(settings.opt("pv_brave_key") or "").strip():
            chain.append("Brave")
        return chain + ["DuckDuckGo", "DuckDuckGo lite"]
    return [engine] + (["DuckDuckGo lite"] if engine == "DuckDuckGo" else [])


def search_all(query, n=5):
    """([{"title", "url", "text", "engine"}], [problems]): the first engine of the chain that answers."""
    problems = []
    for name in _chain():
        try:
            found = ENGINE_FUNCS[name](query, n)
        except Exception as exc:
            problems.append(f"{name}: {exc}")
            continue
        if found:
            return [dict(f, engine=name) for f in found], problems
        problems.append(f"{name}: no results")
    return [], problems


def search(query, n=4):
    """[{"title", "url", "text"}] from the web search chosen in Settings (the first engine that answers)."""
    return search_all(query, n)[0]


# ------------------------------------------------------------------ reading pages

_DROP = re.compile(r"<(script|style|noscript|svg|nav|header|footer|aside|form|iframe|template)\b.*?</\1\s*>", re.S | re.I)
_BLOCK = re.compile(r"</?(p|div|li|ul|ol|h[1-6]|br|tr|td|th|table|section|article|pre|blockquote|dd|dt)\b[^>]*>", re.I)


def page_text(markup):
    """The readable words of a page: its article or main part when it has one, without menus and scripts."""
    markup = _DROP.sub(" ", re.sub(r"<!--.*?-->", " ", markup or "", flags=re.S))
    for tag in ("article", "main"):
        found = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", markup, re.S | re.I)
        if found and len(_text(found.group(1))) > 400:
            markup = found.group(1)
            break
    text = html.unescape(re.sub(r"<[^>]+>", " ", _BLOCK.sub("\n", markup)))
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if len(ln) > 1)


def read_page(url):
    """A web page's readable text, or "" (not a page, too big, or not answering in time)."""
    import requests

    try:
        with requests.get(url, timeout=(6, 10), stream=True, headers={"User-Agent": AGENT, "Accept": "text/html,*/*;q=0.5"}) as res:
            if res.status_code != 200 or "html" not in res.headers.get("Content-Type", "html"):
                return ""
            data = b""
            for chunk in res.iter_content(65536):
                data += chunk
                if len(data) > PAGE_BYTES:
                    break
            encoding = res.encoding if "charset" in res.headers.get("Content-Type", "") else "utf-8"
        return page_text(data.decode(encoding or "utf-8", "replace"))
    except Exception:
        return ""


_STOP = set("a an the of to in on for and or with is are was were be by at as it its this that what which who how why when "
            "does do did can could should would i you me my your from about into than then there their them best good use using "
            "vs versus".split())


def terms(*texts):
    """The words that matter in a question, for picking passages."""
    out = []
    for t in texts:
        for w in re.findall(r"[\w.+-]{2,}", str(t or "").lower()):
            if w not in _STOP and w not in out:
                out.append(w)
    return out


def passages(text, words, n=3, size=700):
    """The n stretches of a page most about the words (rarer words count more), in the page's order."""
    paras, chunk = [], ""
    for line in (text or "").split("\n"):
        if len(chunk) + len(line) > size and chunk:
            paras.append(chunk)
            chunk = ""
        chunk = f"{chunk} {line}".strip()
    if chunk:
        paras.append(chunk)
    if not paras or not words:
        return paras[:n]
    low = [p.lower() for p in paras]
    weight = {w: 1.0 / (1 + sum(w in p for p in low)) for w in words}
    scored = sorted(range(len(paras)), key=lambda i: -sum(weight[w] * min(3, low[i].count(w)) for w in words))
    best = sorted(i for i in scored[:n] if any(w in low[i] for w in words))
    return [paras[i] for i in best]


def to_read(results, pages=3):
    """Which of the results get their page opened: the first ones not already read (Tavily's are)."""
    return [i for i, r in enumerate(results) if not r.get("read")][:pages]


def read_results(results, words, pages=3, chars=1400):
    """The results with the passages of their pages on the point (in parallel); a page that cannot be read keeps its
    search snippet."""
    todo = to_read(results, pages)
    if not todo:
        return results
    with ThreadPoolExecutor(max_workers=len(todo)) as pool:
        texts = list(pool.map(lambda i: read_page(results[i]["url"]), todo))
    out = list(results)
    for i, text in zip(todo, texts):
        picked = passages(text, words) if text else []
        out[i] = dict(results[i], text=" … ".join(picked)[:chars] if picked else results[i].get("text", ""), read=bool(picked))
    return out


# ------------------------------------------------------------------ Civitai


def civitai(query, n=2):
    """Checkpoints and LoRAs on Civitai: kind, base model, trigger words, what its page says."""
    base = os.environ.get("PV_CIVITAI_URL", "https://civitai.com").rstrip("/")
    data = _get(f"{base}/api/v1/models", {"query": query, "limit": n, "nsfw": "true", "sort": "Most Downloaded"})
    out = []
    for m in data.get("items") or []:
        version = (m.get("modelVersions") or [{}])[0]
        words = ", ".join(version.get("trainedWords") or [])
        about = _text(version.get("description") or m.get("description") or "")[:700]
        bits = [m.get("type") or "", f"base model {version['baseModel']}" if version.get("baseModel") else "",
                f"version {version['name']}" if version.get("name") else "", f"trigger words: {words}" if words else ""]
        out.append({"title": f"{m.get('name')} (Civitai)", "url": f"https://civitai.com/models/{m.get('id')}",
                    "text": " · ".join(b for b in bits if b) + (f". {about}" if about else ""), "engine": "Civitai", "read": True})
    return out


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
