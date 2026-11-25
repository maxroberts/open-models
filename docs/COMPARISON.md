# How the catalog's models compare

A side-by-side view of the 29 models in `catalog/models.yaml` on four dimensions: resource
needs, speed, capability, and safety and limitations. [MODELS.md](MODELS.md) explains why
each model was chosen; this document is for choosing between them.

**Status (2026-11-24): research done, local speed measurements pending.** Speed figures
below are estimated ceilings (see "Speed"), apart from two trial measurements. The 18
models on this Mac will be measured after a restart. Memory pressure (swap nearly full)
makes measurements taken now unreliable; see SERVING.md, "Caveat: memory pressure".

## How to read this

- **Maker's own numbers vs independent ones.** Most capability figures come from each
  model's card and are **self-reported** by its maker, who chose the benchmarks and the
  settings. They are useful within a family. Across makers they are only a rough guide,
  because labs run the same benchmark differently. The one independent score used here is
  Artificial Analysis's Intelligence Index [1][2]. It covers only 9 of these models.
- **Our copies are quantized.** Benchmarks are run on full-precision weights. The archive
  keeps 4- to 8-bit GGUF builds, which usually cost a little quality, most on hard
  reasoning. No model here was benchmarked by us for quality.
- **"Thinking" models** reason in hidden text before answering. They score higher but are
  slower to answer. Most of the chat models here think by default.
- **Embedding models** (embeddinggemma-2, qwen3-embedding-0.6b) turn text into vectors for
  search; they don't chat. They have their own section at the end.

## At a glance

| Tier | Model | Maker | Size on disk | Runs on | Good for |
|---|---|---|---|---|---|
| edge | smollm2-135m-q8 | Hugging Face | 0.14 GB | anything, incl. original Pi | demos, very simple text |
| edge | smollm2-360m-q8 | Hugging Face | 0.39 GB | anything, incl. original Pi | simple English text |
| edge | qwen3-0.6b-q8 | Qwen (Alibaba) | 0.64 GB | anything | pipeline test model |
| edge | qwen3.5-0.8b-q8 | Qwen | 0.81 GB | Pi 4/5 and up | tiny multilingual + images |
| edge | lfm3-1.7b-q4 | Liquid AI | 1.10 GB | Pi 4/5 and up | tool calling, structured output |
| edge | qwen3.5-2b-q4 | Qwen | 1.28 GB | Pi 4/5 and up | small general model |
| edge | smollm3-3b-q4 | Hugging Face | 1.92 GB | Pi 5, 2012 MacBook Air | fully open training recipe |
| edge | qwen3.5-4b-q4 | Qwen | 2.74 GB | 4–8 GB machines | best small general model |
| edge | gemma-4-e2b-qat | Google | 3.35 GB | 4–8 GB machines | text, images, audio |
| edge | glm-ocr-q8 | Z.ai | 1.43 GB | 4 GB+ machines | reading text, tables and formulas from scans |
| utility | gemma-4-e4b-qat | Google | 5.15 GB | this Mac | fast everyday, images, audio |
| utility | granite-4.2-8b-q4 | IBM | 5.35 GB | this Mac | documents, tools, long context |
| utility | qwen3.5-9b-q4 | Qwen | 6.60 GB | this Mac | strongest general model here; images |
| utility | gemma-4-12b-qat | Google | 6.98 GB | this Mac | strong generalist, images, audio |
| utility | mellum2.1-12b-q4 | JetBrains | 8.07 GB | this Mac | coding agent work |
| utility | glm-4.6v-flash-q4 | Z.ai | 7.95 GB | this Mac | images; a GLM that runs here |
| mid | gpt-oss-20b-mxfp4 | OpenAI | 12.1 GB | 24 GB+ | reasoning, tools |
| mid | glm-4.7-flash-q8 | Z.ai | 31.8 GB | 48 GB+ | coding and agents, fast MoE |
| mid | qwen3.8-27b-q8 | Qwen | 30.0 GB | 48 GB+ | highest AA index among the mid models it scored |
| mid | gemma-4-31b-q8 | Google | 33.8 GB | 48 GB+ | general, images |
| mid | qwen3.6-35b-a3b-q8 | Qwen | 37.8 GB | 48 GB+ | fast coding agent |
| mid | gpt-oss-120b-mxfp4 | OpenAI | 63.4 GB | 96–128 GB | reasoning, tools |
| mid | qwen3.5-122b-a10b-q4xl | Qwen | 77.9 GB | 128 GB | general, images |
| mid | qwen3-coder-next-q8 | Qwen | 84.8 GB | 128 GB | coding agent (no thinking) |
| frontier | glm-5.3-flash-q4xl | Z.ai | 200.8 GB | 256 GB | near-frontier, images |
| frontier | glm-5.3-q4xl | Z.ai | 467.3 GB | 512 GB | best in the archive (tied) |
| frontier | deepseek-v4.1-flash-q4xl | DeepSeek | 460.2 GB | 512 GB | best in the archive (tied), images |
| embedding | embeddinggemma-2-q8 | Google | 0.31 GB | anything | document search |
| embedding | qwen3-embedding-0.6b-q8 | Qwen | 0.64 GB | anything | multilingual document search |

