# Six-month model refresh

How to update the catalog roughly every six months: add new models and replace the
large ones. `om list` prints a warning once the newest `pinned` date in the catalog is
more than 180 days old. Next refresh due: **May 2027**.

## Checklist

1. **Check the current state.**
   `uv run om list` and `uv run om verify`. Fix any problem before changing anything;
   a refresh must not paper over a corrupt archive.

2. **Research what is new, per tier and role.** Use the method in [MODELS.md](MODELS.md):
   - Use web searches only for leads. Confirm every candidate on Hugging Face: parameter
     count, license (read it if it isn't Apache-2.0/MIT), gating, and file sizes.
   - Check that the GGUF's architecture is supported by the llama.cpp you will archive.
     Get the name from `https://huggingface.co/api/models/<repo>` → `gguf.architecture`,
     then: `strings $(brew --prefix llama.cpp)/lib/libllama.dylib | grep -x <arch>`.
   - Read the GGUF README for minimum llama.cpp builds, special flags, or files to skip
     (see the DeepSeek engram case in MODELS.md).
   - Update llama.cpp first (`brew upgrade llama.cpp`) if new models need it.
     If you do, archive the matching source too: update `LLAMA_BUILD`/`LLAMA_COMMIT`
     in `scripts/build_llama.sh` and the llama.cpp lines in `runtimes/manifest.tsv`
     (docs/OFFLINE.md, "Keeping it current").

3. **Decide, per tier: keep, replace, or add.**
   - Edge and utility models are small: keep superseded ones unless space is tight.
   - Mid and frontier models are large: replace the old one only after the new one is
     downloaded and verified (step 5).
   - Keep at least ~500 GB free on the archive, so a frontier download fits alongside
     the model it replaces.

4. **Pin the new models.**
   `uv run om pin <repo> --id <id> --tier <tier> --role <role> --format gguf --include <patterns> --notes "..." --append`
   Patterns match full repo paths, e.g. `"UD-Q4_K_XL/*.gguf"` for sharded models.
   Check the appended entry in `catalog/models.yaml`.

5. **Download, verify, and place.**
   ```bash
   PYTHONUNBUFFERED=1 HF_HUB_DISABLE_PROGRESS_BARS=1 uv run om fetch <ids...> \
       > /Volumes/Starfish_Prime/model-storage/logs/fetch-<date>.log 2>&1
   uv run om verify <ids...>
   uv run om sync                 # copies new edge/utility models to the T7
   ```
   Smoke-test the runnable models: `scripts/smoke_test.sh` (all edge + utility) or
   `scripts/smoke_test.sh <ids...>`; read the printed replies for sanity.
   Refresh the offline runtime archive and prove it still works:
   `scripts/archive_runtimes.sh && scripts/offline_check.sh` (needed after any change to
   llama.cpp, `uv.lock` or `runtimes/manifest.tsv`).

6. **Retire replaced models.**
   - Delete the model's folder from `/Volumes/Starfish_Prime/model-storage/models/<id>`.
   - Remove its entry from `catalog/models.yaml`.
   - Run `uv run om sync`; it reports any folder left on the T7 that the catalog no
     longer knows, so you can delete it by hand.
   - Git history keeps the old entry with its revision and hashes, so a retired model
     can be fetched again while the upstream repo exists.
   - `om` has no retire command yet; this is manual on purpose, since it deletes data.

7. **Update the docs.** In MODELS.md, update the tables, the date in the title, and the
   reasoning for every change; then set the next due date at the top of this file.
   Commit, then copy the repo into the archive: `scripts/mirror_repo.sh`.

## Reminder

Add a recurring calendar reminder every 6 months ("open-models refresh: docs/REFRESH.md").
The `om list` warning is the backstop if it is missed.
