# Model selection (November 2026)

Why each model in `catalog/models.yaml` was chosen, and what was checked. The catalog
itself is the source of truth for exact files, revisions, and hashes; this document is
the reasoning. Revisit it at each refresh ([REFRESH.md](REFRESH.md)). For choosing between
models (resources, speed, capability, safety), see [COMPARISON.md](COMPARISON.md).

## Requirements (from the owner)

- Several small models that run on anything from the **original 512 MB Raspberry Pi
  Model B** up to a **2012 MacBook Air**, plus Raspberry Pi 4/5 use.
- Several models that run on the **current machine** (MacBook Air M2, 16 GB; about
  10.7 GB usable by the GPU).
- Models for a future **128 GB** machine.
- **Frontier** open models for a future large machine: GLM-5.3, plus DeepSeek V4.1 Flash
  and GLM-5.3 Flash.
- **Coding** models and **embedding** models (for searching your own documents).
- Edge and utility tiers live on the T7 working store as well as the archive; everything
  else is archive-only (Starfish_Prime).

## How models were chosen

1. Leads came from web searches for current recommendations per hardware class. Those
   pages were mostly SEO aggregators with estimated speeds, so nothing here rests on them.
2. For each candidate, the Hugging Face API was queried for parameter count, license,
   gating, release date, and exact file sizes [1]. Licenses marked "other" were read in full.
3. Each GGUF's architecture (from the HF API) was checked against the architectures
   compiled into the installed llama.cpp (Homebrew 1.0.0, build 12359). 20 repos were
   checked directly, and all were present. The other six are siblings in families already
   checked (Qwen3.5 0.8B/2B/4B, Gemma 4 E4B, gpt-oss-20b, Qwen3 0.6B), and actually
   running the edge/utility models confirms them.
4. Model READMEs were scanned for minimum llama.cpp builds or special run instructions.
   The ones found are in the catalog `notes` and below.

Preferences: Apache-2.0/MIT licenses; GGUFs published by the model maker
(Google, Qwen, IBM, JetBrains, LiquidAI, ggml-org) where available, else unsloth's;
model families from several labs, so no single lab is a point of failure.

## The catalog by tier

Sizes are the files kept, in GB (10^9 bytes). All are GGUF.

### Edge: CPU only, up to ~4 GB RAM (T7 + archive)

| id | Size | Why |
|---|---|---|
| smollm2-135m-q8 | 0.14 | Sized for the original 512 MB Pi [2] |
| smollm2-360m-q8 | 0.39 | Upper limit for the 512 MB Pi [2] |
| qwen3.5-0.8b-q8 | 0.81 | Smallest current general model [3] |
| lfm3-1.7b-q4 | 1.10 | Designed for on-device use [4] |
| qwen3.5-2b-q4 | 1.28 | Default for Pi 4/5 [3] |
| smollm3-3b-q4 | 1.92 | Training data and recipe fully open [5] |
| qwen3.5-4b-q4 | 2.74 | Best quality for 4–8 GB machines [3] |
| gemma-4-e2b-qat | 3.35 | Second model family; Google's own quantization-aware build [6] |
| embeddinggemma-2-q8 | 0.31 | Embeddings (document search) [7] |
| qwen3-embedding-0.6b-q8 | 0.64 | Multilingual embeddings [8] |
| qwen3-0.6b-q8 | 0.64 | Pipeline test model from Stage 1 |
| glm-ocr-q8 | 1.43 | Reads text, tables and formulas from scanned documents; not a chat model (added 2026-11-24) [28] |

### Utility: this 16 GB M2 (T7 + archive)

| id | Size | Why |
|---|---|---|
| qwen3.5-9b-q4 | 6.60 | Most-recommended 16 GB model; includes vision adapter [3] |
| gemma-4-12b-qat | 6.98 | Strong generalist, Google build [6] |
| gemma-4-e4b-qat | 5.15 | Fast everyday model [6] |
| granite-4.2-8b-q4 | 5.35 | Tool use and document Q&A, IBM build [9] |
| mellum2.1-12b-q4 | 8.07 | Coding; JetBrains build; needs llama.cpp b11747+ [10] |
| glm-4.6v-flash-q4 | 7.95 | Z.ai vision model, so a GLM runs on this Mac; weaker at text-only answers (added 2026-11-24) [29] |