"Good for" is a one-line summary of the sections below, not a measurement. "Runs on" is
the memory class; speed on the Pi and the 2012 MacBook Air is untested (OFFLINE.md).

## Resource needs

Memory needed is roughly the file size plus a working buffer for the conversation (the
KV cache), which grows with context length. On this Mac about 10.7 GB of the 16 GB can go
to the GPU (MODELS.md). Parameters are the model's size in billions (B). *Mixture-of-experts*
(MoE) models use only some of their parameters (the "active" ones) for each token, which
makes them much faster than their size suggests, but all of them must still fit in memory.

| Model | Parameters total / active | On disk | Max context (card) | Inputs |
|---|---|---|---|---|
| smollm2-135m-q8 | 0.135B | 0.14 GB | not stated | text [3] |
| smollm2-360m-q8 | 0.36B | 0.39 GB | not stated | text [3] |
| qwen3-0.6b-q8 | 0.6B | 0.64 GB | 32K | text [9] |
| qwen3.5-0.8b-q8 | 0.8B | 0.81 GB | 262K | text, image, video [10] |
| lfm3-1.7b-q4 | 1.73B | 1.10 GB | 256K | text [5] |
| qwen3.5-2b-q4 | 2B | 1.28 GB | 262K | text, image, video [10] |
| smollm3-3b-q4 | 3B | 1.92 GB | 64K (128K with YaRN) | text [4] |
| qwen3.5-4b-q4 | 4B | 2.74 GB | 262K (1M with YaRN) | text, image, video [10] |
| gemma-4-e2b-qat | 5.1B / 2.3B effective | 3.35 GB | 128K | text, image, audio [6] |
| glm-ocr-q8 | 0.9B (1.3B incl. vision encoder) | 1.43 GB incl. vision file | not stated | image to text [27] |
| gemma-4-e4b-qat | 8B / 4.5B effective | 5.15 GB | 128K | text, image, audio [6] |
| granite-4.2-8b-q4 | 8B | 5.35 GB | 128K (512K extended) | text [7] |
| qwen3.5-9b-q4 | 9B | 6.60 GB incl. vision file | 262K (1M with YaRN) | text, image, video [10] |
| gemma-4-12b-qat | 11.95B | 6.98 GB | 256K | text, image, audio [6] |
| mellum2.1-12b-q4 | 12B / 2.5B (MoE) | 8.07 GB | 131K | text [8] |
| glm-4.6v-flash-q4 | 9B (10.3B incl. vision) | 7.95 GB incl. vision file | 128K | text, image [28] |
| gpt-oss-20b-mxfp4 | 20.9B / 3.6B (MoE) | 12.1 GB | 131K | text [15] |
| glm-4.7-flash-q8 | 30B / 3B (MoE) | 31.8 GB | not stated | text [29] |
| qwen3.8-27b-q8 | 27B | 30.0 GB | 262K (1M) | text, image, video [11] |
| gemma-4-31b-q8 | 30.7B | 33.8 GB | 256K | text, image [6] |
| qwen3.6-35b-a3b-q8 | 35B / 3B (MoE) | 37.8 GB | 262K (1M) | text, image, video [12] |
| gpt-oss-120b-mxfp4 | 116.8B / 5.1B (MoE) | 63.4 GB | 131K | text [15] |
| qwen3.5-122b-a10b-q4xl | 122B / 10B (MoE) | 77.9 GB | 262K (1M) | text, image, video [10] |
| qwen3-coder-next-q8 | 80B / 3B (MoE) | 84.8 GB | 262K | text [13] |
| glm-5.3-flash-q4xl | 320B / 18B (MoE) | 200.8 GB | not stated as a model limit | text, image [17] |
| glm-5.3-q4xl | 753B / ~40B (MoE) | 467.3 GB | not stated as a model limit | text [16] (active count: MODELS.md) |
| deepseek-v4.1-flash-q4xl | 763B incl. 196B "engram" memory; 552B backbone / 16B active when generating | 460.2 GB | 1M | text, image [18] |
| embeddinggemma-2-q8 | 0.74B (0.27B text) | 0.31 GB | 8K | text (+ image, audio in the original) [19] |
| qwen3-embedding-0.6b-q8 | 0.6B | 0.64 GB | 32K | text [20] |

