# Rebuilding without the internet

How to get open-models and llama.cpp running from the archive alone, on any of the four
target machines. The archive's `runtimes/` folder holds every piece of software needed
on top of the operating system and a C/C++ compiler. A copy of this guide and its
scripts is in `runtimes/tools/`, in case the repo itself is missing.

## What is in the archive

`/Volumes/Starfish_Prime/model-storage/runtimes/` (filled by `scripts/archive_runtimes.sh`):

| Folder | Contents |
|---|---|
| `sources/` | llama.cpp at build 12359 (commit b1b770d9), the same build the catalog was checked against; its prebuilt web UI; cmake 4.4.3 source; CPython 3.12.15 source |
| `cmake/` | cmake 4.4.3 binaries: macOS (current and 10.10+), Linux aarch64 |
| `uv/` | uv 0.13.0 for each target |
| `python/` | Python 3.12.15, prebuilt, for every target except the original Pi |
| `wheels/<target>/` | every Python package `om` and its tests need, with `requirements.txt` (pinned to `uv.lock`, with hashes) |
| `builds/macos-arm64/` | llama.cpp built from `sources/` for Apple Silicon Macs (Metal) |
| `tools/` | the scripts below, this guide, and `manifest.tsv` |
| `SHA256SUMS` | sha256 of every file above |

Upstream files are pinned in `runtimes/manifest.tsv`, which says where each hash came
from. Not archived: the OS, compilers (Xcode Command Line Tools, gcc), and OS libraries.

## Targets

| Target | Machine | llama.cpp | Python / `om` | Tested? |
|---|---|---|---|---|
| `macos-arm64` | this MacBook Air M2, any Apple Silicon Mac | prebuilt in `builds/`, or build from source (Metal) | prebuilt Python + wheels | **Yes**, offline (see below) |
| `macos-x86_64` | 2012 MacBook Air (Ivy Bridge, macOS 10.15 at most) | build on the machine, CPU only (Metal off) | prebuilt Python + wheels | No |
| `linux-aarch64` | Raspberry Pi 4/5, 64-bit Raspberry Pi OS | build on the machine | prebuilt Python + wheels | No |
| `linux-armv6` | original Raspberry Pi Model B | build on the machine, one job at a time (hours; add swap) | build Python from source; PyYAML from source; no hf-xet | No |

## Steps on a new machine

Check the archive first, from inside `runtimes/`: `shasum -a 256 -c --quiet SHA256SUMS`.

1. **cmake** (skip if installed): unpack the binary from `cmake/` and put its `bin/` on
   `PATH`. On the original Pi, build it from `sources/cmake-4.4.3.tar.gz`
   (`./bootstrap && make && sudo make install`).
2. **llama.cpp**:
   `scripts/build_llama.sh <target> <runtimes-dir> <out-dir>`, then use `<out-dir>/bin/llama-cli`.
   On an Apple Silicon Mac you can instead use `builds/macos-arm64/bin/` directly.
3. **Original Pi only, Python:** build Python 3.12 from `sources/Python-3.12.15.tgz`
   (`./configure && make && sudo make altinstall`). Install the OS's OpenSSL and libffi
   development packages first, or Python builds without `ssl`, which `om`'s
   dependencies need.
4. **om:** `scripts/install_om_offline.sh <target> <runtimes-dir> <repo-dir>`
   (for the original Pi: `PYTHON=/usr/local/bin/python3.12 scripts/install_om_offline.sh ...`).
   Then `.venv/bin/om list`.
5. **Models:** point `om` at the archive and working store with `OPEN_MODELS_ARCHIVE` and
   `OPEN_MODELS_WORKING`, then run models as in the README.

`om fetch` and `om pin` need the internet. Everything else (`list`, `verify`, `sync`,
`stage`, `unstage`, `path`) works offline.

## Proof that it works

`scripts/offline_check.sh` runs inside a macOS sandbox with the network blocked. It checks
the archive's hashes, installs `om` from the archive into a fresh environment, runs the
test suite, builds llama.cpp from the archived source, and runs a model with that build.
It covers this Mac only.

Last result, 2026-11-23, MacBook Air M2, macOS 26.6: **passed** in about 2.5 minutes.
All 164 archive files matched their hashes, 32 of 32 tests passed, and the build reported
`version: 1.0.0 (build 12359, commit b1b770d9)`. That is the same build as Homebrew's
llama.cpp. SmolLM2-135M generated a sensible sentence at about 227 tokens/s.

The model step uses `llama-completion`. In this build `llama-cli` talks to a local server
on a loopback port, which the sandbox blocks. On a real offline machine loopback works,
so `llama-cli` is fine there.

## Keeping it current

Rerun `scripts/archive_runtimes.sh` and `scripts/offline_check.sh` whenever `uv.lock`, the
llama.cpp version, or `runtimes/manifest.tsv` changes (docs/REFRESH.md step 2). To move to
a new llama.cpp build, update the `LLAMA_BUILD`/`LLAMA_COMMIT` values in
`scripts/build_llama.sh` and the llama.cpp source and web UI lines in the manifest
together. Then rebuild this Mac's copy in place with
`scripts/build_llama.sh macos-arm64 <runtimes> <runtimes>/builds/macos-arm64`
(`archive_runtimes.sh` skips an existing build), and rerun `archive_runtimes.sh` to
refresh SHA256SUMS. Old files that are no longer in the manifest stay until you delete
them by hand.

## Known limits

- Only the `macos-arm64` path has been tested. The other three are built from the same
  source with standard options, but nobody has run them yet.
- The 2012 MacBook Air: the archived Python needs macOS 10.15 and uv needs 10.12
  (checked in the binaries). 10.15 (Catalina) is the newest macOS that machine runs, so
  update it to 10.15 first. Whether llama.cpp builds with 10.15's older Xcode compiler is unchecked.
- The original Pi's llama.cpp build may run out of memory without swap, and models
  beyond the smallest will be very slow.
- GitHub-generated source tarballs (llama.cpp) can change bytes over time even when
  the code doesn't. If a fresh download no longer matches the manifest, compare the
  contents before trusting it.
