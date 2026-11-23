"""Tests for the `om` CLI against a temporary catalog and temporary stores."""

import pytest
import yaml

from open_models.cli import main

from conftest import write_files


@pytest.fixture
def catalog(tmp_path, fake_model):
    path = tmp_path / "models.yaml"
    path.write_text(yaml.safe_dump({"models": [fake_model.to_dict()]}))
    return str(path)


def test_list(catalog, stores, capsys):
    assert main(["--catalog", catalog, "list"]) == 0
    assert "fake-model" in capsys.readouterr().out


def test_stage_verify_unstage(catalog, stores, fake_model, capsys):
    archive, working = stores
    write_files(archive, fake_model)
    assert main(["--catalog", catalog, "stage", "fake-model"]) == 0
    assert main(["--catalog", catalog, "verify"]) == 0
    assert "checked 2 copies, 0 problem(s)" in capsys.readouterr().out
    assert main(["--catalog", catalog, "path", "fake-model"]) == 0
    assert str(working.root) in capsys.readouterr().out  # working copy preferred
    assert main(["--catalog", catalog, "unstage", "fake-model"]) == 0
    assert not working.model_dir(fake_model).exists()


def test_unstage_refuses_without_archive_copy(catalog, stores, fake_model):
    _, working = stores
    write_files(working, fake_model)
    assert main(["--catalog", catalog, "unstage", "fake-model"]) == 1
    assert working.model_dir(fake_model).exists()


def test_verify_fails_on_corruption(catalog, stores, fake_model):
    archive, _ = stores
    write_files(archive, fake_model)
    archive.file_path(fake_model, fake_model.files[1]).write_bytes(b"X" * fake_model.files[1].size)
    assert main(["--catalog", catalog, "verify"]) == 1


def test_unknown_id_exits(catalog, stores):
    with pytest.raises(SystemExit):
        main(["--catalog", catalog, "fetch", "nope"])


@pytest.fixture
def mixed_catalog(tmp_path):
    """Catalog with one working-tier model and one archive-only model."""
    from conftest import make_model

    path = tmp_path / "mixed.yaml"
    models = [make_model("small", tier="edge"), make_model("big", tier="mid")]
    path.write_text(yaml.safe_dump({"models": [m.to_dict() for m in models]}))
    return str(path), {m.id: m for m in models}


def test_sync_places_models_by_tier(mixed_catalog, stores, capsys):
    path, models = mixed_catalog
    archive, working = stores
    for m in models.values():
        write_files(archive, m)
    write_files(working, models["big"])  # archive-only model wrongly on working store
    (working.root / "models" / "stranger").mkdir()

    assert main(["--catalog", path, "sync", "--dry-run"]) == 0
    assert working.status(models["small"]) == "missing"  # dry run changed nothing

    assert main(["--catalog", path, "sync"]) == 0
    assert working.status(models["small"]) == "present"
    assert working.status(models["big"]) == "missing"
    assert (working.root / "models" / "stranger").is_dir()  # unknown folders untouched
    assert "stranger: on working store but not in the catalog" in capsys.readouterr().out


def test_sync_keeps_working_copy_if_archive_incomplete(mixed_catalog, stores):
    path, models = mixed_catalog
    _, working = stores
    write_files(working, models["big"])
    assert main(["--catalog", path, "sync"]) == 1
    assert working.status(models["big"]) == "present"


def test_path_skips_mmproj_and_picks_first_shard(tmp_path, stores, capsys):
    import hashlib

    from open_models.catalog import Model, ModelFile

    names = ["mmproj-F16.gguf", "Q4/m-00002-of-00002.gguf", "Q4/m-00001-of-00002.gguf"]
    files = tuple(ModelFile(n, 1, hashlib.sha256(b"x").hexdigest()) for n in names)
    m = Model("split", "Split", "o/r", "a" * 40, "gguf", "mid", "chat", "mit", "2026-11-23", files)
    path = tmp_path / "split.yaml"
    path.write_text(yaml.safe_dump({"models": [m.to_dict()]}))
    archive, _ = stores
    for f in files:
        p = archive.file_path(m, f)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    assert main(["--catalog", str(path), "path", "split"]) == 0
    assert capsys.readouterr().out.strip().endswith("Q4/m-00001-of-00002.gguf")


def test_stale_warning():
    import datetime

    from conftest import make_model
    from open_models.cli import stale_warning

    models = {"a": make_model(pinned="2026-01-01")}
    assert stale_warning(models, today=datetime.date(2026, 3, 1)) is None
    assert "refresh" in stale_warning(models, today=datetime.date(2026, 8, 1))