Notes:
- **`om serve` gives every model an 8K-token context** (`--ctx 8192`), far below these
  maxima, to keep memory use predictable on 16 GB. Raise it with `--ctx` if a task needs
  more and the model fits.
- The image/audio column is what the model accepts. Through `om serve`, only
  qwen3.5-9b-q4, glm-4.6v-flash-q4 and glm-ocr-q8 have their vision files in the catalog. Images and audio for the other models
  would need their adapter files added.
- Gemma 4 "E" models list an *effective* size: part of their parameters are lookup tables
  that are not read in full for each token [6].

## Speed

How fast a model writes is mostly limited by **memory bandwidth**: generating each token
means reading the model's active weights once. So the ceiling is roughly
*bandwidth ÷ bytes read per token*. Real speed lands below it. The one comparison so far,
qwen3.5-4b on this Mac, ran at 25.7 tokens/s against a ceiling of 36, about 70% [26].
Very small models fall further below their ceiling, because fixed overheads dominate.

How fast a model *reads* your prompt (prefill) depends on raw compute instead. That
matters for long documents and coding agents, which re-send long contexts. Prefill is
not estimated here; the local measurements will include it.

Ceilings in tokens per second, from each model's file size and its active fraction.
Bandwidths: this MacBook Air M2 100 GB/s [24]; Mac Studio M5 Max (128 GB) 614 GB/s and
M5 Ultra (up to 512 GB) 1.2 TB/s [25]. A ceiling is shown only where the model fits.
About 6 tokens/s reads slowly; 20+ feels fluent.

| Model | Read per token | This Mac (ceiling) | Measured here | M5 Max 128 GB | M5 Ultra 512 GB |
|---|---|---|---|---|---|
| smollm2-135m-q8 | 0.14 GB | 691 | pending | | |
| smollm2-360m-q8 | 0.39 GB | 259 | 143 (trial) [26] | | |
| qwen3-0.6b-q8 | 0.64 GB | 156 | pending | | |
| qwen3.5-0.8b-q8 | 0.81 GB | 123 | pending | | |
| lfm3-1.7b-q4 | 1.10 GB | 91 | pending | | |
| qwen3.5-2b-q4 | 1.28 GB | 78 | pending | | |
| smollm3-3b-q4 | 1.92 GB | 52 | pending | | |
| qwen3.5-4b-q4 | 2.74 GB | 36 | 25.7 (trial) [26] | | |
| gemma-4-e2b-qat | ~1.5 GB | 66 | pending | | |
| glm-ocr-q8 | 0.95 GB | 105 | 122 (one run, under memory pressure) | | |
| gemma-4-e4b-qat | ~2.9 GB | 34 | pending | | |
| granite-4.2-8b-q4 | 5.35 GB | 19 | pending | | |
| qwen3.5-9b-q4 | 5.68 GB | 18 | pending | | |
| gemma-4-12b-qat | 6.98 GB | 14 | pending | | |
| mellum2.1-12b-q4 | ~1.7 GB | 59 | pending | | |
| glm-4.6v-flash-q4 | 6.17 GB | 16 | 11–14 (two runs, under memory pressure) | | |
| gpt-oss-20b-mxfp4 | ~2.1 GB | 48 (only with a raised GPU memory limit) | | 294 | |
| glm-4.7-flash-q8 | ~3.2 GB | | | 193 | 377 |
| qwen3.8-27b-q8 | 29.1 GB | | | 21 | 41 |
| gemma-4-31b-q8 | 32.6 GB | | | 19 | 37 |
| qwen3.6-35b-a3b-q8 | ~3.2 GB | | | 194 | 379 |
| gpt-oss-120b-mxfp4 | ~2.8 GB | | | 222 | 434 |
| qwen3.5-122b-a10b-q4xl | ~6.3 GB | | | 97 | 190 |
| qwen3-coder-next-q8 | ~3.2 GB | | | 193 | 377 |
| glm-5.3-flash-q4xl | ~11.2 GB | | | | 107 |
| deepseek-v4.1-flash-q4xl | ~9.6 GB | | | | 125 |
| glm-5.3-q4xl | ~24.8 GB | | | | 48 |