### Mid: ~24–128 GB machines (archive only)

| id | Size | Why |
|---|---|---|
| gpt-oss-20b-mxfp4 | 12.1 | Runs on 24 GB+; on this Mac only with a raised GPU memory limit [11] |
| gpt-oss-120b-mxfp4 | 63.4 | Fits 128 GB with room for long context [11] |
| qwen3.5-122b-a10b-q4xl | 77.9 | Largest Qwen that fits 128 GB [3] |
| qwen3.8-27b-q8 | 30.0 | Newest Qwen dense model (Aug 2026) [3] |
| qwen3.6-35b-a3b-q8 | 37.8 | Fast mixture-of-experts model, good for coding agents [3] |
| gemma-4-31b-q8 | 33.8 | Google's largest Gemma 4 [6] |
| qwen3-coder-next-q8 | 84.8 | Coding, 80B; Qwen's own build; run with `--jinja` [12] |
| glm-4.7-flash-q8 | 31.8 | Z.ai 30B MoE (3B active) for 32 GB+ machines; repeat penalty off, `--min-p 0.01` (added 2026-11-24) [30] |

### Frontier: ~256 GB+ (archive only)

| id | Size | Needs | Why |
|---|---|---|---|
| glm-5.3-q4xl | 467.3 | ~512 GB | 753B params; same base as GLM-5.2, with more post-training; Z.ai reports top open-weights coding results [13] |
| deepseek-v4.1-flash-q4xl | 460.2 | ~512 GB | 763B, MIT; a second lab as a hedge [14] |
| glm-5.3-flash-q4xl | 200.8 | ~256 GB | 321B; the most realistic next-machine frontier model [15] |

Catalog total: 1,555 GB, of which 54.9 GB is also on the T7.

## Things a reviewer should know

- **The three smaller GLM models (added 2026-11-24) were tested on this Mac** through
  `om serve` after download and hash check. glm-ocr-q8 read a two-line test image exactly
  ("Text Recognition:" prompt). glm-4.6v-flash-q4 answered a text question correctly and
  read the total and due date from the same image. glm-4.7-flash-q8 (mid tier, 31.8 GB) is
  too big for this Mac and was only hash-checked.

- **DeepSeek V4.1 Flash: shard 00008 is deliberately not kept.** It holds the model's
  "engram" table in MXFP8, which llama.cpp b12233 and newer reads as the wrong type and
  "gives wrong output without an error" [16]. We keep the Q6_K replacement table
  (161 GB) instead and must run with
  `--ple engram/DeepSeek-V4.1-Flash-1017-engram-Q6_K.gguf_file` [16]. Without `--ple`
  it fails to start, because shard 00008 is missing. This also saves 41 GB.
- **GLM-5.3's license** is MIT-style. Its one extra condition applies only to
  model-as-a-service operators with over $10B annual revenue [17].
  **LFM3's license** is free for use by companies under $10M annual revenue [4].
  All other models are Apache-2.0 or MIT.
- **The original Pi Model B is untested.** The SmolLM2 models are sized to fit its
  512 MB, but llama.cpp has not been built or run on ARMv6 here. A 2012 MacBook Air
  (Intel, AVX but no AVX2) also needs a CPU-only llama.cpp build. Archiving buildable
  llama.cpp source is Stage 2.
- **Considered and left out:**
  - Kimi K3 / K3.1 Pro: 2.78T parameters [18], over 1.5 TB even at 4-bit (estimate).
  - DeepSeek V4 Pro: 1.6T parameters [1].
  - Qwen3.8 Flash-Next: gated, custom license [1].
  - Gemma 3 270M: gated [1].
  - Devstral Small 2: Mellum 2.1 and the Qwen coders cover coding.
- **No original full-precision weights are kept**, only quantized GGUFs. That means no
  re-quantizing later from originals; the GLM-5.3 originals alone would be 750 GB (FP8)
  to 1.5 TB (BF16).

## How close is the best of this archive to Claude Opus 5.5?

**Short answer: GLM-5.3 is the closest model in the catalog, and it is clearly behind
Opus 5.5.** DeepSeek V4.1 Flash is in the same open-weights tier; no direct comparison
of it with Opus 5.5 was found. Everything else in the catalog is further behind.

