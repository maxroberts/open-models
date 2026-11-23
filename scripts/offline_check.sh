#!/usr/bin/env bash
# Prove that open-models can be rebuilt on this Mac from the archive alone, with no network.
#
# Summary: re-runs itself inside a macOS sandbox that blocks all network access, then
# (1) checks every runtime file against runtimes/SHA256SUMS, (2) installs `om` into a
# fresh environment from the archived uv, Python and wheels and runs the test suite,
# (3) builds llama.cpp from the archived source, and (4) runs the smallest catalog model
# with that fresh build (llama-completion, which needs no local network port). This is
# Stage 2's acceptance test; rerun it after scripts/archive_runtimes.sh changes anything.
#
# Details:
# - macOS only (uses `sandbox-exec`; Apple marks it deprecated, but it works on macOS 26).
#   Step 0 confirms the network really is blocked by trying to reach huggingface.co.
# - Works in a temporary folder that is deleted at the end; nothing in the repo or
#   archive is changed. Takes about 2.5 minutes, mostly the llama.cpp build.
# - Copies this checkout (without .venv, .git or caches) as the project to install.
# - Covers only this Mac's target (macos-arm64). The other targets' files are checked by
#   hash only; their uv and Python cannot run here, and their builds are untested.
# - Step 4 needs the smollm2-135m-q8 model in a store (working store first).
# Usage: scripts/offline_check.sh      (run from the repo root)
set -euo pipefail

if [ -z "${OM_SANDBOXED:-}" ]; then
  exec sandbox-exec -p '(version 1)(allow default)(deny network*)' \
    env OM_SANDBOXED=1 "$0" "$@"
fi

runtimes=${OPEN_MODELS_ARCHIVE:-/Volumes/Starfish_Prime/model-storage}/runtimes
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== 0. network is blocked"
if curl -s -m 5 https://huggingface.co > /dev/null; then echo "FAIL: network reachable" >&2; exit 1; fi
echo "ok"

echo "== 1. archive files match SHA256SUMS"
(cd "$runtimes" && shasum -a 256 -c --quiet SHA256SUMS)
echo "ok ($(wc -l < "$runtimes/SHA256SUMS") files)"

echo "== 2. install om from the archive and run the tests"
rsync -a --exclude .venv --exclude .git --exclude __pycache__ --exclude .pytest_cache ./ "$tmp/repo/"
OM_RUNTIME_HOME="$tmp/rt" UV_CACHE_DIR="$tmp/uv-cache" \
  scripts/install_om_offline.sh macos-arm64 "$runtimes" "$tmp/repo" "$tmp/venv" > "$tmp/install.log" 2>&1 \
  || { cat "$tmp/install.log"; exit 1; }
(cd "$tmp/repo" && "$tmp/venv/bin/python" -m pytest -q -p no:cacheprovider | tail -1)

echo "== 3. build llama.cpp from the archived source"
scripts/build_llama.sh macos-arm64 "$runtimes" "$tmp/llama" > "$tmp/build.log" 2>&1 \
  || { tail -30 "$tmp/build.log"; exit 1; }
"$tmp/llama/bin/llama-cli" --version 2>&1 | head -1

echo "== 4. run a model with the fresh build"
model=$("$tmp/venv/bin/om" path smollm2-135m-q8)
# llama-completion, not llama-cli: this llama-cli runs through a local server port, which
# the sandbox blocks (allowing loopback would also let some HTTPS traffic through here).
"$tmp/llama/bin/llama-completion" -m "$model" -n 24 -no-cnv -p "A Raspberry Pi is" \
  2>"$tmp/run.log" </dev/null
echo
grep -o '[0-9.]* tokens per second' "$tmp/run.log" | tail -1
echo "OFFLINE CHECK PASSED"
