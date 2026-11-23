#!/usr/bin/env bash
# Build llama.cpp from the archived source, with no internet access needed.
#
# Summary: unpacks the pinned llama.cpp source and its prebuilt web UI from the archive's
# `runtimes/sources/`, then configures and builds it for one target and installs the
# binaries into an output folder. Called by `scripts/archive_runtimes.sh` (to build for
# this Mac) and `scripts/offline_check.sh` (to prove the offline build works); on other
# machines you run it by hand (docs/OFFLINE.md). A copy is kept in the archive.
#
# Details:
# - Needs only a C/C++ compiler and cmake >= 3.18 (archived under runtimes/cmake/ and
#   runtimes/sources/). Builds static binaries, so `<out>/bin` is self-contained.
# - Options that would reach the network are turned off: the web UI comes from the
#   archived dist (llama.cpp uses tools/ui/dist first), HTTPS model download
#   (LLAMA_OPENSSL) is off, and tests/examples (which fetch vocab files) are off.
# - Build number and commit are passed in explicitly, because a source tarball has no
#   git history; `llama-cli --version` then reports the same build as Homebrew's.
# - Per-target flags (only where the default would be wrong):
#     macos-arm64    Metal GPU on (default). Tested.
#     macos-x86_64   2012 MacBook Air (Ivy Bridge: AVX, no AVX2/FMA). Metal off, CPU only.
#                    Untested.
#     linux-aarch64  Raspberry Pi 4/5. Defaults (native CPU). Untested.
#     linux-armv6    Original Raspberry Pi. Native CPU, one compile job (512 MB RAM;
#                    expect hours, and add swap). Untested.
#   All targets other than macos-arm64 are meant to be built on that machine itself, so
#   GGML_NATIVE (on by default) picks the right CPU features.
# Usage: scripts/build_llama.sh <target> <runtimes-dir> <out-dir>
set -euo pipefail

LLAMA_BUILD=12359
LLAMA_COMMIT=b1b770d9

if [ $# -ne 3 ]; then
  echo "usage: $0 <macos-arm64|macos-x86_64|linux-aarch64|linux-armv6> <runtimes-dir> <out-dir>" >&2
  exit 2
fi
target=$1
runtimes=$(cd "$2" && pwd)
mkdir -p "$3"
out=$(cd "$3" && pwd)

jobs=$( (sysctl -n hw.ncpu || nproc) 2>/dev/null || echo 2)
case $target in
  macos-arm64)   flags=(-DGGML_METAL=ON) ;;
  macos-x86_64)  flags=(-DGGML_METAL=OFF) ;;
  linux-aarch64) flags=() ;;
  linux-armv6)   flags=(); jobs=1 ;;
  *) echo "unknown target: $target" >&2; exit 2 ;;
esac

# Resolve symlinks (macOS temp dirs are under /var -> /private/var): llama.cpp's web UI
# step builds relative paths and fails on a symlinked build folder.
work=$(cd "$(mktemp -d)" && pwd -P)
trap 'rm -rf "$work"' EXIT
tar xzf "$runtimes/sources/llama.cpp-b$LLAMA_BUILD-$LLAMA_COMMIT.tar.gz" -C "$work"
src=$(echo "$work"/llama.cpp-*)
mkdir -p "$src/tools/ui/dist"
tar xzf "$runtimes/sources/llama-ui-b$LLAMA_BUILD-dist.tar.gz" -C "$src/tools/ui/dist"

cmake -S "$src" -B "$work/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DLLAMA_BUILD_NUMBER=$LLAMA_BUILD -DLLAMA_BUILD_COMMIT=$LLAMA_COMMIT -DLLAMA_BUILD_IS_DEV=OFF \
  -DLLAMA_OPENSSL=OFF -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF \
  ${flags[@]+"${flags[@]}"}
cmake --build "$work/build" -j "$jobs"
cmake --install "$work/build" --prefix "$out"
echo "built llama.cpp b$LLAMA_BUILD for $target into $out/bin"