- **Benchmarks.** Artificial Analysis (both models at maximum effort) [20]:

  | Measure | Opus 5.5 | GLM-5.3 |
  |---|---|---|
  | Intelligence Index | 59 | 32 |
  | Terminal-Bench 4.0 | 59.6% | 41.9% |
  | HLE-Diamond | 67.9% | 17.9% |
  | FrontierCode-AA 2.0 | 46.4% | 21.6% |
  | AutomationBench-AA | 69.5% | 62.2% |

  AutomationBench is the closest result. LLM Stats gives 58.0 vs 49.3, with Opus ahead in
  its reasoning, coding, agents, and tool-use categories; GLM-5.3 wins one shared
  benchmark there (AutomationBench) [21]. Z.ai's own table compares GLM-5.3 against
  Opus 4.8, not 5.5, and has it level with or ahead of Opus 4.8 on most of its coding
  and agent benchmarks [13]. So it is about a generation behind.
- **Our copies are a little weaker than the benchmarked models.** Benchmarks use
  full-precision weights. The archive holds 4-bit quantizations, which usually cost some
  quality, most on hard reasoning.
- **Even hosted, GLM-5.3 is slower.** Artificial Analysis measures its API output at
  57–68 tok/s, against 104–114 tok/s for Opus 5.5 [20].

## What a local machine needs to feel like Opus 5.5

**What "the feel" means, in numbers.** Opus 5.5 streams about **104–114 output tok/s**
(including thinking tokens) [19][20]. Time to first answer token, which includes its
thinking, is about **13 s at medium effort and 22.5 s at high** [19]. In agentic coding,
a second factor matters as much: how fast the machine reads a long prompt (*prefill*).
Each turn re-sends tens of thousands of tokens of context.

**What sets local speed.**
- **Generation speed is limited by memory bandwidth.** Each generated token reads the
  model's *active* weights once. GLM-5.3 activates about 40B of its 753B parameters per
  token (its expert layout is the same as GLM-5's, which Z.ai states as 744B total / 40B
  active) [13][22]. At our UD-Q4_K_XL size (4.96 bits per parameter on average), that is
  about 25 GB read per token. Upper bound: tok/s ≤ bandwidth ÷ 25 GB.
- **Prefill is limited by raw compute**, which is where GPUs far outrun Apple Silicon.

**Options, from cheapest to closest to Opus.** Figures are marked *measured*
(someone ran it) or *estimate*.

| Setup | Model and format | Generation | Prefill | Feel vs Opus 5.5 |
|---|---|---|---|---|
| **Mac Studio M5 Ultra, 256 GB** [23] | GLM-5.3 Flash UD-Q4_K_XL (201 GB, in archive); 18B active [15] | *Estimate:* ~40–55 tok/s (bandwidth bound ~106) | *Estimate:* low hundreds of tok/s | Fast enough to read along, but long contexts take minutes to start. Weaker model: Z.ai says it "approaches Claude Opus 4.8" [15] |
| **Mac Studio M5 Ultra, 512 GB** [23] | GLM-5.3, but the archived Q4 (467 GB) only just fits, after raising macOS's GPU memory limit to ~472 GB [24][25]; UD-Q3_K_XL (343 GB) or UD-IQ4_XS (365 GB) are the practical choices | *Measured on the previous M3 Ultra (MLX 4-bit GLM-5/5.2, second-hand):* 11–18 tok/s. *Estimate for M5 Ultra:* ~26 tok/s [24]. Bandwidth bound ~48 [23] | *Measured on M3 Ultra:* 78–214 tok/s [24] | About ¼ of Opus's generation speed. A 32K-token prompt takes about 2.5–7 min to read the first time. Workable for chat; slow for agentic coding |
| **8× NVIDIA RTX PRO 6000 Blackwell (96 GB each, 768 GB total)**, SGLang or vLLM | GLM-5 / 5.1 NVFP4 with MTP speculative decoding, *measured* [26]. For GLM-5.3: NVIDIA's NVFP4 build (464 GB, **not in the archive**) [27] | *Measured:* ~95 tok/s at short context, ~68–78 tok/s at 128K. ~50 tok/s without MTP | *Measured:* ~3,200–4,300 tok/s | **Close to Opus 5.5's speed.** A 32K prompt is read in about 8–10 s. Quality is still GLM-5.3's, not Opus's |

