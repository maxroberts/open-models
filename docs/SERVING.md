# Serving: Ollama or llama-server?

Stage 5a. Should open-models serve models through Ollama (Homebrew), through llama.cpp's
own `llama-server`, or both? This compares them on this Mac with the catalog's own files.
**Status: compatibility results are final. Speed results are preliminary**, because the
Mac was short of memory during the main run (see "Caveat" below). A rerun with memory
freed up is pending.

## Short answer

- **Ollama 0.40.18 is a wrapper around llama.cpp.** For a GGUF model it starts its own
  bundled `llama-server` (build 12651, newer than our pinned 12359) and passes requests
  to it. It also bundles Apple's MLX engine, which these GGUF models did not use. At
  matched settings, the two servers come out about the same wherever the Mac had free
  memory. They are the same engine, and differences come from the llama.cpp build and
  from Ollama's own defaults and chat templates.
- **Every working-store model runs on Ollama**, including embeddings and vision. On
  llama-server, the benchmarked models ran; the rest are 5b's job. The differences are
  elsewhere:
  - **Ollama** makes its own copy of every model (42 GB for the 16 working models) and
    cannot pass extra llama.cpp flags. So DeepSeek V4.1, which needs `--ple`, cannot
    run on it.
  - **llama-server** is the build we archive and can rebuild offline on all four target
    machines (docs/OFFLINE.md). It loads files directly from the `om` stores and accepts
    any flag.
- **Preliminary recommendation: serve with llama-server; Ollama is optional.**
  llama-server's built-in "router" mode (`--models-dir`, `--models-preset`) can switch
  models on demand, which is the main thing Ollama adds. That still has to be tried in
  5b. Keep Ollama only if a tool you want needs Ollama's own API. If you do, the Ollama
  binaries would also need archiving for offline use.

## Setup

