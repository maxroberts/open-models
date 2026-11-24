"""Tests for `scripts/mirror_repo.sh`: the repo copy kept in the archive.

Runs the real script against a throwaway git repo and a temporary archive folder
(`OPEN_MODELS_ARCHIVE`), then restores from what it wrote. Needs `git` and `bash`.
"""

import subprocess
import tarfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mirror_repo.sh"


def git(cwd, *args):
    """Run git in `cwd` with a fixed identity and return its stdout."""
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def make_repo(path):
    """Create a git repo with two commits and return the HEAD commit."""
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    (path / "README.md").write_text("first\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "first")
    (path / "catalog.yaml").write_text("models: []\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "second")
    return git(path, "rev-parse", "HEAD")


def run_mirror(repo, archive):
    """Run mirror_repo.sh on `repo`, writing into `archive`; return the finished process."""
    return subprocess.run(
        ["bash", str(SCRIPT), str(repo)], env={"PATH": "/usr/bin:/bin:/opt/homebrew/bin",
                                               "OPEN_MODELS_ARCHIVE": str(archive)},
        check=True, capture_output=True, text=True,
    )


def test_mirror_restores_history_and_files(tmp_path):
    repo, archive = tmp_path / "repo", tmp_path / "archive"
    head = make_repo(repo)
    run_mirror(repo, archive)
    out = archive / "repo"

    # The bundle restores the full history at the same commit.
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(out / "open-models.bundle"), str(clone))
    assert git(clone, "rev-parse", "HEAD") == head
    assert git(clone, "log", "--format=%s") == "second\nfirst"

    # The snapshot holds the committed files, under open-models/.
    with tarfile.open(out / "open-models.tar.gz") as tar:
        names = tar.getnames()
    assert "open-models/README.md" in names and "open-models/catalog.yaml" in names

    # MIRROR.txt names the commit, and SHA256SUMS checks out.
    assert f"commit: {head}" in (out / "MIRROR.txt").read_text()
    subprocess.run(["shasum", "-a", "256", "-c", "SHA256SUMS"], cwd=out, check=True,
                   capture_output=True)
    assert not list(out.glob("*.partial"))


def test_mirror_warns_about_uncommitted_changes(tmp_path):
    repo, archive = tmp_path / "repo", tmp_path / "archive"
    make_repo(repo)
    (repo / "README.md").write_text("edited but not committed\n")
    result = run_mirror(repo, archive)
    assert "uncommitted changes are not mirrored" in result.stderr
    # The snapshot has the committed version, not the edit.
    with tarfile.open(archive / "repo" / "open-models.tar.gz") as tar:
        assert tar.extractfile("open-models/README.md").read() == b"first\n"
