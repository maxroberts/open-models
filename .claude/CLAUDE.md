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
4. Integrity + backups: scheduled `om verify`, second archive copy, repo mirror into archive
5. Serving: OpenAI-compatible server, model switching (an earlier Ollama/Open WebUI/MCP
   setup is in `../local llm project.zip`, possibly reusable)
   - Decide here whether to use Ollama (Homebrew), alongside or instead of llama-server
     (user's decision, 2026-11-23). Ollama is not installed yet. Benchmark both on the same
     edge/utility models: generation tok/s, prefill tok/s, time to first token, load time,
     memory use, and output sanity. Also check which catalog models Ollama can import and
     run (architectures, sharded files, --ple/mmproj), duplicate storage (set OLLAMA_MODELS
     to the T7), and whether Ollama would then need archiving for offline use (Stage 2).