**Resources for the "Opus feel" option** (the 8-GPU route). The measured setup [26] needs:
- **Memory:** at least ~500 GB of GPU memory, enough for the ~440–464 GB 4-bit weights
  plus a long-context cache. The measured setup used 768 GB. 4× 96 GB GPUs is not enough,
  and 6 GPUs is the "less tested" minimum.
- **Compute and format:** NVIDIA Blackwell GPUs (FP4 tensor cores) running an NVFP4
  checkpoint in SGLang or vLLM. Not llama.cpp/GGUF: the archive's GGUF copy is the wrong
  format for this route.
- **Speculative decoding (MTP):** it roughly doubles generation speed in those tests
  (51.6 → 95.1 tok/s).
- **Power and cooling:** GPUs alone draw up to ~4.8 kW during prefill [26]. This needs
  dedicated high-power circuits and server-grade cooling: a server room or garage, not a desk.
- **Host:** a server or workstation board with eight GPU slots, running Linux, with fast
  NVMe storage. In the measured setup the weights load in about 36 s, but full startup
  takes 7–8 min.
- **Cost was not researched.** It is server-class.

**Middle grounds.**
- On a Mac, keep the context short and rely on prompt caching. llama.cpp's server reuses
  the already-processed prefix, so only new tokens pay the slow prefill cost.
- A 256 GB Mac running GLM-5.3 Flash is the most responsive single-box option, at the
  cost of a weaker model.
- **Archive gap:** to be ready for the GPU route without internet, the archive would also
  need the NVFP4 build of GLM-5.3 (464 GB). Its license adds the NVIDIA Open Model
  Agreement on top of the GLM-5.3 license [27]. **TODO (deferred, 2026-11-23):** add
  `nvidia/GLM-5.3-NVFP4` to the catalog (frontier tier, `safetensors`) when we commit to
  the GPU route or have archive space to spare.

**Same model, not quite the same answers.** Across these setups the model is the same,
but the quality is not guaranteed to be identical:
- **Quantization differs.** The Mac options run 3- or 4-bit GGUF builds, and the GPU
  route runs NVIDIA's NVFP4 build. Each rounds the original weights differently, and
  lower-bit builds (such as the 3-bit one a 512 GB Mac needs) usually lose more. No
  side-by-side quality comparison of these builds was found; this is general experience
  with quantization, not a measurement.
- **Speed changes what is practical.** At ~26 tok/s, long thinking and long agentic
  runs take several times longer, so in practice you may give the model less room.
- **MTP should not change answers.** Speculative decoding checks every drafted token
  against the full model, so by design it changes speed, not output quality.
- **Runtimes can have bugs.** A new model may be handled incorrectly by one runtime and
  not another (see the DeepSeek engram case above), so test outputs, not just speed.

The Mac figures are second-hand: no llama.cpp/GGUF measurement of GLM-5.x on a Mac was
found [24][25]. Verify with `llama-bench` on real hardware before buying.

## References

