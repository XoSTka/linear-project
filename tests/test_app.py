"""Start the demo web server (demo/app.py) on a free port and call it like the browser page does."""

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import numpy as np
import pytest

import app  # demo/app.py
import core


@pytest.fixture(scope="module")
def base_url():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)  # port 0: the system picks a free port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(base_url, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base_url + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_page_and_info(base_url):
    status, body = call(base_url, "/")
    assert status == 200 and b"<html" in body.lower()
    status, body = call(base_url, "/api/info")
    info = json.loads(body)
    assert status == 200 and set(info["modes"]) == {"robust", "balanced", "capacity"}
    assert len(info["cases"]) >= 10


def test_stego_round_trip_over_http(base_url):
    y, x = np.mgrid[0:160, 0:240]
    img = 110 + 50 * np.sin(x / 13) + 35 * np.cos(y / 9)
    status, body = call(base_url, "/api/load", {"image": core.encode_png(img)})
    assert status == 200
    cover = json.loads(body)["image"]
    status, body = call(base_url, "/api/stego/embed", {"cover": cover, "text": "สวัสดี", "key": "k1", "mode": "balanced"})
    assert status == 200
    stego_img = json.loads(body)["image"]
    status, body = call(base_url, "/api/stego/extract", {"image": stego_img, "key": "k1", "mode": "balanced"})
    out = json.loads(body)
    assert status == 200 and out["status"] == "ok" and out["text"] == "สวัสดี"


def test_errors_come_back_as_json(base_url):
    status, body = call(base_url, "/api/nope", {})
    assert status == 404 and "error" in json.loads(body)
    status, body = call(base_url, "/api/stego/embed", {"cover": "not an image", "text": "x", "mode": "balanced"})
    assert status == 500 and "error" in json.loads(body)
    status, _ = call(base_url, "/missing.html")
    assert status == 404
