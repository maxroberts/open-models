"""Load and validate the model catalog (`catalog/models.yaml`).

Summary: turns the YAML catalog, the source of truth for which models we keep, into
validated `Model` objects that the store, fetch, and CLI modules work from.

Details:
- The catalog is a YAML file with a top-level `models:` list. Each entry pins one model
  to an exact Hugging Face commit and lists every file to keep with its size in bytes
  and its sha256, so any copy can be verified without the network. See
  `catalog/models.yaml` for an annotated example; entries are normally generated with
  `om pin` rather than written by hand.
- Validation is strict and fails loudly (`CatalogError`) on anything malformed, because
  a silently wrong hash or path would defeat the point of the archive:
  ids are lowercase slugs and unique; `revision` is a full 40-hex commit (never a branch
  name, which can move); `sha256` is 64 hex; file paths are relative and stay inside the
  model folder; `tier`, `role`, and `format` come from fixed sets below; `pinned` is
  an ISO date (YAML may give it as a date object; it is kept as a "YYYY-MM-DD" string).
- `tier` also decides storage placement: models in `WORKING_TIERS` belong on the
  working store as well as the archive (enforced by `om sync`); all others are
  archive-only.
- `Model.to_dict()` produces the same shape the YAML uses; the store writes it next to
  the files as `model.yaml` so each store folder describes itself without the repo.
"""

import datetime
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

import yaml

# Hardware tiers: what it takes to run the model, not how good it is.
#   edge     - CPU only, <= ~4 GB RAM (Raspberry Pi, 2012 MacBook Air)
#   utility  - runs on a 16 GB Apple Silicon laptop (~10.7 GB usable by the GPU)
#   mid      - needs roughly 24-128 GB of fast memory
#   frontier - needs roughly 256 GB+ (big unified-memory Mac or multi-GPU server)
TIERS = ("edge", "utility", "mid", "frontier")
# Tiers runnable on the current machine; `om sync` keeps exactly these on the working store.
WORKING_TIERS = ("edge", "utility")
# What the model is for: general assistant, coding specialist, or text embeddings (search).
ROLES = ("chat", "code", "embedding")
FORMATS = ("gguf", "safetensors", "mlx")

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CatalogError(ValueError):
    """Raised when the catalog file or one of its entries is malformed."""


@dataclass(frozen=True)
class ModelFile:
    """One file of a model: path relative to the model folder, size in bytes, sha256 hex."""

    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Model:
    """One catalog entry: a model pinned to an exact upstream revision.

    `repo` and `revision` identify the Hugging Face source; `files` lists everything we
    keep. `pinned` is the date the entry was made (used to flag a stale catalog).
    `notes` is free text (e.g. why we keep it, prompt-format quirks).
    """

    id: str
    name: str
    repo: str
    revision: str
    format: str
    tier: str
    role: str
    license: str
    pinned: str
    files: tuple[ModelFile, ...]
    notes: str = ""

    @property
    def total_size(self) -> int:
        """Sum of all file sizes in bytes."""
        return sum(f.size for f in self.files)

    @property
    def on_working(self) -> bool:
        """True if storage policy puts this model on the working store (see WORKING_TIERS)."""
        return self.tier in WORKING_TIERS

    def to_dict(self) -> dict:
        """Return the entry as plain data in catalog YAML shape (used for `model.yaml`)."""
        d = asdict(self)
        d["files"] = [asdict(f) for f in self.files]
        return d


def _require(entry: dict, key: str, where: str):
    """Return `entry[key]`, raising `CatalogError` naming `where` if it is missing or empty."""
    value = entry.get(key)
    if value in (None, ""):
        raise CatalogError(f"{where}: missing '{key}'")
    return value


