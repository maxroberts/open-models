"""Tests for `serve.py` and the `om serve` command: presets, key, command line, launchd agent.

Uses temporary stores (conftest `stores`) and a temporary config folder
(`OPEN_MODELS_CONFIG`), and a fake `llama-server` that records its arguments instead of
serving, so nothing real is started. `om service` is not run here, because it would
install a real login agent; `launch_agent`, which builds its definition, is tested instead.
"""

import configparser
import hashlib
import stat
import sys

import pytest
import yaml

from open_models import serve
from open_models.catalog import Model, ModelFile
from open_models.cli import main


def make(model_id, names, role="chat", fmt="gguf", tier="utility"):
    """A Model with one 1-byte file per name in `names`."""
    files = tuple(ModelFile(n, 1, hashlib.sha256(b"x").hexdigest()) for n in names)
    return Model(model_id, model_id, "o/r", "a" * 40, fmt, tier, role, "mit", "2026-11-23", files)


def put(store, model):
    """Write `model`'s files into `store` so it counts as present."""
    for f in model.files:
        p = store.file_path(model, f)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")


CHAT = make("chat-m", ["chat.gguf", "README.md"])
VISION = make("vision-m", ["mmproj-F16.gguf", "v.gguf"])
EMBED = make("embed-m", ["e.gguf"], role="embedding")
SPLIT = make("split-m", ["Q4/s-00002-of-00002.gguf", "Q4/s-00001-of-00002.gguf"])
SAFETENSORS = make("st-m", ["model.safetensors"], fmt="safetensors")
ABSENT = make("absent-m", ["a.gguf"])


def test_main_gguf_and_mmproj():
    assert serve.main_gguf(SPLIT) == "Q4/s-00001-of-00002.gguf"
    assert serve.main_gguf(VISION) == "v.gguf"
    assert serve.main_gguf(SAFETENSORS) is None
    assert serve.mmproj_file(VISION) == "mmproj-F16.gguf"
    assert serve.mmproj_file(CHAT) is None


def test_presets_cover_present_gguf_models_with_their_flags(stores):
    _, working = stores
    for m in (CHAT, VISION, EMBED, SPLIT, SAFETENSORS):
        put(working, m)
    models = {m.id: m for m in (CHAT, VISION, EMBED, SPLIT, SAFETENSORS, ABSENT)}
    served = serve.served_models(models, working)
    assert [m.id for m in served] == ["chat-m", "vision-m", "embed-m", "split-m"]

    ini = configparser.ConfigParser()
    ini.read_string("[top]\n" + serve.presets_ini(served, working, 4096))  # `version` sits above sections
    assert ini["*"]["c"] == "4096"
    assert ini["chat-m"]["model"] == str(working.model_dir(CHAT) / "chat.gguf")
    assert "mmproj" not in ini["chat-m"] and "embeddings" not in ini["chat-m"]
    assert ini["vision-m"]["mmproj"] == str(working.model_dir(VISION) / "mmproj-F16.gguf")
    assert ini["vision-m"]["model"].endswith("/v.gguf")
    assert ini["embed-m"]["embeddings"] == "true"
    assert ini["split-m"]["model"].endswith("s-00001-of-00002.gguf")


def test_ensure_key_creates_private_key_once(tmp_path):
    key = tmp_path / "cfg" / "llama-server.key"
    assert serve.ensure_key(key) is True
    first = key.read_text()
    assert len(first.strip()) >= 30
    assert stat.S_IMODE(key.stat().st_mode) == 0o600
    assert serve.ensure_key(key) is False and key.read_text() == first


def test_server_command(tmp_path, monkeypatch):
    monkeypatch.delenv("LLAMA_SERVER", raising=False)
    cmd = serve.server_command(tmp_path / "p.ini", tmp_path / "k", "0.0.0.0", 8080, 1, 300)
    assert cmd[0] == "llama-server"
    assert cmd[cmd.index("--models-preset") + 1] == str(tmp_path / "p.ini")
    assert cmd[cmd.index("--api-key-file") + 1] == str(tmp_path / "k")
    assert cmd[cmd.index("--sleep-idle-seconds") + 1] == "300"
    assert "--sleep-idle-seconds" not in serve.server_command(tmp_path, tmp_path, "h", 1, 1, 0)


def test_launch_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("OPEN_MODELS_WORKING", "/somewhere")
    agent = serve.launch_agent(tmp_path / "om", ["--port", "8080"], tmp_path / "serve.log")
    assert agent["Label"] == serve.LABEL
    assert agent["ProgramArguments"] == [str(tmp_path / "om"), "serve", "--port", "8080"]
    assert agent["RunAtLoad"] is True and agent["KeepAlive"] is True
    assert "/opt/homebrew/bin" in agent["EnvironmentVariables"]["PATH"]
    assert agent["EnvironmentVariables"]["OPEN_MODELS_WORKING"] == "/somewhere"


@pytest.fixture
def served_catalog(tmp_path, stores, monkeypatch):
    """A catalog of CHAT and EMBED, both on the working store; config in tmp_path."""
    _, working = stores
    put(working, CHAT)
    put(working, EMBED)
    path = tmp_path / "models.yaml"
    path.write_text(yaml.safe_dump({"models": [CHAT.to_dict(), EMBED.to_dict()]}))
    monkeypatch.setenv("OPEN_MODELS_CONFIG", str(tmp_path / "cfg"))
    return str(path)


def test_om_serve_writes_presets_and_key_then_runs_llama_server(served_catalog, tmp_path,
                                                                monkeypatch):
    fake = tmp_path / "llama-server"
    args_out = tmp_path / "args.txt"
    fake.write_text(f"#!{sys.executable}\nimport sys\nopen({str(args_out)!r}, 'w')"
                    ".write('\\n'.join(sys.argv[1:]))\n")
    fake.chmod(0o755)
    monkeypatch.setenv("LLAMA_SERVER", str(fake))
    # om serve replaces its own process (exec); run it in a child process so the test survives.
    import subprocess
    r = subprocess.run([sys.executable, "-c", "import sys; from open_models.cli import main; "
                        f"sys.exit(main(['--catalog', {served_catalog!r}, 'serve', '--port', '9999']))"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    cfg = tmp_path / "cfg"
    assert "[embed-m]" in (cfg / "presets.ini").read_text()
    assert (cfg / "llama-server.key").is_file()
    args = args_out.read_text().splitlines()
    assert args[args.index("--port") + 1] == "9999"
    assert args[args.index("--models-preset") + 1] == str(cfg / "presets.ini")


def test_om_serve_print_presets(served_catalog, capsys):
    assert main(["--catalog", served_catalog, "serve", "--print-presets"]) == 0
    out = capsys.readouterr().out
    assert "[chat-m]" in out and "embeddings = true" in out


def test_om_serve_refuses_without_working_store(served_catalog, monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OPEN_MODELS_WORKING", str(tmp_path / "unplugged"))
    assert main(["--catalog", served_catalog, "serve"]) == 1
    assert "working store not found" in capsys.readouterr().err
