"""Stand-ins for what Verify looks things up on, answering as the real ones do: DuckDuckGo's HTML page (redirect
links, an advert), Wikipedia's search, Danbooru's tags and autocomplete, SearXNG's JSON. A query with "fail" in it
makes DuckDuckGo answer 500, so Wikipedia is asked instead."""
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
        if url.path == "/html/":
            if "fail" in q.get("q", ""):
                return self.send(500, "text/html", "busy")
            words = q.get("q", "")
            target = urllib.parse.quote("https://example.org/guide?x=1&y=2", safe="")
            page = ('<div class="result results_links result--ad"><a class="result__a" href="https://duckduckgo.com/y.js?ad=1">Advert</a></div>'
                    f'<div class="result results_links results_links_deep web-result"><h2 class="result__title">'
                    f'<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg={target}&amp;rut=abc">Guide to <b>{words}</b></a></h2>'
                    f'<a class="result__snippet" href="x">Use Euler a, 28 steps &amp; CFG 5 for {words}.</a></div>'
                    '<div class="result results_links web-result"><a class="result__a" href="https://second.example.com/page">Second “page”</a>'
                    '<a class="result__snippet" href="y">Café notes, 2026.</a></div>')
            return self.send(200, "text/html", page)
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


def start():
    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}"