1. Hugging Face model API (parameter counts, licenses, gating, file sizes), e.g. https://huggingface.co/api/models/zai-org/GLM-5.3
2. SmolLM2 GGUFs: https://huggingface.co/bartowski/SmolLM2-135M-Instruct-GGUF, https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF
3. Qwen models and GGUFs: https://huggingface.co/Qwen, https://huggingface.co/unsloth (e.g. https://huggingface.co/unsloth/Qwen3.5-9B-GGUF)
4. LFM3 1.7B GGUF, README and LICENSE: https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF
5. SmolLM3 3B: https://huggingface.co/HuggingFaceTB/SmolLM3-3B
6. Gemma 4 GGUFs: https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf (and E2B / E4B siblings), https://huggingface.co/unsloth/gemma-4-31B-it-GGUF
7. EmbeddingGemma 2 GGUF: https://huggingface.co/ggml-org/embeddinggemma-2-GGUF
8. Qwen3 Embedding 0.6B GGUF: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF
9. Granite 4.2 8B GGUF: https://huggingface.co/ibm-granite/granite-4.2-8b-GGUF
10. Mellum 2.1 GGUF (README states the llama.cpp b11747 requirement): https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking-GGUF
11. gpt-oss GGUFs: https://huggingface.co/ggml-org/gpt-oss-20b-GGUF, https://huggingface.co/ggml-org/gpt-oss-120b-GGUF
12. Qwen3-Coder-Next GGUF: https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF
13. GLM-5.3 model card: https://huggingface.co/zai-org/GLM-5.3. GGUF: https://huggingface.co/unsloth/GLM-5.3-GGUF
14. DeepSeek V4.1 Flash: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash. GGUF: https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF
15. GLM-5.3 Flash: https://huggingface.co/zai-org/GLM-5.3-Flash. GGUF: https://huggingface.co/unsloth/GLM-5.3-Flash-GGUF
16. DeepSeek V4.1 Flash engram notes: https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF/blob/main/engram/README.md
17. GLM-5.3 license: https://huggingface.co/zai-org/GLM-5.3/blob/main/LICENSE
18. Kimi K3: https://huggingface.co/moonshotai/Kimi-K3
19. Artificial Analysis, Claude Opus 5.5 model pages (output speed, time to first answer token; 5-day rolling averages via Anthropic's API): https://artificialanalysis.ai/models/claude-opus-5-5-medium, https://artificialanalysis.ai/models/claude-opus-5-5-high
20. Artificial Analysis, Claude Opus 5.5 vs GLM-5.3 (Intelligence Index v5.0.1, per-benchmark scores, output speed): https://artificialanalysis.ai/models/comparisons/claude-opus-5-5-vs-glm-5-3
21. LLM Stats, Claude Opus 5.5 vs GLM-5.3 (page dated 2026-11-23): https://llm-stats.com/models/compare/claude-opus-5-5-vs-glm-5.3
22. GLM-5 and GLM-5.3 configs (identical expert layout: 78 layers, 256 routed experts, 8 per token, 1 shared): https://huggingface.co/zai-org/GLM-5/blob/main/config.json, https://huggingface.co/zai-org/GLM-5.3/blob/main/config.json. GLM-5 model card (744B total / 40B active): https://huggingface.co/zai-org/GLM-5
23. Apple, Mac Studio (2026) tech specs (M5 Ultra: up to 512 GB, 1.2 TB/s; M5 Max: up to 128 GB, 614 GB/s): https://support.apple.com/128107
24. Pinggy, "Self-Hosting LLMs on the 512GB M5 Ultra Mac Studio" (2026-09-01). Second-hand M3 Ultra MLX measurements of GLM-5/5.2, an M5 Ultra estimate, and wired-memory limit settings: https://pinggy.io/blog/self_hosting_llms_on_512gb_m5_ultra_mac_studio/
25. Unsloth GLM-5.3 GGUF discussion, "512GB Mac Studio benchmark?" (no measured GGUF results; Q4/Q3 sizes; `iogpu.wired_limit_mb`): https://huggingface.co/unsloth/GLM-5.3-GGUF/discussions/7
26. local-inference-lab, GLM-5 on 8× RTX PRO 6000 (SGLang/vLLM, NVFP4, MTP; decode, prefill, power; March–May 2026): https://github.com/local-inference-lab/rtx6kpro/blob/master/models/glm5.md, https://github.com/local-inference-lab/rtx6kpro/blob/master/benchmarks/results.md
27. NVIDIA GLM-5.3 NVFP4 (464 GB; NVIDIA Open Model Agreement + GLM-5.3 License): https://huggingface.co/nvidia/GLM-5.3-NVFP4
28. GLM-OCR: https://huggingface.co/zai-org/GLM-OCR (0.9B, MIT, prompt formats). GGUF: https://huggingface.co/ggml-org/GLM-OCR-GGUF
29. GLM-4.6V-Flash: https://huggingface.co/zai-org/GLM-4.6V-Flash (9B, 128K context, MIT, stated limitations). GGUF: https://huggingface.co/unsloth/GLM-4.6V-Flash-GGUF
30. GLM-4.7-Flash: https://huggingface.co/zai-org/GLM-4.7-Flash (30B-A3B, MIT, benchmarks). GGUF and recommended settings: https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF
