"""Demo app: hide a text message in a photo, and watermark a photo, using the project's real code.

    python demo/app.py            # opens http://127.0.0.1:8765 in your browser
    python demo/app.py --port 9000 --no-browser

Needs only the packages in requirements.txt (the web server is Python's built-in http.server).
Everything runs on this computer; no image leaves it.  Test results are saved to demo/demo_log.csv.
"""

from __future__ import annotations

import argparse
import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import core  # demo/core.py (Python puts the script's own folder on the import path)

STATIC = Path(__file__).resolve().parent / "static"
CONTENT_TYPES = {
    ".woff2": "font/woff2",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain; charset=utf-8",
}

ROUTES = {
    "/api/load": lambda d: core.load_cover(d["image"]),
    "/api/stego/embed": lambda d: core.stego_embed(
        d["cover"], d.get("text", ""), d.get("key", ""), d["mode"], bool(d.get("ecc"))
    ),
    "/api/stego/extract": lambda d: core.stego_extract(d["image"], d.get("key", ""), d["mode"], bool(d.get("ecc"))),
    "/api/stego/attack": lambda d: core.stego_attack_test(
        d["image"], d["text"], d.get("key", ""), d["mode"], d["kind"], d.get("level"), bool(d.get("ecc"))
    ),
    "/api/wm/embed": lambda d: core.wm_embed(d["cover"], d["alpha"], d.get("logo_text", ""), d.get("logo_image")),
    "/api/wm/extract": lambda d: core.wm_extract(d["image"], d["key_id"]),
    "/api/wm/attack": lambda d: core.wm_attack(d["image"], d["kind"], d.get("level")),
    "/api/case/run": lambda d: core.run_case(d.get("id", ""), d.get("image")),
    "/api/log": lambda d: core.log_result(
        d.get("tester", ""), d.get("case_id", ""), d.get("observed", ""), bool(d.get("matched")), d.get("note", "")
    ),
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/info":
            self._json(
                {
                    "modes": core.MODES,
                    "samples": core.list_samples(),
                    "cases": core.test_cases(),
                    "log": core.log_summary(),
                }
            )
        elif self.path == "/api/log.csv":
            self._send(200, core.log_csv(), "text/csv; charset=utf-8")
        elif self.path.startswith("/static/"):
            f = (STATIC / self.path[len("/static/") :].split("?")[0]).resolve()
            if f.is_file() and STATIC.resolve() in f.parents and f.suffix in CONTENT_TYPES:
                self._send(200, f.read_bytes(), CONTENT_TYPES[f.suffix])
            else:
                self._send(404, b"not found", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        fn = ROUTES.get(self.path)
        if fn is None:
            return self._json({"error": "unknown endpoint"}, 404)
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._json(fn(data))
        except Exception as e:  # show the reason in the page, not a blank
            traceback.print_exc()
            self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    def log_message(self, fmt, *args):  # keep the console quiet
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    url = f"http://127.0.0.1:{a.port}"
    print(f"Demo running at {url}  (press Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