"~" marks MoE models, where bytes per token were estimated as file size × active ÷ total
parameters. The estimate assumes each token reads the whole file. In fact the
word-embedding table is read only one row per token, and in small models it is a large
share of the file, so their real ceiling is higher. glm-ocr-q8 shows this: it measured
122 tokens/s against an estimated ceiling of 105. For models above a few billion
parameters the table is a small share and the estimate holds better. What this shows:
- **MoE models are fast for their size.** qwen3.6-35b-a3b reads about a tenth of what the
  dense qwen3.8-27b reads per token, so it should generate about 9× faster on the same
  machine. Mellum 2.1 on this Mac has a higher ceiling than the much smaller qwen3.5-4b.
- **Dense mid models are slow even on a big Mac.** qwen3.8-27b and gemma-4-31b at 8-bit
  have ceilings near 20 tokens/s on an M5 Max.
- **Thinking costs time, not just tokens/s.** A thinking model may write hundreds or
  thousands of hidden tokens before its answer, so time to an answer can be many seconds
  even at a good speed.
- For the frontier models on a Mac, MODELS.md has measured figures from other people's
  hardware and a GPU alternative.

## Capability

### Independent score: Artificial Analysis Intelligence Index

Artificial Analysis (AA) runs the same nine hard tests on every model: agentic office
work with file outputs, workflow automation through APIs, hard coding and terminal tasks,
expert-level science, and factual recall [1]. Scores are out of 100; Claude Opus 5.5
scores 59 on the same index (MODELS.md). The tests are demanding enough that small and
mid models score near the bottom, so the index separates the big models well and says
little about the small ones. It measures the hosted, full-precision models.

| Model | AA Intelligence Index v5.0.2 (default effort) |
|---|---|
| glm-5.3-q4xl | 32 (Max effort; 23 at Low) |
| deepseek-v4.1-flash-q4xl | 32 (Max; 29 High; 19 without reasoning) |
| glm-5.3-flash-q4xl | 28 (Max) |
| qwen3.8-27b-q8 | 20 (xhigh; 10 without reasoning) |
| lfm3-1.7b-q4 | 6 |
| gemma-4-e4b-qat | 5 (reasoning) |
| gemma-4-31b-q8 | 4 (reasoning) |
| gpt-oss-120b-mxfp4 | 4 (high) |

Listed by AA but without a score: qwen3.5 0.8B/2B/4B/9B/122B, gemma-4-e2b, gemma-4-12b,
granite-4.2-8b, gpt-oss-20b, qwen3.6-35b-a3b, qwen3-coder-next. Not on AA: smollm2,
smollm3, mellum2.1, qwen3-0.6b. No score found for glm-4.7-flash, glm-4.6v-flash or
glm-ocr. Read 2026-11-24 [2].

Two results look surprising and are what the pages say: LFM3 1.7B (6) above Gemma 4 31B
(4), and Gemma 4 31B far below Qwen3.8 27B (20). The index rewards agentic and
tool-driven work, which some models are trained for more than others. Don't read it as
general chat quality.

### Makers' own benchmark scores

Higher is better; all in %. Self-reported by each maker [3]–[18]. Blank means the card
doesn't report that benchmark.
- **GPQA Diamond**: graduate-level science questions.
- **MMLU-Pro**: broad knowledge and reasoning.
- **LiveCodeBench v6**: competitive programming.
- **SWE-bench Verified**: fixing real GitHub issues (agentic coding).
- **IFEval**: following explicit instructions.

