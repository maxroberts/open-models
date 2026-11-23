"""Talk to Hugging Face: download pinned models into a store, and pin new catalog entries.

Summary: the only module that uses the network. `fetch_model` fills a store (normally
the archive) from Hugging Face at the exact revision the catalog pins; `pin_entry`
builds a new catalog entry, with sizes and sha256s, for a repo you want to add.

Details:
- Downloads use `huggingface_hub.hf_hub_download(..., local_dir=...)`, which resumes
  interrupted downloads and keeps its bookkeeping in `<model folder>/.cache/huggingface/`.
  After download every file is hashed and checked against the catalog; a mismatch
  raises and the model is not marked complete (no `model.yaml` is written).
- `pin_entry` resolves a branch or tag to a full commit hash, so the catalog never
  points at something that can move. Hugging Face's API reports a sha256 only for
  large (LFS) files; small text files (LICENSE, README.md, configs) are downloaded to a
  temporary folder and hashed locally.
- Gated or private repos need a token; huggingface_hub picks it up from `HF_TOKEN` or a
  prior `hf auth login`. Nothing here stores tokens.
"""

import datetime
import fnmatch
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

from .catalog import Model, parse_model
from .store import Store, sha256_file


def fetch_model(model: Model, store: Store, log: Callable[[str], None] = print) -> None:
    """Download all of `model`'s files from Hugging Face into `store` and verify them.

    Files already present with the catalog size and sha256 are skipped (they are
    hashed to check, which for a resumed frontier download means re-reading every
    finished shard). Before downloading anything, checks that the store's disk has
    room for the files still missing plus 5% (huggingface_hub also keeps a partial
    file while downloading). On success writes `model.yaml` into the model folder.
    Raises `OSError` if the disk is too full, `ValueError` on a hash mismatch;
    network errors propagate from huggingface_hub.
    """
    dest = store.model_dir(model)
    dest.mkdir(parents=True, exist_ok=True)
    needed = sum(f.size for f in model.files if not store.file_path(model, f).is_file())
    free = shutil.disk_usage(dest).free
    if needed * 1.05 > free:
        raise OSError(f"{model.id}: needs {needed / 1e9:.1f} GB but only {free / 1e9:.1f} GB free on {store.name}")
    for f in model.files:
        target = store.file_path(model, f)
        if target.is_file() and target.stat().st_size == f.size and sha256_file(target) == f.sha256:
            log(f"  {f.path}: already in {store.name}, verified")
            continue
        log(f"  downloading {f.path} ({f.size / 1e9:.2f} GB) from {model.repo}@{model.revision[:10]}")
        hf_hub_download(model.repo, f.path, revision=model.revision, local_dir=dest)
        digest = sha256_file(target)
        if digest != f.sha256:
            raise ValueError(f"{model.id}/{f.path}: downloaded hash {digest} != catalog {f.sha256}")
    store.write_manifest(model)


def pin_entry(
    repo: str,
    include: list[str],
    model_id: str,
    tier: str,
    fmt: str,
    role: str = "chat",
    revision: str = "main",
    name: str | None = None,
    notes: str = "",
) -> dict:
    """Build a validated catalog entry for `repo` at `revision`, ready for the catalog.

    `include` is a list of glob patterns (e.g. `["*Q4_K_M*.gguf", "LICENSE", "README.md"]`)
    choosing which repo files to keep; patterns match full repo paths, including any
    subfolder. The license comes from the repo's model card ("unknown" if absent);
    `pinned` is today's date. Small non-LFS files are downloaded to a temp folder to hash.

    Returns the entry as a dict (catalog YAML shape). Raises `ValueError` if no file
    matches, and `CatalogError` if the result fails catalog validation.
    """
    info = HfApi().model_info(repo, revision=revision, files_metadata=True)
    siblings = [s for s in info.siblings if any(fnmatch.fnmatch(s.rfilename, p) for p in include)]
    if not siblings:
        raise ValueError(f"{repo}@{revision}: no files match {include}")
    files = []
    with tempfile.TemporaryDirectory() as tmp:
        for s in siblings:
            if s.lfs is not None:
                sha = s.lfs.sha256
            else:
                path = hf_hub_download(repo, s.rfilename, revision=info.sha, local_dir=tmp)
                sha = sha256_file(Path(path))
            files.append({"path": s.rfilename, "size": s.size, "sha256": sha})
    license_ = (info.card_data or {}).get("license") or "unknown"
    entry = {
        "id": model_id,
        "name": name or repo.split("/")[-1],
        "repo": repo,
        "revision": info.sha,
        "format": fmt,
        "tier": tier,
        "role": role,
        "license": str(license_),
        "pinned": datetime.date.today().isoformat(),
        "files": files,
    }
    if notes:
        entry["notes"] = notes
    parse_model(entry)  # fail now, not later, if anything is off
    return entry
