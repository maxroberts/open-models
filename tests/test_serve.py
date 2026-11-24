"""Tests for `scripts/serve.sh`: start, status, stop and its safety checks.

Uses a fake `llama-server` (a small Python HTTP server that answers /health) on a free
port, with a temporary working store and key file, so the real server and key are never
touched. Needs macOS tools the script uses (`lsof`, `curl`, `route`, `ipconfig`).
"""

import os
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "serve.sh"

FAKE_SERVER = f"""#!{sys.executable}
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
args = sys.argv[1:]
port = int(args[args.index("--port") + 1])
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass
HTTPServer(("127.0.0.1", port), H).serve_forever()
"""


def free_port():
    """A TCP port nothing is listening on right now."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def env(tmp_path):
    """Environment pointing serve.sh at a fake llama-server, temp store and temp key."""
    fake = tmp_path / "bin" / "llama-server"
    fake.parent.mkdir()
    fake.write_text(FAKE_SERVER)
    fake.chmod(0o755)
    (tmp_path / "working" / "models").mkdir(parents=True)
    e = dict(os.environ, OM_SERVE_PORT=str(free_port()), OM_SERVE_HOST="127.0.0.1",
             OM_SERVE_KEY_FILE=str(tmp_path / "cfg" / "key"),
             OPEN_MODELS_WORKING=str(tmp_path / "working"), LLAMA_SERVER=str(fake))
    yield e
    subprocess.run(["bash", str(SCRIPT), "stop"], env=e, capture_output=True)


def serve(env, *args):
    """Run serve.sh with `args`; return the finished process (no exception on failure)."""
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True,
                          text=True, timeout=90)


def test_start_status_stop(env):
    assert serve(env, "status").returncode == 1  # nothing running yet

    r = serve(env, "start")
    assert r.returncode == 0, r.stderr
    assert "created a new API key" in r.stdout
    key = Path(env["OM_SERVE_KEY_FILE"])
    assert len(key.read_text().strip()) >= 30
    assert stat.S_IMODE(key.stat().st_mode) == 0o600  # readable only by the owner

    r = serve(env, "status")
    assert r.returncode == 0 and f"http://127.0.0.1:{env['OM_SERVE_PORT']}" in r.stdout

    r = serve(env, "start")  # a second start refuses
    assert r.returncode == 1 and "already running" in r.stderr

    assert "stopped" in serve(env, "stop").stdout
    time.sleep(0.5)
    assert serve(env, "status").returncode == 1


def test_start_keeps_existing_key(env):
    key = Path(env["OM_SERVE_KEY_FILE"])
    key.parent.mkdir()
    key.write_text("existing-key\n")
    r = serve(env, "start")
    assert r.returncode == 0 and "created" not in r.stdout
    assert key.read_text() == "existing-key\n"


def test_start_refuses_without_working_store(env, tmp_path):
    env["OPEN_MODELS_WORKING"] = str(tmp_path / "unplugged")
    r = serve(env, "start")
    assert r.returncode == 1 and "working store not found" in r.stderr


def test_stop_leaves_other_programs_alone(env):
    port = int(env["OM_SERVE_PORT"])
    other = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind",
                              "127.0.0.1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):  # wait until it listens
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    break
            time.sleep(0.1)
        r = serve(env, "stop")
        assert r.returncode == 1 and "not stopping it" in r.stderr
        assert other.poll() is None  # still running
    finally:
        other.terminate()
        other.wait()
