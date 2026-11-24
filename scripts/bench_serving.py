"""Benchmark llama.cpp's `llama-server` against Ollama on the same catalog models (Stage 5a).

Summary: for each model id, starts each server on the same GGUF file with matched
settings, then measures cold start, time to first token, prefill and generation speed,
memory, and a one-word sanity answer. Writes one JSON line per (model, engine) and
prints a table. Used to decide whether open-models serves through Ollama, llama-server
or both (docs/SERVING.md records the results and the decision).

Details:
- Models come from `om path <id>` (working store first), so run it with the repo's
  venv: `.venv/bin/python scripts/bench_serving.py qwen3.5-4b-q4 ...`.
- Matched settings on both engines: context 4096, all layers on the GPU, flash
  attention on, f16 KV cache, one request at a time, temperature 0, thinking off
  (`enable_thinking: false` for llama-server, `think: false` for Ollama).
- llama-server is started fresh per model (`--port 18080`). Ollama must already be
  running (`ollama serve`, default port 11434, with OLLAMA_FLASH_ATTENTION=1 and
  OLLAMA_NUM_PARALLEL=1 to match). Each model is imported into Ollama as
  `om-<id>` with a Modelfile `FROM <gguf>` if it isn't there yet. Ollama copies the
  file into its own store (OLLAMA_MODELS), so the import costs disk space.
- Cold start: llama-server, from process start to the first streamed token of a short
  request (includes its warm-up run). Ollama, from request to first token with the
  model unloaded (the server process is already up). Both are what a user waits for.
- Warm runs (default 3): the same ~600-token passage plus "summarize it", up to 200
  new tokens, streamed. Each run starts with a different `Run N.` line, so neither
  server can reuse a cached prompt. Time to first token is measured on the client.
  Prefill and generation tok/s come from each server's own timings (llama-server's
  `timings` in the final chunk, Ollama's `prompt_eval_*` / `eval_*`). Medians reported.
- Memory, summed over the server process and all its descendants after the warm runs:
  resident memory (RSS, includes the weights, which are mapped from the file) and the
  macOS physical footprint (excludes those file-backed pages, so roughly KV cache and
  compute buffers).
- Sanity: "What is the capital of France? Answer with one word." passes if the reply
  contains "Paris". The summary text from the last warm run is kept for reading.
- Errors for one model/engine are recorded in the JSON line and the run moves on.
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LLAMA_PORT = 18080
OLLAMA_URL = "http://127.0.0.1:11434"
CTX = 4096
MAX_TOKENS = 200

PASSAGE = (
    "The Raspberry Pi is a series of small single-board computers developed in the "
    "United Kingdom by the Raspberry Pi Foundation in association with Broadcom. The "
    "original model became popular far beyond its intended market of computer science "
    "teaching, for uses such as robotics, home automation and media centres. It does "
    "not include peripherals such as keyboards and mice or cases. Later models added "
    "faster processors, more memory, wireless networking and Bluetooth, and support for "
    "64-bit operating systems. "
) * 6
SUMMARY_PROMPT = PASSAGE + "\nSummarize the text above in three sentences."
SANITY_PROMPT = "What is the capital of France? Answer with one word."


def post_stream(url, body, timeout=600):
    """POST `body` as JSON and yield (arrival time, parsed JSON) for each streamed event.

    Handles both Server-Sent Events (`data: {...}` lines, llama-server's OpenAI API)
    and newline-delimited JSON (Ollama's native API).
    """
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if line.startswith("data:"):
                line = line[5:].strip()
            if not line or line == "[DONE]":
                continue
            yield time.perf_counter(), json.loads(line)


def chat_llama(prompt, max_tokens):
    """Stream one chat request to llama-server; return (ttft_s, text, prefill_tps, gen_tps)."""
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens,
            "temperature": 0, "stream": True,
            "chat_template_kwargs": {"enable_thinking": False}}
    t0, first, text, timings = time.perf_counter(), None, "", {}
    for t, ev in post_stream(f"http://127.0.0.1:{LLAMA_PORT}/v1/chat/completions", body):
        delta = (ev.get("choices") or [{}])[0].get("delta", {}).get("content") or ""
        if delta and first is None:
            first = t
        text += delta
        timings = ev.get("timings", timings)
    return ((first or time.perf_counter()) - t0, text,
            timings.get("prompt_per_second"), timings.get("predicted_per_second"))


def chat_ollama(model, prompt, max_tokens):
    """Stream one chat request to Ollama; return (ttft_s, text, prefill_tps, gen_tps)."""
    body = {"model": model, "messages": [{"role": "user", "content": prompt}],
            "stream": True, "think": False,
            "options": {"num_ctx": CTX, "num_predict": max_tokens, "temperature": 0}}
    t0, first, text, final = time.perf_counter(), None, "", {}
    for t, ev in post_stream(f"{OLLAMA_URL}/api/chat", body):
        delta = ev.get("message", {}).get("content") or ""
        if delta and first is None:
            first = t
        text += delta
        if ev.get("done"):
            final = ev

    def rate(n, ns):
        return n / (ns / 1e9) if n and ns else None

    return ((first or time.perf_counter()) - t0, text,
            rate(final.get("prompt_eval_count"), final.get("prompt_eval_duration")),
            rate(final.get("eval_count"), final.get("eval_duration")))


def descendants(pid):
    """`pid` and all processes below it (Ollama's model runner is a child of `ollama serve`)."""
    kids = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
    return [str(pid)] + [d for k in kids for d in descendants(k)]


def memory_mb(pid):
    """Memory of `pid` plus all its descendants, in MB: (resident, physical footprint).

    Resident (RSS, from `ps`) includes the model weights, which llama.cpp maps straight
    from the file. The footprint (macOS `footprint`) leaves those file-backed pages out,
    so it shows roughly what the server allocates beyond the weights (KV cache,
    compute buffers).
    """
    rss = footprint = 0.0
    for p in descendants(pid):
        rss += int(subprocess.run(["ps", "-o", "rss=", "-p", p], capture_output=True,
                                  text=True).stdout.strip() or 0) / 1024
        out = subprocess.run(["footprint", "-p", p], capture_output=True, text=True).stdout
        m = re.search(r"Footprint:\s*([\d.]+)\s*(KB|MB|GB)", out)
        if m:
            footprint += float(m.group(1)) * {"KB": 1 / 1024, "MB": 1, "GB": 1024}[m.group(2)]
    return round(rss), round(footprint)


def measure(chat, runs):
    """Run the warm runs and sanity check with `chat(prompt, max_tokens)`; return a dict."""
    ttfts, prefill, gen, text = [], [], [], ""
    for i in range(runs):
        ttft, text, p, g = chat(f"Run {i + 1}.\n" + SUMMARY_PROMPT, MAX_TOKENS)
        ttfts.append(ttft)
        prefill += [p] if p else []
        gen += [g] if g else []
    sanity = chat(SANITY_PROMPT, 16)[1]

    def med(xs):
        return round(statistics.median(xs), 2) if xs else None

    return {"ttft_s": med(ttfts), "prefill_tps": med(prefill), "gen_tps": med(gen),
            "sanity_ok": "paris" in sanity.lower(), "sanity": sanity.strip()[:80],
            "summary": text.strip()}


def bench_llama(gguf, runs):
    """Start llama-server on `gguf`, measure it, stop it; return a result dict."""
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        ["llama-server", "-m", gguf, "--port", str(LLAMA_PORT),
         "-c", str(CTX), "-ngl", "999", "-fa", "on", "-np", "1", "--no-webui"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        while True:  # wait for /health, then time the first token of a short request
            if proc.poll() is not None:
                raise RuntimeError(f"llama-server exited with {proc.returncode}")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{LLAMA_PORT}/health", timeout=1)
                break
            except OSError:
                time.sleep(0.2)
        chat_llama("Hi", 1)
        cold = time.perf_counter() - t0
        result = measure(chat_llama, runs)
        rss, fp = memory_mb(proc.pid)
        result |= {"cold_start_s": round(cold, 2), "rss_mb": rss, "footprint_mb": fp}
        return result
    finally:
        proc.terminate()
        proc.wait()


def ollama_api(path, body):
    """POST to Ollama's native API (non-streaming) and return the parsed reply."""
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read() or b"{}")


def ollama_pid():
    """PID of the running `ollama serve` process (exact process name, not a shell wrapper)."""
    out = subprocess.run(["pgrep", "-x", "ollama"], capture_output=True, text=True).stdout
    return int(out.split()[0])


def bench_ollama(model_id, gguf, runs, workdir):
    """Import `gguf` into Ollama if needed, measure it, unload it; return a result dict."""
    name = f"om-{model_id}"
    tags = {m["name"].split(":")[0] for m in ollama_api_get("/api/tags")["models"]}
    if name not in tags:
        modelfile = workdir / f"{name}.Modelfile"
        modelfile.write_text(f"FROM {gguf}\n")
        subprocess.run(["ollama", "create", name, "-f", str(modelfile)], check=True,
                       capture_output=True, text=True)
    ollama_api("/api/generate", {"model": name, "keep_alive": 0})  # make sure it's unloaded
    time.sleep(1)
    t0 = time.perf_counter()
    chat_ollama(name, "Hi", 1)
    cold = time.perf_counter() - t0
    try:
        result = measure(lambda p, n: chat_ollama(name, p, n), runs)
        rss, fp = memory_mb(ollama_pid())
        result |= {"cold_start_s": round(cold, 2), "rss_mb": rss, "footprint_mb": fp}
        return result
    finally:
        ollama_api("/api/generate", {"model": name, "keep_alive": 0})


def ollama_api_get(path):
    """GET from Ollama's native API and return the parsed reply."""
    with urllib.request.urlopen(f"{OLLAMA_URL}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def main():
    """Parse arguments, benchmark each model on each engine, write JSON lines, print a table."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("ids", nargs="+", help="catalog model ids (must have a .gguf in a store)")
    ap.add_argument("--engines", default="llama,ollama")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", type=Path, required=True, help="JSON lines file to append to")
    args = ap.parse_args()
    om = Path(sys.executable).parent / "om"
    workdir = args.out.parent
    workdir.mkdir(parents=True, exist_ok=True)

    cols = ["cold_start_s", "ttft_s", "prefill_tps", "gen_tps", "rss_mb", "footprint_mb", "sanity_ok"]
    print(f"{'model':24} {'engine':7} " + " ".join(f"{c:>12}" for c in cols))
    for model_id in args.ids:
        gguf = subprocess.run([str(om), "path", model_id], check=True, capture_output=True,
                              text=True).stdout.strip()
        for engine in args.engines.split(","):
            try:
                r = bench_llama(gguf, args.runs) if engine == "llama" else \
                    bench_ollama(model_id, gguf, args.runs, workdir)
            except Exception as e:  # record and move on to the next model/engine
                r = {"error": f"{type(e).__name__}: {e}"}
            r = {"model": model_id, "engine": engine, "date": time.strftime("%Y-%m-%d"), **r}
            with args.out.open("a") as f:
                f.write(json.dumps(r) + "\n")
            print(f"{model_id:24} {engine:7} " +
                  (" ".join(f"{str(r.get(c)):>12}" for c in cols) if "error" not in r
                   else r["error"][:100]), flush=True)


if __name__ == "__main__":
    main()
