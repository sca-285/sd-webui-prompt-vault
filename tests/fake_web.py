"""Stand-ins for what Verify looks things up on, answering as the real ones do: DuckDuckGo's HTML page (redirect
links, an advert) and lite page, the pages its results point to (menus, scripts and one article), Brave's API,
Civitai's models, Wikipedia's search, Danbooru's tags and autocomplete, SearXNG's JSON. A query with "fail" in it
makes both DuckDuckGo pages answer 500, so Wikipedia is asked instead; one with "captcha" makes the HTML page ask for
a captcha, as DuckDuckGo does to bots, and the lite page still answer."""
import json, os, threading, time, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TAGS = {"1girl": 900000, "red_hair": 500000, "sundress": 40000, "hatsune_miku_(cosplay)": 3000, "balcony": 30000}
SUGGEST = {"glowing_tapestry_hair": ["glowing_hair", "long_hair"], "sun_dres": ["sundress"]}
seen = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, kind, body):
        data = body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", kind); self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        time.sleep(float(os.environ.get("FAKE_WEB_DELAY", "0")))
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        seen.append((url.path, q))
        host = "http://" + self.headers.get("Host", "")
        if url.path == "/html/":
            if "fail" in q.get("q", ""):
                return self.send(500, "text/html", "busy")
            if "captcha" in q.get("q", ""):
                return self.send(200, "text/html", '<div class="anomaly-modal">Unfortunately, bots use DuckDuckGo too.</div>')
            words = q.get("q", "")
            target = urllib.parse.quote(f"{host}/page/guide?x=1&y=2", safe="")
            page = ('<div class="result results_links result--ad"><a class="result__a" href="https://duckduckgo.com/y.js?ad=1">Advert</a></div>'
                    f'<div class="result results_links results_links_deep web-result"><h2 class="result__title">'
                    f'<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg={target}&amp;rut=abc">Guide to <b>{words}</b></a></h2>'
                    f'<a class="result__snippet" href="x">Use Euler a, 28 steps &amp; CFG 5 for {words}.</a></div>'
                    f'<div class="result results_links web-result"><a class="result__a" href="{host}/page/gone">Second “page”</a>'
                    '<a class="result__snippet" href="y">Café notes, 2026.</a></div>')
            return self.send(200, "text/html", page)
        if url.path == "/lite/":
            if "fail" in q.get("q", ""):
                return self.send(500, "text/html", "busy")
            return self.send(200, "text/html", (
                f'<table><tr><td><a rel="nofollow" href="{host}/page/guide?x=1&amp;y=2" class=\'result-link\'>Lite guide</a></td></tr>'
                "<tr><td class='result-snippet'>From the lite page.</td></tr></table>"))
        if url.path == "/page/guide":
            filler = "".join(f"<p>Paragraph {i} about the history of painting and nothing else of use here.</p>" for i in range(30))
            return self.send(200, "text/html; charset=utf-8", (
                "<html><head><script>var tracking = 'sampler cfg';</script><style>p{color:red}</style></head><body>"
                "<nav>Home | Sampler menu | Login</nav><header>Site header</header><article>"
                f"<h1>Settings guide</h1>{filler}"
                "<p>For Illustrious XL the recommended sampler is Euler a with 28 steps and CFG 5; above CFG 7 colours burn.</p>"
                "<p>Café owners say the 2026 release changed nothing.</p>"
                f"{filler}</article><footer>Footer cfg sampler links</footer></body></html>"))
        if url.path == "/res/v1/web/search":
            if self.headers.get("X-Subscription-Token") != "brave-key":
                return self.send(401, "application/json", "{}")
            return self.send(200, "application/json", json.dumps({"web": {"results": [
                {"title": "From <strong>Brave</strong>", "url": f"{host}/page/guide?x=1&y=2", "description": "brave snippet"}]}}))
        if url.path == "/api/v1/models":
            return self.send(200, "application/json", json.dumps({"items": [
                {"id": 795765, "name": q.get("query", ""), "type": "Checkpoint", "description": "<p>An anime model.</p>",
                 "modelVersions": [{"name": "v2.0", "baseModel": "Illustrious", "trainedWords": ["masterpiece", "best quality"],
                                    "description": "<p>Use CFG 5 to 6, Euler a.</p>"}]}]}))
        if url.path == "/w/rest.php/v1/search/page":
            return self.send(200, "application/json", json.dumps({"pages": [
                {"id": 1, "key": "Illustrious_XL", "title": "Illustrious XL", "description": "image model",
                 "excerpt": 'An <span class="searchmatch">anime</span> model from 2024.'}]}))
        if url.path == "/tags.json":
            names = q.get("search[name_comma]", "").split(",")
            return self.send(200, "application/json", json.dumps([{"name": n, "post_count": TAGS[n]} for n in names if n in TAGS]))
        if url.path == "/autocomplete.json":
            return self.send(200, "application/json", json.dumps(
                [{"type": "tag-word", "label": s.replace("_", " "), "value": s, "category": 0, "post_count": 1}
                 for s in SUGGEST.get(q.get("search[query]", ""), [])]))
        if url.path == "/search":
            return self.send(200, "application/json", json.dumps({"results": [
                {"url": "https://searx.example/one", "title": "From SearXNG", "content": "the answer is 42"}]}))
        self.send(404, "text/plain", "no")


    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        seen.append((url.path, body))
        host = "http://" + self.headers.get("Host", "")
        if url.path == "/search":  # Tavily: results with the passages of their pages on the query
            if self.headers.get("Authorization") != "Bearer tavily-key":
                return self.send(401, "application/json", '{"detail": {"error": "Unauthorized"}}')
            q = body.get("query", "")
            passage = (f"Tavily passage on {q}: Illustrious XL v2.0 was released in 2025; the model card recommends "
                       "Euler a, 28 steps and CFG 5 to 6, with a resolution near one megapixel. ") * 3
            return self.send(200, "application/json", json.dumps({"query": q, "answer": None, "results": [
                {"title": f"Tavily on {q}", "url": f"{host}/page/tavily-one", "content": passage, "score": 0.9},
                {"title": "Short one", "url": f"{host}/page/guide?x=1&y=2", "content": "too short", "score": 0.4}]}))
        self.send(404, "text/plain", "no")


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
