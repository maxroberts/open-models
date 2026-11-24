# open-models

Offline archive + daily runner for open-weights LLMs. The user's goal: keep access to
world-class open models even with no internet, from utility models up to frontier ones
(for future hardware). See README.md for architecture.

## Commands
- `uv sync --dev`, `uv run pytest`
- `uv run om list | fetch | verify | sync | stage | unstage | path | pin` (see `om --help`)
- Long downloads: run in background, log to `/Volumes/Starfish_Prime/model-storage/logs/`,
  with `PYTHONUNBUFFERED=1 HF_HUB_DISABLE_PROGRESS_BARS=1`; judge progress from the log
- Run a model: `llama-cli -m "$(uv run om path <id>)"` (llama.cpp from Homebrew)
- Smoke-test runnable models: `scripts/smoke_test.sh [ids]`
- Offline runtimes: `scripts/archive_runtimes.sh` then `scripts/offline_check.sh` (docs/OFFLINE.md).
- After the user commits: `scripts/mirror_repo.sh` copies the repo into `<archive>/repo`.
  Never `rm -rf` inside the archive; rebuild llama.cpp in place with build_llama.sh

## Storage (decided with the user)
- Archive (everything, incl. later runtimes and a repo mirror): `/Volumes/Starfish_Prime/model-storage` (4 TB, HFS+, USB)
- Working store: `/Volumes/BackUp_T7/lm-storage` (T7 SSD, outside Dropbox). Holds exactly the
  `edge` + `utility` tiers (`om sync`); mid/frontier are archive-only (user's rule)
- The repo is inside the live Dropbox folder: never put weights or large files here.
  `.venv` carries the `com.dropbox.ignored` xattr; re-apply if `.venv` is recreated.
- Current machine: MacBook Air M2, 16 GB (~10-11 GB usable by the GPU), so only the
  `edge`/`utility` tiers run locally. The user plans to buy stronger hardware later.
- Edge targets the user named: original 512 MB Raspberry Pi Model B (ARMv6), Pi 4/5, 2012 MacBook Air.

## Model choices
docs/MODELS.md (rationale + sources) and docs/REFRESH.md (six-month refresh; next May 2027).
Verify claims against Hugging Face repos, not SEO "best LLM" pages. Check each GGUF's
`gguf.architecture` against the installed llama.cpp and read READMEs for gotchas
(e.g. DeepSeek V4.1 Flash shard 00008 skipped, run with `--ple`).

## Plan (one stage at a time, pause for review after each)
1. Skeleton, catalog, stores, one model end to end: done
2. Archive runtimes offline: done (2026-11-23). `scripts/archive_runtimes.sh` fills
   `<archive>/runtimes` (779 MB); `scripts/offline_check.sh` passed in a no-network sandbox.
   Only macos-arm64 is built/tested; the other 3 targets are archived as source + wheels
3. Research and fill the catalog by tier: done (Nov 2026); downloads may still be running
4. Integrity + backups: repo mirror done (2026-11-23, `scripts/mirror_repo.sh` ->
   `<archive>/repo`, tested). Deferred (user, 2026-11-23): second archive drive (none yet;
   TODO) and scheduled checks (add once there is a second copy to repair from).
5. Serving: OpenAI-compatible server, model switching (an earlier Ollama/Open WebUI/MCP
   setup is in `../local llm project.zip`, possibly reusable)
   - 5a done 2026-11-24 (docs/SERVING.md, scripts/bench_serving.py): Ollama 0.40.18
     installed via Homebrew (not as a service); it wraps a bundled llama-server (build
     12651). Preliminary recommendation: llama-server router mode (--models-dir /
     --models-preset), Ollama optional. User has not decided yet. Speed numbers need a
     rerun without memory pressure. 16 working models are imported into Ollama's store
     at /Volumes/BackUp_T7/lm-storage/ollama (42 GB, `om-<id>`).
   - User chose llama-server (2026-11-24), provided it can match Ollama's features.
     Missing vs Ollama: Ollama's native /api/* endpoints (ask whether any tool needs them).
     Network chat works by hand (docs/SERVING.md, "Using the chat from another computer"):
     router mode on 0.0.0.0:8080 with --api-key-file ~/.config/open-models/llama-server.key.
     User works remotely (VS Code Remote-SSH from another machine on the LAN).
   - 5b plan (not started): `om serve` generating a --models-preset INI from the catalog
     (mmproj/embedding/--ple flags), launchd service at login with the network + key
     setup, idle unload, tests that every working model loads via the router, optionally
     Open WebUI and the old MCP tools; then remove Ollama + its 42 GB store if unneeded.
   - Original 5a brief: decide whether to use Ollama (Homebrew), alongside or instead
     of llama-server (user's decision, 2026-11-23). Benchmark both on the same
     edge/utility models: generation tok/s, prefill tok/s, time to first token, load time,
     memory use, and output sanity. Also check which catalog models Ollama can import and
     run (architectures, sharded files, --ple/mmproj), duplicate storage (set OLLAMA_MODELS
     to the T7), and whether Ollama would then need archiving for offline use (Stage 2).
