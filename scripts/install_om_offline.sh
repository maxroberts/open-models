#!/usr/bin/env bash
# Install the `om` tool and its test dependencies from the archive, with no internet access.
#
# Summary: unpacks the archived uv and Python 3.12 for one target, creates a virtual
# environment for an open-models checkout, and installs the pinned packages from the
# archived wheelhouse. Used by `scripts/offline_check.sh` and by hand on a new or offline
# machine (docs/OFFLINE.md). A copy is kept in the archive.
#
# Details:
# - uv and Python are unpacked under $OM_RUNTIME_HOME/<target> (default
#   ~/.local/open-models-runtime). This keeps them out of the repo, which may sit in a
#   synced folder.
# - Packages come only from runtimes/wheels/<target>/ (`--no-index`), checked against the
#   sha256 hashes in that folder's requirements.txt, which lists every package needed
#   (installed with --no-deps). Versions match the repo's uv.lock.
# - Does not use `uv sync`: offline, uv sync re-resolves for every platform and fails,
#   so this installs the target's requirements list and then the project itself.
# - linux-armv6 (original Pi) has no prebuilt Python: build Python >= 3.12 from
#   runtimes/sources/Python-3.12.15.tgz first and pass it as PYTHON=/path/to/python3.12.
#   There, PyYAML is built from source (pure Python, without libyaml), and hf-xet (fast
#   Hugging Face downloads) is left out, as huggingface-hub does on that CPU. Untested.
# - Refuses to replace an existing virtual environment at the destination (uv's error).
# Usage: scripts/install_om_offline.sh <target> <runtimes-dir> <repo-dir> [venv-dir]
#        (venv-dir defaults to <repo-dir>/.venv)
set -euo pipefail

if [ $# -lt 3 ]; then
  echo "usage: $0 <macos-arm64|macos-x86_64|linux-aarch64|linux-armv6> <runtimes-dir> <repo-dir> [venv-dir]" >&2
  exit 2
fi
target=$1
runtimes=$(cd "$2" && pwd)
repo=$(cd "$3" && pwd)
venv=${4:-$repo/.venv}

case $target in
  macos-arm64)   triple=aarch64-apple-darwin ;;
  macos-x86_64)  triple=x86_64-apple-darwin ;;
  linux-aarch64) triple=aarch64-unknown-linux-gnu ;;
  linux-armv6)   triple=arm-unknown-linux-musleabihf ;;
  *) echo "unknown target: $target" >&2; exit 2 ;;
esac

home=${OM_RUNTIME_HOME:-$HOME/.local/open-models-runtime}/$target
mkdir -p "$home"
tar xzf "$runtimes/uv/uv-0.13.0-$triple.tar.gz" -C "$home"
uv="$home/uv-$triple/uv"

if [ -z "${PYTHON:-}" ]; then
  if [ "$target" = linux-armv6 ]; then
    echo "linux-armv6: set PYTHON to a Python >= 3.12 built from runtimes/sources/Python-3.12.15.tgz" >&2
    exit 2
  fi
  tar xzf "$runtimes/python/cpython-3.12.15-$triple.tar.gz" -C "$home"
  PYTHON="$home/python/bin/python3.12"
fi

wheels="$runtimes/wheels/$target"
export UV_OFFLINE=1 UV_NO_CONFIG=1 VIRTUAL_ENV="$venv"
"$uv" venv --python "$PYTHON" "$venv"
# requirements.txt is the full pinned dependency set, so no resolving is needed (--no-deps).
"$uv" pip install --no-index --find-links "$wheels" --no-deps -r "$wheels/requirements.txt"
"$uv" pip install --no-index --find-links "$wheels" --no-deps -e "$repo"
echo "installed om into $venv (run: $venv/bin/om list)"