| Model | GPQA Diamond | MMLU-Pro | LiveCodeBench v6 | SWE-bench Verified | IFEval |
|---|---|---|---|---|---|
| smollm2-135m-q8 | | | | | 29.9 [3] |
| smollm2-360m-q8 | | | | | 41.0 [3] |
| qwen3-0.6b-q8 | | | | | |
| qwen3.5-0.8b-q8 | 11.9 (GPQA, thinking) | 42.3 (thinking) | | | 52.1 (no thinking) |
| lfm3-1.7b-q4 | 63.4 | | 73.5 | 43.4 | 96.7 |
| qwen3.5-2b-q4 | 51.6 (GPQA, thinking) | 66.5 (thinking) | | | 78.6 (thinking) |
| smollm3-3b-q4 | 41.7 (thinking) | | | | 76.7 |
| qwen3.5-4b-q4 | 76.2 | 79.1 | 55.8 | | 89.8 |
| gemma-4-e2b-qat | 43.4 | 60.0 | 44.0 | | |
| glm-ocr-q8 | | | | | |
| gemma-4-e4b-qat | 58.6 | 69.4 | 52.0 | | |
| granite-4.2-8b-q4 | 64.1 | 74.0 | | 47.7 | |
| qwen3.5-9b-q4 | 81.7 | 82.5 | 65.6 | | 91.5 |
| gemma-4-12b-qat | 78.8 | 77.2 | 72.0 | | |
| mellum2.1-12b-q4 | 64.6 | | 82.0 | 47.0 | 90.6 |
| glm-4.6v-flash-q4 | | | | | |
| gpt-oss-20b-mxfp4 | 71.5 (high) | | | 60.7 | |
| glm-4.7-flash-q8 | 75.2 (GPQA) | | 64.0 | 59.2 | |
| qwen3.8-27b-q8 | 89.2 | | 90.3 | | |
| gemma-4-31b-q8 | 84.3 | 85.2 | 80.0 | | |
| qwen3.6-35b-a3b-q8 | 86.0 (GPQA) | 85.2 | | 73.4 (Qwen's own harness) | |
| gpt-oss-120b-mxfp4 | 80.1 (high) | | | 62.4 | |
| qwen3.5-122b-a10b-q4xl | 86.6 | 86.7 | 78.9 | 72.0 | 93.4 |
| qwen3-coder-next-q8 | | 80.5 | | 70.6 | |
| glm-5.3-flash-q4xl | | | | | |
| glm-5.3-q4xl | | | | | |
| deepseek-v4.1-flash-q4xl | 90.9 (max effort) | | | | |

The frontier cards report agentic benchmarks instead [16][17][18]:

| Model | Terminal-Bench 2.1 | DeepSWE v1.1 | HLE with tools |
|---|---|---|---|
| deepseek-v4.1-flash-q4xl | 90.6 | 74.2 | 63.9 |
| glm-5.3-q4xl | 88.2 | 66.9 | 62.5 |
| glm-5.3-flash-q4xl | 84.3 | 63.4 | |

Reading these together:
- **Within the Qwen3.5 family the numbers are consistent and worth trusting:** each step
  up in size is a clear step up. qwen3.5-9b is the strongest general model that runs here.
- **LFM3 1.7B's self-reported scores are far above its size class.** For example, it
  reports 63.4 on GPQA Diamond, against 51.6 for Qwen3.5 2B. AA's independent index
  agrees it is unusually strong for its size (6, against a median of 3 for similar
  models) [2]. Its own card still says it is "not recommended for agentic coding or
  complex multi-step reasoning" [5].
- **For coding on this Mac**, mellum2.1-12b reports the best coding scores (LiveCodeBench
  82.0, SWE-bench 47.0) and has a high speed ceiling.
- **GLM-5.3 and DeepSeek V4.1 Flash are level** on AA's index (32 each), and both are well
  behind Claude Opus 5.5 (59). MODELS.md compares GLM-5.3 with Opus 5.5 in detail.
- **The new GLM models,** tested here on 2026-11-24 (MODELS.md): GLM-OCR transcribed a
  test image exactly, and GLM-4.6V-Flash answered text and image questions correctly.
  Their makers' scores: GLM-4.7-Flash reports 59.2 on SWE-bench Verified and 75.2 on
  GPQA, ahead of gpt-oss-20b on Z.ai's own table [29]. That table shows how far
  makers' numbers can differ: it gives gpt-oss-20b 34.0 on SWE-bench Verified, where
  OpenAI's own card reports 60.7 [15]. GLM-4.6V-Flash's card gives its
  scores only as an image, so none are listed. GLM-OCR reports 94.62 on OmniDocBench
  v1.5, a document-reading benchmark, and calls that #1 overall [27].
- **Languages:** the Qwen3.5 family lists 201 languages and dialects [10], Gemma 4 35+
  out of the box [6], LFM3 16 [5], Granite 12 tested [7], SmolLM3 6 [4]. SmolLM2 is
  "primarily" English [3].

## Safety and limitations

Running a model locally removes the hosted provider's safeguards. Nothing in `om serve`
filters content, so what you get is each model's own trained behaviour. Open weights can
also be fine-tuned to strip that behaviour; OpenAI states this for gpt-oss [15].

**What each maker says about safety**

| Model(s) | Safety training stated | Stated limitations and cautions |
|---|---|---|
| gpt-oss-20b / 120b | Yes: trained to refuse a wide range of harmful content (e.g. illicit advice), resist jailbreaks, and follow an instruction hierarchy (system > developer > user); harmful pretraining data filtered [15] | "Determined attackers could fine-tune them to bypass safety refusals" [15]. The reasoning text is "not intended to be shown to end users" [14]. Not for medical diagnosis or treatment [15]. Knowledge cutoff June 2024 [15]. Must use OpenAI's "harmony" chat format [14] |
| Gemma 4 (all) | Yes: safety evaluations reported; Google says they "significantly outperform" Gemma 3 on safety [6] | "May generate incorrect or outdated factual statements"; developers should add their own content safeguards [6]. Data cutoff January 2025 [6] |
| granite-4.2-8b | Yes: "aligned for safety" [7] | "May occasionally produce inaccurate, biased, or unsafe responses"; IBM recommends pairing it with its Granite Guardian filter model [7]. Its thinking text "may contain unpolished or intermediate thoughts" [7] |
| mellum2.1-12b | Reports safety scores: XSTest 88.8, HarmBench 8.5 (lower is better) [8] | No limitations section. Intended for agentic coding [8] |
| lfm3-1.7b | Not stated | "Not recommended for agentic coding or complex multi-step reasoning"; use retrieval for knowledge-heavy tasks [5] |
| smollm2, smollm3 | Not stated | Output "may not always be factually accurate, logically consistent, or free from biases"; use as assistive tools, "not definitive sources" [3][4] |
| Qwen3, Qwen3.5, Qwen3.6, Qwen3.8, Qwen3-Coder-Next | Not stated (no safety section on any card) | Qwen3.5 0.8B and 2B are meant for "prototyping, task-specific fine-tuning" and research, and are "more prone to entering thinking loops" [10] |
| glm-5.3, glm-5.3-flash | Not stated | None stated. The card highlights strong results in finding and exploiting software vulnerabilities (CyberGym, ExploitGym) [16] |
| glm-4.6v-flash | Not stated | Text-only answering "still has significant room for improvement"; "may still overthink or even repeat itself"; weak at counting and identifying specific people [28] |
| glm-4.7-flash | Not stated | None stated [29]. unsloth: turn the repeat penalty off and set `--min-p 0.01`, or output degrades (catalog notes) |
| glm-ocr | Not stated | Only fixed prompts ("Text Recognition:" etc.) or a strict JSON schema work [27] |
| deepseek-v4.1-flash | Not stated | None stated [18]. Must run with `--ple` (MODELS.md) |

**Political topics and models from Chinese labs.** Qwen (10 catalog entries, including
the embedding model), GLM (5) and DeepSeek (1) come from Chinese developers.
- **Qwen3:** a 2026 study found Qwen3 models "frequently produce falsehoods about subjects
  like Falun Gong or the Tiananmen protests", while sometimes answering correctly, so the
  knowledge is there but suppressed [21].
- **Chinese-developed models generally:** a study of ten models found them "substantially
  more likely to refuse otherwise identical political requests when they concern China"
  [22].
- **Not only Chinese models:** a 2025 study of 14 models from Western countries, China and
  Russia found censorship "across the board", tailored to each provider's domestic
  audience [23].
- **None of these studies tested the exact versions in our catalog.** For politically
  sensitive questions, especially about China, compare answers across makers.

**Limitations shared by all of them**
- **They make things up.** Every card that discusses accuracy warns about it, and smaller
  models do it more. Nothing here checks facts or searches the web, unless you connect a
  search tool (SERVING.md, "Privacy").
- **Their knowledge stops at a date.** Gemma 4: January 2025 [6]. gpt-oss: June 2024 [15].
  The others don't state one.
- **Long reasoning isn't proof.** Thinking text can be wrong, and for gpt-oss it is
  explicitly not meant to be shown as an explanation [14].

## Embedding models (document search)

| Model | Vector size | Max input | Stated score | Languages | Notes |
|---|---|---|---|---|---|
| embeddinggemma-2-q8 | 768 (can shorten to 512/256/128) | 8K tokens | MTEB multilingual v2 61.36; MTEB English v2 68.46; MTEB code 78.68 [19] | 100+ | "Does not undergo post-training alignment, safety tuning, or output-level moderation"; covered by Gemma's Prohibited Use Policy; "Do not use float16" [19] |
| qwen3-embedding-0.6b-q8 | up to 1024 (32–1024) | 32K tokens | MTEB multilingual 64.33; MTEB English v2 70.70; C-MTEB 66.33 [20] | 100+, incl. programming languages | Add an instruction to search queries: leaving it out costs about 1–5% retrieval quality [20] |

Both are self-reported. qwen3-embedding-0.6b reports higher MTEB scores and takes much
longer inputs. embeddinggemma-2 is half the size and stronger on code (78.68, against no
reported code score for Qwen). Both scored sensibly in our own small test (SERVING.md).

## Choosing, in short

This is a judgment from the evidence above, not a measurement:
- **Everyday questions on this Mac:** qwen3.5-9b-q4, which is strongest on every reported
  benchmark and handles images. gemma-4-e4b-qat is a faster alternative (about twice the
  speed ceiling) with audio support.
- **Coding on this Mac:** mellum2.1-12b-q4 (best reported coding scores, MoE so fast).
- **Scanned documents and photos of text:** glm-ocr-q8, with the prompt "Text
  Recognition:" (or "Table Recognition:", "Formula Recognition:").
- **Raspberry Pi 4/5:** qwen3.5-2b-q4, or lfm3-1.7b-q4 for tool calling and structured
  output. Original Pi: smollm2-360m-q8, which is only good for simple English text.
- **Long documents:** granite-4.2-8b-q4 reports the best long-context score among the
  small models (RULER 128K 71.4 [7], against LFM3's 65.6 [5]). Remember `om serve`
  caps context at 8K unless you raise `--ctx`.
- **Politically sensitive or China-related questions:** prefer Gemma, Granite, gpt-oss
  or SmolLM over the Qwen, GLM and DeepSeek models, and compare more than one.
- **On a 128 GB machine:** qwen3.6-35b-a3b or qwen3-coder-next for coding (fast MoE),
  qwen3.5-122b-a10b for general use, qwen3.8-27b for best quality at a lower speed.
- **On a 256–512 GB machine:** GLM-5.3 Flash, or GLM-5.3 / DeepSeek V4.1 Flash for the best
  results the archive holds.

## To do

- Measure generation and prefill speed and memory use for the 16 local models, after a
  restart with other apps closed. Fill in the "Measured here" column and add prefill.
- The Raspberry Pi and 2012 MacBook Air speeds are unmeasured (no hardware tested yet).

## References

1. Artificial Analysis, Intelligence Index methodology (v5.0.2, nine evaluations and weights): https://artificialanalysis.ai/methodology/intelligence-benchmarking
2. Artificial Analysis model pages, read 2026-11-24, e.g. https://artificialanalysis.ai/models/glm-5-3, https://artificialanalysis.ai/models/deepseek-v4-1-flash-1017, https://artificialanalysis.ai/models/glm-5-3-flash, https://artificialanalysis.ai/models/qwen3-8-27b, https://artificialanalysis.ai/models/lfm3-1-7b, https://artificialanalysis.ai/models/gemma-4-e4b, https://artificialanalysis.ai/models/gemma-4-31b, https://artificialanalysis.ai/models/gpt-oss-120b; leaderboard: https://artificialanalysis.ai/leaderboards/models
3. SmolLM2 model cards: https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct, https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
4. SmolLM3-3B model card: https://huggingface.co/HuggingFaceTB/SmolLM3-3B
5. LFM3-1.7B model card: https://huggingface.co/LiquidAI/LFM3-1.7B
6. Gemma 4 model card (family tables, safety, limitations; on the 12B page): https://huggingface.co/google/gemma-4-12B-it
7. Granite 4.2 8B model card: https://huggingface.co/ibm-granite/granite-4.2-8b
8. Mellum 2.1 model card: https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking
9. Qwen3-0.6B model card: https://huggingface.co/Qwen/Qwen3-0.6B
10. Qwen3.5 model cards: https://huggingface.co/Qwen/Qwen3.5-0.8B, https://huggingface.co/Qwen/Qwen3.5-2B, https://huggingface.co/Qwen/Qwen3.5-4B, https://huggingface.co/Qwen/Qwen3.5-9B, https://huggingface.co/Qwen/Qwen3.5-122B-A10B
11. Qwen3.8-27B model card: https://huggingface.co/Qwen/Qwen3.8-27B
12. Qwen3.6-35B-A3B model card: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
13. Qwen3-Coder-Next model card (scores from the page's evaluation results): https://huggingface.co/Qwen/Qwen3-Coder-Next
14. gpt-oss model cards: https://huggingface.co/openai/gpt-oss-20b, https://huggingface.co/openai/gpt-oss-120b
15. OpenAI, "gpt-oss-120b & gpt-oss-20b Model Card" (benchmarks at high reasoning, safety training, knowledge cutoff): https://arxiv.org/abs/2508.10925 (HTML: https://arxiv.org/html/2508.10925v1)
16. GLM-5.3 model card: https://huggingface.co/zai-org/GLM-5.3
17. GLM-5.3 Flash model card: https://huggingface.co/zai-org/GLM-5.3-Flash
18. DeepSeek V4.1 Flash model card: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash
19. EmbeddingGemma 2 model card: https://huggingface.co/google/embeddinggemma-2
20. Qwen3-Embedding-0.6B model card: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
21. "Censored LLMs as a Natural Testbed for Secret Knowledge Elicitation" (arXiv 2603.05494, March 2026): https://arxiv.org/abs/2603.05494
22. "What a Model Refuses, a State Fears: How Authoritarian Information Control Reproduces in Language-Model Guardrails" (arXiv 2609.07507, September 2026): https://arxiv.org/abs/2609.07507
23. "What Large Language Models Do Not Talk About: An Empirical Study of Moderation and Censorship Practices" (arXiv 2504.03803, April 2025): https://arxiv.org/abs/2504.03803
24. Apple, MacBook Air (M2, 2022) tech specs (100 GB/s memory bandwidth): https://support.apple.com/en-us/111867
25. Apple, Mac Studio (M5 Max or M5 Ultra) tech specs (614 GB/s M5 Max top configuration; 1.2 TB/s M5 Ultra): https://support.apple.com/en-us/128107
26. Local trial benchmark, 2026-11-24 (one warm run each, with more free memory than the main run): `docs/benchmarks/serving-2026-11-24-trial.jsonl`; method in [SERVING.md](SERVING.md)
27. GLM-OCR model card (0.9B, prompt formats, OmniDocBench v1.5 94.62, self-reported): https://huggingface.co/zai-org/GLM-OCR
28. GLM-4.6V-Flash model card (9B, 128K, stated limitations): https://huggingface.co/zai-org/GLM-4.6V-Flash
29. GLM-4.7-Flash model card (30B-A3B, benchmark table, self-reported): https://huggingface.co/zai-org/GLM-4.7-Flash; recommended llama.cpp settings: https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF

## Inaccessible sources (consider obtaining)

- The arXiv PDF of [15] could not be text-extracted; the HTML version was used instead.
- Gemma's own model card page (https://ai.google.dev/gemma/docs/core/model_card_4) now
  redirects to gemma.ai and was not read. The Hugging Face card [6] carries the same
  family tables.
