"""Tests for `scripts/bench_serving.py`: parsing the two streaming formats it reads.

The benchmark's timings depend on `post_stream` reading each server's stream correctly:
llama-server sends Server-Sent Events (`data: {...}`, ending `data: [DONE]`), Ollama
sends one JSON object per line. A tiny local HTTP server plays each role. The
benchmark itself needs real servers and models, so it is not run here.
"""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bench_serving.py"
spec = importlib.util.spec_from_file_location("bench_serving", SCRIPT)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

EVENTS = [{"n": 1}, {"n": 2}, {"n": 3, "done": True}]
BODIES = {
    "/sse": "".join(f"data: {json.dumps(e)}\n\n" for e in EVENTS) + "data: [DONE]\n\n",
    "/ndjson": "".join(json.dumps(e) + "\n" for e in EVENTS),
}


@pytest.fixture(scope="module")
def server():
    """Serve BODIES on a free local port; yield the base URL."""
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = BODIES[self.path].encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.mark.parametrize("path", ["/sse", "/ndjson"])
def test_post_stream_reads_both_formats(server, path):
    events = [ev for _, ev in bench.post_stream(server + path, {"x": 1})]
    assert events == EVENTS  # blank lines and [DONE] are skipped


def test_post_stream_timestamps_increase(server):
    times = [t for t, _ in bench.post_stream(server + "/ndjson", {})]
    assert times == sorted(times)
