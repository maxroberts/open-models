"""Tests for `open_models.store` and `open_models.fetch` (with Hugging Face faked out)."""

import pytest
import yaml

from open_models import fetch
from open_models.store import MISSING, PARTIAL, PRESENT, copy_model

from conftest import FILES, write_files


def test_status(stores, fake_model):
    archive, _ = stores
    assert archive.status(fake_model) == MISSING
    write_files(archive, fake_model)
    assert archive.status(fake_model) == PRESENT
    archive.file_path(fake_model, fake_model.files[0]).write_bytes(b"short")
    assert archive.status(fake_model) == PARTIAL


def test_verify_detects_same_size_corruption(stores, fake_model):
    archive, _ = stores
    write_files(archive, fake_model)
    assert archive.verify(fake_model, log=lambda _: None) == []
    f = fake_model.files[0]
    p = archive.file_path(fake_model, f)
    data = bytearray(p.read_bytes())
    data[0] ^= 0xFF  # flip bits without changing size: status() can't see this, verify() must
    p.write_bytes(bytes(data))
    assert archive.status(fake_model) == PRESENT
    assert "sha256 mismatch" in archive.verify(fake_model, log=lambda _: None)[0]


def test_copy_model_and_manifest(stores, fake_model):
    archive, working = stores
    write_files(archive, fake_model)
    copy_model(fake_model, archive, working, log=lambda _: None)
    assert working.verify(fake_model, log=lambda _: None) == []
    manifest = yaml.safe_load((working.model_dir(fake_model) / "model.yaml").read_text())
    assert manifest["revision"] == fake_model.revision


def test_copy_rejects_corrupt_source(stores, fake_model):
    archive, working = stores
    write_files(archive, fake_model)
    f = fake_model.files[0]
    archive.file_path(fake_model, f).write_bytes(b"X" * f.size)
    with pytest.raises(ValueError, match="hash"):
        copy_model(fake_model, archive, working, log=lambda _: None)
    # Neither the final file nor the .partial temp file is left behind.
    assert not working.file_path(fake_model, f).exists()
    assert list(working.model_dir(fake_model).glob("*.partial")) == []


def test_fetch_downloads_and_verifies(stores, fake_model, monkeypatch):
    archive, _ = stores

    def fake_download(repo, filename, revision, local_dir):
        assert revision == fake_model.revision  # always the pinned commit
        (local_dir / filename).write_bytes(FILES[filename])
        return str(local_dir / filename)

    monkeypatch.setattr(fetch, "hf_hub_download", fake_download)
    fetch.fetch_model(fake_model, archive, log=lambda _: None)
    assert archive.status(fake_model) == PRESENT
    assert (archive.model_dir(fake_model) / "model.yaml").exists()


def test_fetch_rejects_bad_download(stores, fake_model, monkeypatch):
    archive, _ = stores

    def bad_download(repo, filename, revision, local_dir):
        (local_dir / filename).write_bytes(b"tampered")

    monkeypatch.setattr(fetch, "hf_hub_download", bad_download)
    with pytest.raises(ValueError, match="hash"):
        fetch.fetch_model(fake_model, archive, log=lambda _: None)
    assert not (archive.model_dir(fake_model) / "model.yaml").exists()


def test_fetch_refuses_when_disk_too_full(stores, fake_model, monkeypatch):
    import shutil
    from collections import namedtuple

    archive, _ = stores
    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda _: usage(10, 10, 0))
    monkeypatch.setattr(fetch, "hf_hub_download", lambda *a, **k: pytest.fail("should not download"))
    with pytest.raises(OSError, match="free"):
        fetch.fetch_model(fake_model, archive, log=lambda _: None)
