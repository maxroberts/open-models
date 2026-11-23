"""open-models: keep a verified, offline archive of open-weights LLMs and run them locally.

Summary: the Python package behind the `om` command. It reads a catalog of pinned
models, downloads them into an archive store, copies chosen ones to a fast working
store, and hash-checks every copy.

Details (modules, bottom-up):
- `config`  - where the catalog, archive store, and working store live.
- `catalog` - loads and validates `catalog/models.yaml` into `Model` objects.
- `store`   - on-disk store layout, size/hash checks, verified copy, removal.
- `fetch`   - Hugging Face downloads and `pin` (making new catalog entries); the only
              module that uses the network.
- `cli`     - the `om` subcommands, built on the modules above.
Running models is done by llama.cpp (installed separately); `om path` hands it a file.
"""
