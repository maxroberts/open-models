# open-models

Keep a verified, offline archive of open-weights LLMs, from small utility models to
frontier-scale ones, and run them locally day to day.

Goals:
- **Survive losing the internet.** Every model is pinned to an exact upstream commit and
  stored with sha256 checksums, so copies can be checked with no network access.
- **Be useful every day.** A few models live on a fast working drive and run with llama.cpp.
- **Outlive this laptop.** The archive holds models too big to run here (for future
  hardware), and is laid out so it can be understood without this repo.

## Where things live

| What | Where | Notes |
|---|---|---|
| This repo (code, catalog, docs) | `…/Dropbox/AI/open-models` | Small; synced by Dropbox. `.venv` is marked Dropbox-ignored. |
| **Archive store**: every model | `/Volumes/Starfish_Prime/model-storage` | The copy recovery starts from. Download logs in `logs/`. |
| **Repo mirror**: this repo's history + snapshot | `/Volumes/Starfish_Prime/model-storage/repo` | Committed work only, refreshed on every `git push` (hook) or by `scripts/mirror_repo.sh`. |
| **Runtime archive**: software to rebuild offline | `/Volumes/Starfish_Prime/model-storage/runtimes` | llama.cpp source and a build for this Mac, cmake, uv, Python, wheels. See [docs/OFFLINE.md](docs/OFFLINE.md). |
| **Working store**: models runnable here | `/Volumes/BackUp_T7/lm-storage` | Fast SSD; outside Dropbox on purpose. |
| Ollama's own store (Stage 5a test) | `/Volumes/BackUp_T7/lm-storage/ollama` | Ollama's copies of the working models (42 GB), not managed by `om`. See [docs/SERVING.md](docs/SERVING.md). |

Override either store with `OPEN_MODELS_ARCHIVE` / `OPEN_MODELS_WORKING`.
Model weights must never be put inside the Dropbox folder.

## What's in the catalog

29 models, about 1.55 TB, in four hardware tiers. Each model also has a role: chat, code
or embedding. Which tier a model is in decides where it lives:

| Tier | Runs on | Stored on |
|---|---|---|
| `edge` | CPU only, <= ~4 GB RAM (Raspberry Pi, 2012 MacBook Air) | T7 + archive |
| `utility` | this 16 GB M2 | T7 + archive |
| `mid` | ~24-128 GB machines | archive only |
| `frontier` | ~256 GB+ (GLM-5.3, GLM-5.3 Flash, DeepSeek V4.1 Flash) | archive only |

Why each model was chosen, and what was checked: [docs/MODELS.md](docs/MODELS.md).
How they compare on resources, speed, capability and safety: [docs/COMPARISON.md](docs/COMPARISON.md).
It also covers how close the best model here (GLM-5.3) is to Claude Opus 5.5, and what
hardware it would take to match Opus 5.5's responsiveness locally.
The six-month update process: [docs/REFRESH.md](docs/REFRESH.md).

## Setup

