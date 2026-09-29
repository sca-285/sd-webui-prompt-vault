"""Model downloads from Hugging Face, done carefully.

A download goes to name.part and is renamed only when it is complete and has the
size the server announced, so a broken connection never leaves a half file that
looks like a model. HF_ENDPOINT (a mirror) and HF_TOKEN are honoured.
"""

from __future__ import annotations

import os
import threading

from . import TAG

_lock = threading.Lock()


def hf_url(repo, filename):
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co").rstrip("/")
    return f"{endpoint}/{repo}/resolve/main/{filename}"


def fetch(repo, filename, dest, progress=None):
    """Download repo/filename to dest unless it is already there. Returns dest."""
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        return dest
    import requests

    with _lock:
        if os.path.isfile(dest) and os.path.getsize(dest) > 0:
            return dest
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        url = hf_url(repo, filename)
        part = dest + ".part"
        headers = {}
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        print(f"{TAG} downloading {url}")
        try:
            with requests.get(url, stream=True, timeout=60, headers=headers, allow_redirects=True) as r:
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                total = int(r.headers.get("content-length") or 0)
                done, shown = 0, -1
                with open(part, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        if not chunk:
                            continue
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            pct = int(done * 100 / total)
                            if pct // 10 != shown:
                                shown = pct // 10
                                print(f"{TAG} {filename}: {pct}% of {total / 1e6:.0f} MB")
                            if progress:
                                progress(done / total)
            if total and os.path.getsize(part) != total:
                raise RuntimeError(f"incomplete: {os.path.getsize(part)} of {total} bytes")
            os.replace(part, dest)
        except Exception as exc:
            try:
                os.remove(part)
            except Exception:
                pass
            raise RuntimeError(
                f"could not download {filename} from {repo} ({exc}). Download it by hand from "
                f"{url} and put it at {dest}"
            ) from None
        print(f"{TAG} saved {dest}")
        return dest