| | llama-server | Ollama |
|---|---|---|
| Version | 1.0.0, build 12359 (Homebrew; same as the archived build) | 0.40.18 (Homebrew), bundling llama.cpp build 12651 |
| Model files | read in place from the working store (`om path`) | copied into its store by `ollama create` (`FROM <gguf>`) |
| Settings | `-c 4096 -ngl 999 -fa on -np 1` | `num_ctx 4096`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_NUM_PARALLEL=1` |

Both: f16 KV cache, temperature 0, thinking off, one request at a time. Machine: MacBook
Air M2, 16 GB, macOS 26.6. Ollama's store: `OLLAMA_MODELS=/Volumes/BackUp_T7/lm-storage/ollama`.

Method, in `scripts/bench_serving.py`:
- **Warm runs:** three per model and server. Each sends the same ~600-token passage
  with "summarize it" and generates up to 200 tokens. A different first line each run
  stops either server from reusing a cached prompt. Medians are reported.
- **Time to first token:** measured by the client.
- **Prefill and generation speed:** as reported by each server.
- **Cold start:** for llama-server, from process start to the first token. For Ollama,
  from the request to the first token with the model unloaded.
- **Memory:** resident memory of the server and all its child processes.
- **Sanity:** a one-word question ("capital of France").

Raw results: `docs/benchmarks/serving-2026-11-24.jsonl` (main run) and
`serving-2026-11-24-trial.jsonl` (an earlier single-run trial).

## Speed (preliminary)

Main run, 2026-11-24 (3 warm runs each):

| Model | Server | Cold start s | First token s | Prefill tok/s | Generate tok/s | Resident MB |
|---|---|---|---|---|---|---|
| lfm3-1.7b-q4 (1.1 GB) | llama-server | 2.6 | 0.81 | 734 | 67.0 | 1307 |
| | Ollama | 2.1 | 0.80 | 746 | 65.3 | 1270 |
| qwen3.5-4b-q4 (2.7 GB) | llama-server | 9.8 | 3.89 | 148 | 12.7 | 1068 |
| | Ollama | 6.9 | 3.10 | 185 | 15.4 | 3228 |
| gemma-4-e4b-qat (5.2 GB) | llama-server | 10.4 | 1.22 | 486 | 26.1 | 5129 |
| | Ollama | 10.3 | 2.00 | 295 | 15.9 | 4955 |
| granite-4.2-8b-q4 (5.4 GB) | llama-server | 11.6 | 8.97 | 63 | 12.4 | 5564 |
| | Ollama | 10.8 | 7.01 | 83 | 6.4 | 5540 |
| qwen3.5-9b-q4 (5.7 GB) | llama-server | 12.7 | 7.89 | 72 | 6.9 | 5314 |
| | Ollama | 19.1 | 11.39 | 50 | 4.5 | 784 |

Trial run earlier the same morning, with more free memory (1 warm run each):

| Model | Server | First token s | Prefill tok/s | Generate tok/s |
|---|---|---|---|---|
| smollm2-360m-q8 | llama-server | 0.28 | 2139 | 143.4 |
| | Ollama | 0.21 | 2835 | 144.0 |
| qwen3.5-4b-q4 | llama-server | 2.28 | 250 | 25.7 |
| | Ollama | 2.07 | 277 | 25.4 |

All runs on both servers gave sensible summaries and answered "Paris".

### Caveat: memory pressure

During the main run, swap use reached 13.2 of 14.3 GB, so the Mac was paging heavily.
Most of the memory belonged to other processes: `rpcsvchost` held 6.7 GB (nearly all
compressed or swapped), Spotlight's `mds` 1.3 GB, and VS Code, Notes, Safari and Dropbox
about 1 GB each. The symptoms:
- qwen3.5-4b generated at 12.7 tokens/s in the main run against 25.7 in the trial.
- Resident memory for Ollama's 9B was 784 MB, which means its weights had been paged out.
- Neither server was consistently faster; the gaps swung both ways from model to model.

So the 4–9B rows measure memory pressure more than the servers. Only lfm3-1.7b in the
main run and both trial models had enough room, and there the servers are within a few
percent on generation speed. Ollama was ahead on prefill and first token in those cases.

**To do:** rerun `scripts/bench_serving.py` on the same five models after a restart, with
other apps closed, and replace this section.

## Compatibility

Each model was imported into Ollama with a Modelfile `FROM <file>` and asked the sanity
question.

| Case | Ollama | llama-server (Homebrew build 12359) |
|---|---|---|
| All 14 working-store chat models | all run and answer correctly | 7 have run correctly (6 in this benchmark, smollm2-135m in the Stage 2 offline check); the other 7 were not tried |
| Embedding models (embeddinggemma-2, qwen3-embedding-0.6b) | work (`/api/embed`; cat~kitten 0.92 / 0.91, cat~tax 0.63 / 0.43) | not tried here (`--embedding`) |
| Vision (`qwen3.5-9b-q4` + `mmproj-F16.gguf`) | works with two `FROM` lines; it passes `--mmproj` to its llama-server and named a red test image "Red" | not tried here (`--mmproj`) |
| Split GGUF (the frontier models) | understood: given shard 00001 alone it refused ("has 1 shards, expected 6"), so it looks for the siblings; importing the full set would copy them all | not tried here; llama.cpp loads shard 00001 and finds the rest |
| DeepSeek V4.1 (shard 8 left out, `--ple` table) | **cannot run**: the import would refuse the missing shard, and there is no per-model way to pass `--ple` (`LLAMA_ARG_SHARD` on the server would apply to every model) | not tried here (needs ~512 GB RAM); `--ple` is in this build's `--help` |

Split handling was tested only by importing GLM-5.3 Flash's 9 MB first shard on its own.
The frontier models need far more memory than this Mac has. The untested llama-server
cases go into 5b's tests.

## Storage and offline use

- **Duplicate files:** Ollama stores its own copy of every imported file, under its
  sha256. Importing the 16 working models took 42 GB on the T7. A vision variant reuses
  the base model's weights instead of storing them twice. llama-server reads the
  catalog's files in place.
- **Unplugged drive:** if the T7 is unplugged, Ollama refuses to start ("mkdir
  /Volumes/...: permission denied"). It does not fall back to the internal disk, because
  `/Volumes` belongs to root. Missing folders on a writable path are created without a
  warning.
- **Ollama outside open-models:** models pulled with `ollama pull` land in the same store.
  They are not in the catalog, not checked by `om verify`, and not archived.
- **Offline rebuild:** Ollama is not in the runtime archive. The Homebrew bottle is about
  69 MB, plus 171 MB for MLX. It would also need to be archived for each target, and
  whether Ollama supports the 2012 MacBook Air (macOS 10.15) or the original Pi (ARMv6)
  is unchecked. llama-server is already archived and builds on all four.
- **Network:** Ollama creates `~/.ollama/id_ed25519` (its ollama.com sign-in key) on first
  run, and its cloud features are on unless `OLLAMA_NO_CLOUD=1` is set.

## Using the chat from another computer

Until 5b adds `om serve` and a login service, start the server by hand. Router mode
lists every working-store model under its catalog id and loads the one a request names,
one at a time (`--models-max 1`):

```bash
llama-server --models-dir /Volumes/BackUp_T7/lm-storage/models --models-max 1 -c 8192 \
  --host 0.0.0.0 --port 8080 --api-key-file ~/.config/open-models/llama-server.key
