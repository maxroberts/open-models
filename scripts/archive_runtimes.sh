#!/usr/bin/env bash
# Fill the archive's `runtimes/` folder: everything needed to rebuild open-models offline.
#
# Summary: downloads the pinned runtime files in runtimes/manifest.tsv (llama.cpp source,
# its web UI, cmake, uv, Python), builds a Python wheelhouse per target from uv.lock,
# builds llama.cpp for this Mac from the archived source, copies the offline scripts and
# guide alongside, and writes SHA256SUMS. Stage 2 of the plan; rerun it after changing
# the manifest, uv.lock or llama.cpp version (docs/REFRESH.md).
#
# Details:
# - Needs the internet. Safe to rerun: files already present with the right hash are
#   skipped. Downloads go to `<file>.partial` and are renamed only after the hash matches.
# - Targets: macos-arm64 (this Mac), macos-x86_64 (2012 MacBook Air), linux-aarch64
#   (Pi 4/5), linux-armv6 (original Pi). Only macos-arm64 is built; the others are built
#   on their own machine with scripts/build_llama.sh (docs/OFFLINE.md).
# - Wheelhouses: `uv pip compile` produces runtimes/wheels/<target>/requirements.txt,
#   pinned to uv.lock's versions (as constraints) and with sha256 hashes from PyPI; pip
#   then downloads exactly those files and checks every hash (--require-hashes). pip runs
#   via `uvx`, in its own throwaway environment, not the system Python.
#   linux-armv6 has no binary wheels on PyPI: it gets pure-Python wheels, the PyYAML
#   source package, and the tools to build it (setuptools, Cython; build-requirements.txt).
# - SHA256SUMS covers every file under runtimes/; check it with `shasum -a 256 -c`.
# Usage: scripts/archive_runtimes.sh      (run from the repo root; archive from
#        $OPEN_MODELS_ARCHIVE, default /Volumes/Starfish_Prime/model-storage)
set -euo pipefail

runtimes=${OPEN_MODELS_ARCHIVE:-/Volumes/Starfish_Prime/model-storage}/runtimes
mkdir -p "$runtimes"

echo "== pinned downloads (runtimes/manifest.tsv)"
grep -v -e '^#' -e '^$' runtimes/manifest.tsv | while IFS=$'\t' read -r path sha url; do
  dest="$runtimes/$path"
  if [ -f "$dest" ] && [ "$(shasum -a 256 "$dest" | cut -d' ' -f1)" = "$sha" ]; then
    echo "ok        $path"; continue
  fi
  mkdir -p "$(dirname "$dest")"
  curl -fsSL -o "$dest.partial" "$url"
  got=$(shasum -a 256 "$dest.partial" | cut -d' ' -f1)
  if [ "$got" != "$sha" ]; then
    rm -f "$dest.partial"
    echo "HASH MISMATCH $path: expected $sha, got $got" >&2; exit 1
  fi
  mv "$dest.partial" "$dest"
  echo "fetched   $path"
done

echo "== Python wheelhouses (from uv.lock)"
constraints=$(mktemp)
trap 'rm -f "$constraints"' EXIT
uv export --all-groups --no-hashes --no-emit-project --format requirements-txt -q > "$constraints"
compile() {  # compile <target> <uv python-platform> [extra uv args...]: write requirements.txt
  local w="$runtimes/wheels/$1" platform=$2; shift 2
  mkdir -p "$w"
  uv pip compile pyproject.toml --group dev --python-version 3.12 --python-platform "$platform" \
    -c "$constraints" --generate-hashes --no-header -q "$@" -o "$w/requirements.txt"
}
download() {  # download <target> <requirements file> [extra pip args...]
  local w="$runtimes/wheels/$1" req=$2; shift 2
  uvx --python 3.12 pip download -q --require-hashes --no-deps -r "$req" -d "$w" "$@"
}
compile macos-arm64 aarch64-apple-darwin
download macos-arm64 "$runtimes/wheels/macos-arm64/requirements.txt" \
  --only-binary=:all: --platform macosx_11_0_arm64 --python-version 3.12 --implementation cp
compile macos-x86_64 x86_64-apple-darwin
download macos-x86_64 "$runtimes/wheels/macos-x86_64/requirements.txt" \
  --only-binary=:all: --platform macosx_10_15_x86_64 --python-version 3.12 --implementation cp
compile linux-aarch64 aarch64-manylinux_2_28
download linux-aarch64 "$runtimes/wheels/linux-aarch64/requirements.txt" \
  --only-binary=:all: --platform manylinux_2_28_aarch64 --python-version 3.12 --implementation cp
# ARMv6: uv has no armv6 platform; resolve for generic Linux and drop hf-xet, which
# huggingface-hub only requires on x86_64/arm64.
compile linux-armv6 linux --no-emit-package hf-xet
download linux-armv6 "$runtimes/wheels/linux-armv6/requirements.txt" --no-binary pyyaml
printf 'setuptools\ncython\n' | uv pip compile - --python-version 3.12 --generate-hashes \
  --no-header -q -o "$runtimes/wheels/linux-armv6/build-requirements.txt"
download linux-armv6 "$runtimes/wheels/linux-armv6/build-requirements.txt" \
  --only-binary=:all: --platform any --python-version 3.12 --implementation py

echo "== offline scripts and guide"
mkdir -p "$runtimes/tools"
cp scripts/build_llama.sh scripts/install_om_offline.sh scripts/offline_check.sh \
   docs/OFFLINE.md runtimes/manifest.tsv "$runtimes/tools/"

echo "== llama.cpp for this Mac (macos-arm64), from the archived source"
build="$runtimes/builds/macos-arm64"
if [ -x "$build/bin/llama-cli" ]; then
  echo "ok        builds/macos-arm64 (to rebuild in place: scripts/build_llama.sh macos-arm64 $runtimes $build)"
else
  mkdir -p "$build"
  scripts/build_llama.sh macos-arm64 "$runtimes" "$build" > "$runtimes/builds/build-macos-arm64.log" 2>&1 \
    || { echo "build failed; see $runtimes/builds/build-macos-arm64.log" >&2; exit 1; }
  "$build/bin/llama-cli" --version 2>&1 | head -1
fi

echo "== SHA256SUMS"
(cd "$runtimes" && find . -type f ! -name SHA256SUMS ! -name '*.partial' | sort \
  | sed 's|^\./||' | tr '\n' '\0' | xargs -0 shasum -a 256 > SHA256SUMS)
echo "$(wc -l < "$runtimes/SHA256SUMS") files, $(du -sh "$runtimes" | cut -f1) in $runtimes"
