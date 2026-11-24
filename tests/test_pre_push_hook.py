"""Tests for `githooks/pre-push`: the repo mirror runs on `git push` and never blocks it.

Builds a throwaway repo containing copies of the hook and `scripts/mirror_repo.sh`, enables
the hook with `core.hooksPath`, and pushes to a local bare repo, with the archive pointed
at a temporary folder (`OPEN_MODELS_ARCHIVE`). Needs `git` and `bash`.
"""

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(cwd, *args, env=None):
    """Run git in `cwd` with a fixed identity; return the finished process."""
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                          cwd=cwd, env=env, check=True, capture_output=True, text=True)


def make_repo(tmp_path):
    """A repo with the hook enabled and one commit, plus a bare 'origin'; return the repo."""
    repo = tmp_path / "repo"
    (repo / "githooks").mkdir(parents=True)
    (repo / "scripts").mkdir()
    shutil.copy(ROOT / "githooks" / "pre-push", repo / "githooks" / "pre-push")
    shutil.copy(ROOT / "scripts" / "mirror_repo.sh", repo / "scripts" / "mirror_repo.sh")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.hooksPath", "githooks")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    git(tmp_path, "init", "-q", "--bare", "origin.git")
    git(repo, "remote", "add", "origin", str(tmp_path / "origin.git"))
    return repo


def test_push_mirrors_the_pushed_commit(tmp_path):
    repo = make_repo(tmp_path)
    archive = tmp_path / "archive"
    archive.mkdir()
    r = git(repo, "push", "-q", "origin", "main",
            env=dict(os.environ, OPEN_MODELS_ARCHIVE=str(archive)))
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    assert f"commit: {head}" in (archive / "repo" / "MIRROR.txt").read_text()
    assert "pre-push: mirrored" in r.stderr


def test_push_goes_ahead_without_the_archive(tmp_path):
    repo = make_repo(tmp_path)
    missing = tmp_path / "not-mounted"
    r = git(repo, "push", "-q", "origin", "main",
            env=dict(os.environ, OPEN_MODELS_ARCHIVE=str(missing)))  # check=True: must succeed
    assert "archive not mounted" in r.stderr
    assert not missing.exists()  # did not create the archive folder
    assert git(tmp_path / "origin.git", "rev-parse", "main").stdout.strip() == \
        git(repo, "rev-parse", "HEAD").stdout.strip()


def test_push_goes_ahead_when_the_mirror_fails(tmp_path):
    repo = make_repo(tmp_path)
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "repo").write_text("a file where the mirror folder should be")
    r = git(repo, "push", "-q", "origin", "main",
            env=dict(os.environ, OPEN_MODELS_ARCHIVE=str(archive)))
    assert "repo mirror FAILED" in r.stderr
    assert git(tmp_path / "origin.git", "rev-parse", "main").stdout.strip() == \
        git(repo, "rev-parse", "HEAD").stdout.strip()