```

Then open `http://<this Mac's address>:8080` from any computer on the home network
(`http://192.168.0.50:8080` on 2026-11-24). Tested that day against that network address (from this Mac): the
page loads, API requests without the key are refused (401), and with the key
qwen3.5-4b answered correctly.

- **The API key** is in `~/.config/open-models/llama-server.key`, readable only by you
  (created 2026-11-24 with `secrets.token_urlsafe(24)`). Show it with
  `cat ~/.config/open-models/llama-server.key`. It is not in the repo. To change it,
  edit the file and restart the server.
- **First visit from a browser:** the page shows "Server Connection Error: Access
  denied". That is expected. The page has no key yet, and its first request (`/props`)
  is refused. Click the button below the message, paste the key into **API Key**, then
  **Save & Retry**. The page checks the key, stores it in that browser, and opens the
  chat. This was confirmed in use on 2026-11-24. Only the page itself and `/health` are
  open without the key; every API call needs it.
- **Other tools** (Open WebUI, scripts) use the same key as an OpenAI-style bearer token:
  `Authorization: Bearer <key>`, base URL `http://<address>:8080/v1`.
- **Home network only.** The connection is plain HTTP, so the key is not encrypted in
  transit. Never forward this port to the internet on the router. This Mac's firewall
  was off on 2026-11-24, so nothing else blocks the port.
- **No key, no network exposure:** start the server without `--host`/`--api-key-file`
  (it then listens on this Mac only) and use VS Code's port forwarding (Ports tab) or
  `ssh -L 8080:localhost:8080 <this Mac>`. Then open `http://localhost:8080` on your
  own computer.
- **Limits until 5b:** the server stops when the terminal or session that started it
  ends, and it doesn't start at login. Vision and embedding models load without the
  flags they need (`--mmproj`, `--embedding`), so image input and embeddings don't work
  yet.

## Current state of this machine

- An API key for the network chat is in `~/.config/open-models/llama-server.key`.
- Ollama 0.40.18 is installed with Homebrew, but not as a background service. The
  benchmark ran `ollama serve` by hand with the settings above.
- The 16 working models, plus a vision variant, are imported into
  `/Volumes/BackUp_T7/lm-storage/ollama` (42 GB) as `om-<id>`. They can be removed with
  `ollama rm` if Ollama is dropped.