def parse_file(entry: dict, where: str) -> ModelFile:
    """Validate one `files:` item and return it as a `ModelFile`.

    Raises `CatalogError` if the path is absolute or escapes the model folder, the size
    is not a non-negative int, or the sha256 is not 64 lowercase hex characters.
    """
    path = str(_require(entry, "path", where))
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise CatalogError(f"{where}: file path must be relative and inside the model folder: {path}")
    size = entry.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise CatalogError(f"{where}: {path}: size must be a non-negative integer")
    sha = str(_require(entry, "sha256", where))
    if not _SHA256_RE.match(sha):
        raise CatalogError(f"{where}: {path}: sha256 must be 64 lowercase hex characters")
    return ModelFile(path=path, size=size, sha256=sha)


def parse_model(entry: dict) -> Model:
    """Validate one catalog entry (a dict from YAML) and return it as a `Model`.

    Raises `CatalogError` describing the first problem found.
    """
    if not isinstance(entry, dict):
        raise CatalogError(f"catalog entry must be a mapping, got {type(entry).__name__}")
    model_id = str(_require(entry, "id", "entry"))
    where = f"model '{model_id}'"
    if not _ID_RE.match(model_id):
        raise CatalogError(f"{where}: id must be lowercase letters, digits, '.', '_' or '-'")
    revision = str(_require(entry, "revision", where))
    if not _REVISION_RE.match(revision):
        raise CatalogError(f"{where}: revision must be a full 40-character commit hash")
    fmt = _require(entry, "format", where)
    if fmt not in FORMATS:
        raise CatalogError(f"{where}: format must be one of {FORMATS}")
    tier = _require(entry, "tier", where)
    if tier not in TIERS:
        raise CatalogError(f"{where}: tier must be one of {TIERS}")
    role = _require(entry, "role", where)
    if role not in ROLES:
        raise CatalogError(f"{where}: role must be one of {ROLES}")
    pinned = _require(entry, "pinned", where)
    try:
        pinned = datetime.date.fromisoformat(str(pinned)).isoformat()
    except ValueError:
        raise CatalogError(f"{where}: pinned must be a date like 2026-11-23") from None
    raw_files = _require(entry, "files", where)
    if not isinstance(raw_files, list):
        raise CatalogError(f"{where}: files must be a list")
    files = tuple(parse_file(f, where) for f in raw_files)
    paths = [f.path for f in files]
    if len(set(paths)) != len(paths):
        raise CatalogError(f"{where}: duplicate file paths")
    return Model(
        id=model_id,
        name=str(_require(entry, "name", where)),
        repo=str(_require(entry, "repo", where)),
        revision=revision,
        format=fmt,
        tier=tier,
        role=role,
        license=str(_require(entry, "license", where)),
        pinned=pinned,
        files=files,
        notes=str(entry.get("notes") or ""),
    )


def append_entry(path: Path, entry: dict) -> None:
    """Validate `entry` and append it as YAML text to the end of the catalog at `path`.

    Appends text rather than rewriting the file, so the catalog's comments survive.
    Assumes `models:` is the last top-level key and its items are indented two spaces
    (as in `catalog/models.yaml`). Raises `CatalogError` if the entry is invalid or its
    id is already in the catalog; the file is untouched in that case.
    """
    model = parse_model(entry)
    if model.id in load_catalog(path):
        raise CatalogError(f"catalog: id '{model.id}' already exists")
    text = yaml.safe_dump([entry], sort_keys=False)
    indented = "".join("  " + line for line in text.splitlines(keepends=True))
    with open(path, "a") as fh:
        fh.write("\n" + indented)


def load_catalog(path: Path) -> dict[str, Model]:
    """Read and validate the catalog YAML at `path`; return models keyed by id, in file order.

    Raises `CatalogError` on malformed YAML structure or duplicate ids, and
    `FileNotFoundError` if the file does not exist.
    """
    data = yaml.safe_load(Path(path).read_text()) or {}
    entries = data.get("models") or []
    if not isinstance(entries, list):
        raise CatalogError("catalog: 'models' must be a list")
    models: dict[str, Model] = {}
    for entry in entries:
        model = parse_model(entry)
        if model.id in models:
            raise CatalogError(f"catalog: duplicate id '{model.id}'")
        models[model.id] = model
    return models