Prerequisites: macOS on Apple Silicon, [Homebrew](https://brew.sh), and [uv](https://docs.astral.sh/uv/).
Without internet, follow [docs/OFFLINE.md](docs/OFFLINE.md) instead.

```bash
brew install llama.cpp          # inference engine (llama-cli, llama-server)
cd /Volumes/BackUp_T7/Dropbox/AI/open-models
uv sync --dev                   # creates .venv and installs the `om` command
xattr -w com.dropbox.ignored 1 .venv   # once, if .venv was just created: keep it out of Dropbox
uv run pytest                   # should pass
git config core.hooksPath githooks   # once per clone: mirror the repo into the archive on push
```

One-time store setup: the T7's top folder is owned by `root`, so create the working
store once with
`sudo mkdir /Volumes/BackUp_T7/lm-storage && sudo chown "$USER":staff /Volumes/BackUp_T7/lm-storage`.
The archive folder on Starfish_Prime is created automatically.

No Hugging Face account is needed for public models. For gated models, or to avoid
rate limits, set `HF_TOKEN` or run `uvx hf auth login`.

## Usage

```bash
uv run om list                          # catalog, tiers, sizes, which store has each model
uv run om fetch qwen3-0.6b-q8           # download into the archive, verified
uv run om sync                          # put edge/utility models on the T7, remove others
uv run om verify                        # hash-check every copy in both stores
uv run om stage / unstage <id>          # manual override of sync for one model

# Chat with a model (uses the working copy if staged, else the archive copy)
llama-cli -m "$(uv run om path qwen3.5-9b-q4)"

# Check every model runnable here loads and answers (prints reply + tokens/s)
scripts/smoke_test.sh

# Archive the software needed to rebuild offline, then prove it works with no network
scripts/archive_runtimes.sh
scripts/offline_check.sh

# Copy the repo (full history + snapshot) into the archive. Runs by itself on every
# `git push` (githooks/pre-push); run it by hand to mirror without pushing.
scripts/mirror_repo.sh
```

Rebuilding on a new or offline machine (this Mac, a 2012 MacBook Air, a Raspberry Pi
4/5 or an original Pi) is described in [docs/OFFLINE.md](docs/OFFLINE.md).

When you run llama.cpp by hand, some models need extra flags (`om serve` adds the first
two itself); check their `notes` in the catalog. Embedding models need `--embeddings`.
Vision models use `--mmproj` with their `mmproj-F16.gguf`. DeepSeek V4.1 Flash must be
run with `--ple` (see docs/MODELS.md).

Chat with the working models from any computer on the home network (llama-server's web
page, protected by an API key), or use them from other tools via its OpenAI-style API:

```bash
uv run om service install   # serve now and at every login (also: status, restart, uninstall)
uv run om serve             # or run the server in the foreground
```

The first visit from a browser asks for the key; see "Using the chat from another
computer" in [docs/SERVING.md](docs/SERVING.md). `om serve` adds the vision and
embedding flags from the catalog, and unloads a model after 5 idle minutes. Conversations stay on this Mac and the home network; see "Privacy" in
[docs/SERVING.md](docs/SERVING.md) for the details and the opt-in features that reach the
internet.

Adding a model (full process in docs/REFRESH.md):

```bash
uv run om pin Qwen/Qwen3-0.6B-GGUF --id qwen3-0.6b-q8 --include "*Q8_0.gguf" LICENSE README.md \
    --tier edge --role chat --format gguf --append    # writes the entry into the catalog
uv run om fetch qwen3-0.6b-q8 && uv run om sync
```

## Codebase architecture

```
catalog/models.yaml      what we keep: pinned repo + revision, tier, role, pinned date,
                         files with size and sha256
runtimes/manifest.tsv    pinned upstream software files (url + sha256) for the offline
                         runtime archive
src/open_models/
  config.py              store and catalog locations (env-overridable)
  catalog.py             load and strictly validate the catalog; tier -> placement policy;
                         append new entries without losing comments
  store.py               on-disk layout, fast size check, sha256 verify, verified copy
  fetch.py               Hugging Face download (with free-space check) and `pin`
                         (the only network code)
  serve.py               `om serve` / `om service`: model presets from the catalog,
                         llama-server router command line, launchd login agent
  cli.py                 the `om` command, built on the modules above
docs/MODELS.md           why each model was chosen; compatibility findings; sources
docs/COMPARISON.md       the models side by side: resources, speed, capability, safety
docs/REFRESH.md          six-month refresh checklist
docs/OFFLINE.md          rebuilding from the archive without internet, per target machine
docs/SERVING.md          Ollama vs llama-server: benchmark, compatibility, recommendation
docs/benchmarks/         raw benchmark results (JSON lines)
scripts/smoke_test.sh    run edge/utility (or given) models once via llama.cpp
scripts/archive_runtimes.sh   fill <archive>/runtimes: manifest downloads, per-target
                         wheelhouses from uv.lock, llama.cpp build for this Mac, SHA256SUMS
scripts/build_llama.sh   build llama.cpp from the archived source for one target, offline
scripts/install_om_offline.sh  install `om` from the archived uv, Python and wheels
scripts/offline_check.sh run the offline rebuild on this Mac in a no-network sandbox
scripts/mirror_repo.sh   copy the repo into <archive>/repo: git bundle + snapshot of HEAD
githooks/pre-push        runs mirror_repo.sh on every `git push`; warns but never blocks
                         the push (enable with `git config core.hooksPath githooks`)
scripts/bench_serving.py benchmark llama-server vs Ollama on the same catalog models
tests/                   pytest; temporary stores, fake downloads, no network;
                         test_mirror_repo.py runs mirror_repo.sh on a throwaway git repo;
                         test_bench_serving.py checks the benchmark's stream parsing;
                         test_serve.py checks presets, key, command line and the launchd
                         agent definition, and runs `om serve` with a fake llama-server;
                         test_pre_push_hook.py pushes to a local bare repo with the hook on
```

**Flow.** `om pin --append` asks Hugging Face for a repo's files and adds a catalog
entry → `om fetch` downloads exactly those files at the pinned commit into the archive
and checks every sha256 → `om sync` copies edge/utility models to the working store
(again checked) and removes anything that doesn't belong there → llama.cpp runs the
file `om path` prints, or `om serve` serves every working-store model on the network
(presets generated from the catalog, started at login by `om service`).

**Offline runtimes** (separate from `om`, in shell scripts). `archive_runtimes.sh` reads
`runtimes/manifest.tsv` and uv.lock and fills `<archive>/runtimes/`. The
`build_llama.sh` and `install_om_offline.sh` scripts use only that folder, and
`offline_check.sh` runs both with networking blocked to prove it. Copies of the scripts
and docs/OFFLINE.md are kept in `<archive>/runtimes/tools/`. `mirror_repo.sh` puts the
whole repo, with its git history, in `<archive>/repo/`, so the archive (models, runtimes
and repo) is self-contained.

**Key design decisions.**
- *The catalog is the source of truth* and lives in git; stores hold only files. Each
  model folder also gets a `model.yaml` copy of its entry, so a store makes sense on
  its own during recovery.
- *Pin commits, not branches.* `revision` must be a full commit hash, so an upstream
  change can't silently alter what we archived.
- *Two checks.* `om list` / `status` compare file sizes only (instant); `om verify`
  reads and hashes every byte (slow for big models) and is the only real integrity check.
- *Placement follows tier.* `catalog.WORKING_TIERS` (edge, utility) is the whole policy;
  `om sync` enforces it. It never deletes a working copy unless the archive copy is
  present, and never touches folders the catalog doesn't know.
- *Stale catalogs are flagged.* `om list` warns when the newest `pinned` date is over
  180 days old.
- *Writes are all-or-nothing per file.* Copies go to `*.partial` and are renamed only
  after the hash matches; a failed download never gets a `model.yaml`.
- *llama.cpp + GGUF* is the runtime: one engine for Mac, NVIDIA, and plain CPU.
  `safetensors` and `mlx` are allowed catalog formats but no tooling targets them yet.
- *Serve with llama-server, not Ollama* (docs/SERVING.md). Ollama wraps the same engine
  but copies every model and can't take per-model flags; llama-server is already
  archived and reads the stores in place. Its router mode supplies model switching and
  idle unloading.
- *Archive the runtime with the models.* llama.cpp is archived as source at the exact
  build the catalog was checked against (12359), plus the prebuilt web UI its build would
  otherwise download. Only this Mac's build is archived; other machines build their own.
  Compilers and the OS are assumed, not archived.

Store layout: `<store>/models/<id>/<files…>` plus `model.yaml`, and Hugging Face's
download bookkeeping in `<id>/.cache/huggingface/` (archive only; safe to delete).

## Known gaps

These are planned for later stages:
- **Day-to-day use still runs Homebrew's llama.cpp,** not the archived build. Both are
  build 12359. Updating Homebrew without rerunning `scripts/archive_runtimes.sh` would
  make them differ.
- **The offline rebuild is proven only on this Mac.** The 2012 MacBook Air and both
  Raspberry Pi paths are archived but untested (docs/OFFLINE.md).
- **`om verify` does not check the runtime archive.** Use
  `shasum -a 256 -c --quiet SHA256SUMS` in `<archive>/runtimes/`.
- **Everything in the archive has a single copy.** HFS+ does not detect bit rot, and
  checks are not scheduled: run `om verify` (and `shasum -a 256 -c --quiet SHA256SUMS`
  in `runtimes/` and `repo/`) by hand, at least at each six-month refresh. Until there is a
  second copy, a damaged model can only be repaired by downloading it again while the
  upstream repo exists: delete the bad file, then `om fetch <id>`.
- **TODO (deferred, no drive yet):** a second archive drive, with an `om` command to
  mirror the archive to it and repair a bad file from the good copy. Scheduled checks
  are worth adding then, since a check could also repair.
- **The repo mirror is only as fresh as the last push** (or `scripts/mirror_repo.sh` run),
  and holds committed work only. Commits that aren't pushed aren't mirrored, and a push
  made while the archive drive is unplugged skips the mirror with a warning. The hook
  only runs in clones where `core.hooksPath` is set.
- **`om service` is only partly tested.** Installing it, serving through it and reading
  the T7 from it all work (docs/SERVING.md). Starting at login after a restart, and its
  retry while the T7 is unmounted, have not been tried. Ollama's own API (`/api/*`) is not provided. The 5a speed numbers were
  taken under heavy memory pressure and need a rerun with apps closed.
- `om unstage` checks only that the archive files exist at the right sizes, not their hashes.
- `om path` returns the first model `.gguf` in path order (skipping `mmproj` vision
  adapters), which is shard 00001 for split models. It does not add the extra flags
  some models need (`--mmproj`, `--ple`, `--embedding`); see each entry's `notes`.
- **Nothing in the frontier or mid tiers has been run.** They need hardware we don't
  have yet; only their downloads and hashes are verified.
- **No model has been run on the original Raspberry Pi Model B (ARMv6) or the 2012
  MacBook Air.** Their software is archived, but nothing has been built there yet.
- Retiring a model is manual (docs/REFRESH.md step 6).
- **TODO (deferred):** the archive has no NVFP4 build of GLM-5.3 (`nvidia/GLM-5.3-NVFP4`,
  464 GB), which the fast 8-GPU route in docs/MODELS.md needs. Only the GGUF builds are kept.
