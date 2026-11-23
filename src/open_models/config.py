"""Locations of the catalog and the two model stores.

Summary: the single place that decides where `open-models` reads its catalog and
keeps model files. Every other module asks this one for paths.

Details:
- **Archive store** (`archive_root`): holds every model in the catalog and is the copy
  recovery starts from. Default `/Volumes/Starfish_Prime/model-storage`.
- **Working store** (`working_root`): fast SSD holding the models runnable on this
  machine (the edge and utility tiers; see `catalog.WORKING_TIERS` and `om sync`).
  Default `/Volumes/BackUp_T7/lm-storage` (deliberately outside the Dropbox folder, so
  Dropbox never syncs model weights).
- Both can be overridden with environment variables `OPEN_MODELS_ARCHIVE` and
  `OPEN_MODELS_WORKING`, e.g. on new hardware or in tests.
- The catalog defaults to `catalog/models.yaml` at the repo root. The repo root is found
  relative to this file, which assumes the package runs from the source tree (the
  editable install `uv sync` creates), not from a built wheel.
"""

import os
from pathlib import Path

DEFAULT_ARCHIVE = Path("/Volumes/Starfish_Prime/model-storage")
DEFAULT_WORKING = Path("/Volumes/BackUp_T7/lm-storage")

# src/open_models/config.py -> parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO_ROOT / "catalog" / "models.yaml"


def archive_root() -> Path:
    """Return the archive store root: `$OPEN_MODELS_ARCHIVE`, else the Starfish_Prime default."""
    return Path(os.environ.get("OPEN_MODELS_ARCHIVE", DEFAULT_ARCHIVE))


def working_root() -> Path:
    """Return the working store root: `$OPEN_MODELS_WORKING`, else the T7 default."""
    return Path(os.environ.get("OPEN_MODELS_WORKING", DEFAULT_WORKING))
