"""Shared pytest fixtures: a tiny fake model and isolated archive/working stores.

Summary: lets every test run against temporary folders instead of the real drives,
with no network access.

Details: `fake_model` is a `Model` whose two files' contents are known (`FILES`), so
tests can write them and get matching sizes and sha256s. `stores` points the
OPEN_MODELS_ARCHIVE / OPEN_MODELS_WORKING env vars (read by `config`) at
temporary folders and returns the matching `Store` objects.
"""

import hashlib

import pytest

from open_models.catalog import Model, ModelFile
from open_models.store import Store

FILES = {"weights.gguf": b"fake weights " * 1000, "LICENSE": b"Apache-2.0\n"}


def make_model(model_id: str = "fake-model", tier: str = "utility", pinned: str = "2026-11-23") -> Model:
    """Build a `Model` whose file entries match the contents in `FILES`."""
    files = tuple(
        ModelFile(path=p, size=len(b), sha256=hashlib.sha256(b).hexdigest()) for p, b in FILES.items()
    )
    return Model(
        id=model_id,
        name="Fake",
        repo="org/fake",
        revision="a" * 40,
        format="gguf",
        tier=tier,
        role="chat",
        license="apache-2.0",
        pinned=pinned,
        files=files,
    )


def write_files(store: Store, model: Model) -> None:
    """Write the `FILES` contents for `model` into `store`, as a fetch would."""
    for f in model.files:
        p = store.file_path(model, f)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(FILES[f.path])


@pytest.fixture
def fake_model() -> Model:
    return make_model()


@pytest.fixture
def stores(tmp_path, monkeypatch) -> tuple[Store, Store]:
    """(archive, working) stores in tmp_path, also wired into `config` via env vars."""
    monkeypatch.setenv("OPEN_MODELS_ARCHIVE", str(tmp_path / "archive"))
    monkeypatch.setenv("OPEN_MODELS_WORKING", str(tmp_path / "working"))
    return Store("archive", tmp_path / "archive"), Store("working", tmp_path / "working")
