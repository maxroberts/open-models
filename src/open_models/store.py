"""Model stores on disk: layout, presence checks, hash verification, copying, removal.

Summary: a `Store` is one root folder holding model files (the archive on
Starfish_Prime or the working store on the T7). This module is what the CLI and
`fetch` use to find, check, copy, and delete model files.

Details:
- Layout: `<root>/models/<model id>/<file path from the catalog>`, plus a
  `model.yaml` copy of the catalog entry in each model folder, so a store can be
  understood and verified with no repo (e.g. during recovery).
  `fetch` may also leave a `.cache/huggingface/` folder inside a model folder; that is
  Hugging Face's download bookkeeping and is ignored here.
- Two levels of checking:
  `Store.status` is fast (existence and byte size only, no reading of contents);
  `Store.verify` reads every byte and compares sha256 against the catalog. Only
  `verify` proves a copy is intact.
- `copy_model` copies archive -> working (or any store -> store), writing each file
  under a temporary name, hashing the written copy, and only then renaming it into
  place, so an interrupted or corrupt copy never looks complete.
- Hashing streams in 8 MiB chunks, so memory use is flat even for 100+ GB files.
"""

import hashlib
import shutil
from collections.abc import Callable
from pathlib import Path

import yaml

from .catalog import Model, ModelFile

CHUNK = 8 * 1024 * 1024
MANIFEST = "model.yaml"

# Values returned by Store.status.
PRESENT, PARTIAL, MISSING = "present", "partial", "missing"


def sha256_file(path: Path) -> str:
    """Return the sha256 hex digest of the file at `path`, read in 8 MiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


class Store:
    """A named model store rooted at `root` (e.g. `Store("archive", Path(...))`).

    The name only appears in messages. Nothing is created on disk until a model is
    written into the store.
    """

    def __init__(self, name: str, root: Path):
        self.name = name
        self.root = Path(root)

    def model_dir(self, model: Model) -> Path:
        """Folder holding `model`'s files in this store."""
        return self.root / "models" / model.id

    def file_path(self, model: Model, f: ModelFile) -> Path:
        """Full path of one of `model`'s files in this store."""
        return self.model_dir(model) / f.path

    def status(self, model: Model) -> str:
        """Fast presence check by existence and size only (no hashing).

        Returns `PRESENT` if every file exists with the catalog size, `MISSING` if none
        exist, else `PARTIAL` (some missing or wrong size).
        """
        ok = 0
        any_exists = False
        for f in model.files:
            p = self.file_path(model, f)
            if p.is_file():
                any_exists = True
                if p.stat().st_size == f.size:
                    ok += 1
        if ok == len(model.files):
            return PRESENT
        return PARTIAL if any_exists else MISSING

    def verify(self, model: Model, log: Callable[[str], None] = print) -> list[str]:
        """Hash every file of `model` and compare with the catalog.

        Returns a list of human-readable problems (empty means every file is present
        and intact). Logs one line per file via `log`. Does not modify anything.
        """
        problems = []
        for f in model.files:
            p = self.file_path(model, f)
            if not p.is_file():
                problems.append(f"{self.name}: {model.id}/{f.path}: missing")
            elif p.stat().st_size != f.size:
                problems.append(f"{self.name}: {model.id}/{f.path}: size {p.stat().st_size} != {f.size}")
            else:
                log(f"  hashing {self.name}:{model.id}/{f.path} ({f.size / 1e9:.2f} GB)")
                digest = sha256_file(p)
                if digest != f.sha256:
                    problems.append(f"{self.name}: {model.id}/{f.path}: sha256 mismatch ({digest})")
        return problems

    def write_manifest(self, model: Model) -> None:
        """Write `model.yaml` (the catalog entry) into the model's folder in this store."""
        d = self.model_dir(model)
        d.mkdir(parents=True, exist_ok=True)
        (d / MANIFEST).write_text(yaml.safe_dump(model.to_dict(), sort_keys=False))

    def remove(self, model: Model) -> None:
        """Delete the model's whole folder from this store (no-op if absent)."""
        if self.model_dir(model).exists():
            shutil.rmtree(self.model_dir(model))


def copy_model(model: Model, src: Store, dst: Store, log: Callable[[str], None] = print) -> None:
    """Copy every file of `model` from `src` to `dst`, verifying each copy by sha256.

    Files already in `dst` with the right size and hash are skipped. Each file is
    copied to `<name>.partial`, hashed, and renamed into place only if the hash matches
    the catalog. Writes `model.yaml` in `dst` when done.

    Raises `FileNotFoundError` if a source file is missing and `ValueError` if a copied
    file's hash does not match (the `.partial` file is deleted first).
    """
    for f in model.files:
        source = src.file_path(model, f)
        target = dst.file_path(model, f)
        if not source.is_file():
            raise FileNotFoundError(f"{src.name}: {model.id}/{f.path} is missing; cannot copy")
        if target.is_file() and target.stat().st_size == f.size and sha256_file(target) == f.sha256:
            log(f"  {f.path}: already in {dst.name}, verified")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".partial")
        log(f"  copying {f.path} ({f.size / 1e9:.2f} GB) {src.name} -> {dst.name}")
        shutil.copyfile(source, tmp)
        digest = sha256_file(tmp)
        if digest != f.sha256:
            tmp.unlink()
            raise ValueError(f"{model.id}/{f.path}: copy hash {digest} != catalog {f.sha256}")
        tmp.replace(target)
    dst.write_manifest(model)
