"""Tests for `open_models.catalog`: the real catalog loads, and bad entries are rejected."""

import pytest

from open_models import config
from open_models.catalog import CatalogError, load_catalog, parse_model

from conftest import make_model


def test_repo_catalog_is_valid():
    models = load_catalog(config.DEFAULT_CATALOG)
    assert "qwen3-0.6b-q8" in models


def test_round_trip():
    m = make_model()
    assert parse_model(m.to_dict()) == m


@pytest.mark.parametrize(
    "change, message",
    [
        ({"revision": "main"}, "revision"),
        ({"tier": "huge"}, "tier"),
        ({"format": "bin"}, "format"),
        ({"id": "Bad ID"}, "id"),
        ({"license": ""}, "license"),
    ],
)
def test_bad_fields_rejected(change, message):
    entry = make_model().to_dict() | change
    with pytest.raises(CatalogError, match=message):
        parse_model(entry)


@pytest.mark.parametrize("path", ["/etc/passwd", "../escape.gguf", "a/../../b"])
def test_file_paths_must_stay_inside_model_folder(path):
    entry = make_model().to_dict()
    entry["files"][0]["path"] = path
    with pytest.raises(CatalogError, match="relative"):
        parse_model(entry)


def test_bad_sha_rejected():
    entry = make_model().to_dict()
    entry["files"][0]["sha256"] = "abc"
    with pytest.raises(CatalogError, match="sha256"):
        parse_model(entry)


def test_duplicate_ids_rejected(tmp_path):
    import yaml

    d = make_model().to_dict()
    path = tmp_path / "models.yaml"
    path.write_text(yaml.safe_dump({"models": [d, d]}))
    with pytest.raises(CatalogError, match="duplicate"):
        load_catalog(path)


def test_role_and_pinned_validated():
    with pytest.raises(CatalogError, match="role"):
        parse_model(make_model().to_dict() | {"role": "poetry"})
    with pytest.raises(CatalogError, match="pinned"):
        parse_model(make_model().to_dict() | {"pinned": "last tuesday"})


def test_pinned_accepts_yaml_date(tmp_path):
    import yaml

    text = yaml.safe_dump({"models": [make_model().to_dict()]}).replace("'2026-11-23'", "2026-11-23")
    path = tmp_path / "models.yaml"
    path.write_text(text)
    assert load_catalog(path)["fake-model"].pinned == "2026-11-23"


def test_working_tiers():
    assert make_model(tier="edge").on_working and make_model(tier="utility").on_working
    assert not make_model(tier="mid").on_working and not make_model(tier="frontier").on_working


def test_append_entry_keeps_comments(tmp_path):
    from open_models.catalog import append_entry

    path = tmp_path / "models.yaml"
    path.write_text("# keep me\nmodels:\n")
    append_entry(path, make_model("one").to_dict())
    append_entry(path, make_model("two").to_dict())
    assert path.read_text().startswith("# keep me")
    assert list(load_catalog(path)) == ["one", "two"]
    with pytest.raises(CatalogError, match="already exists"):
        append_entry(path, make_model("one").to_dict())
