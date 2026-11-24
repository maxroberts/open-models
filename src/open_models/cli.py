"""The `om` command-line tool: the user-facing entry point to everything in the package.

Summary: subcommands for listing, downloading, verifying, placing, and locating
models, built on `catalog`, `store`, and `fetch`. Installed as the `om` script by
`pyproject.toml`.

Details (each subcommand maps to one `cmd_*` function below):
- `om list`                 catalog with tier, role, size, and presence in both stores
                            (fast size check, not a hash check). Warns when the newest
                            `pinned` date is over REFRESH_DAYS old (time for the
                            refresh in docs/REFRESH.md).
- `om fetch ID...`          download from Hugging Face into the archive, verified
- `om verify [ID...]`       hash-check every copy that exists, in either store;
                            exits 1 if any problem is found
- `om sync [--dry-run]`     make the working store match the tier policy
                            (catalog.WORKING_TIERS): copy in models that belong there,
                            remove ones that don't. Never deletes a working copy
                            unless the archive copy is present; never touches folders
                            the catalog doesn't know (it lists them instead).
- `om stage ID...`          copy archive -> working store, verified (manual override)
- `om unstage ID...`        delete from the working store; refuses unless the archive
                            copy is present (size check only; run `om verify` for hashes)
- `om path ID`              print the path llama.cpp should load: the first model
                            .gguf in path order, skipping `mmproj` vision adapters (so
                            shard 00001 for split models); working store preferred
- `om serve [opts]`         serve every working-store model over the network with
                            llama-server's router mode (presets generated from the
                            catalog, API key; see `serve.py`); runs in the foreground
- `om service ACTION`       install / uninstall / restart / status the launchd agent that
                            runs `om serve` at login and restarts it if it exits
- `om pin REPO ...`         print a new catalog entry as YAML, or `--append` it to the catalog
Stores come from `config` (env overrides: OPEN_MODELS_ARCHIVE / OPEN_MODELS_WORKING);
`--catalog` overrides the catalog path.
"""

import argparse
import datetime
import os
import plistlib
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

from . import config, serve
from .catalog import FORMATS, ROLES, TIERS, Model, append_entry, load_catalog
from .store import MISSING, PRESENT, Store, copy_model

# The catalog should be reviewed about every 6 months (docs/REFRESH.md).
REFRESH_DAYS = 180


def _stores() -> tuple[Store, Store]:
    """Return (archive, working) stores from the configured roots."""
    return Store("archive", config.archive_root()), Store("working", config.working_root())


def _select(models: dict[str, Model], ids: list[str]) -> list[Model]:
    """Return the models named by `ids` (all models if `ids` is empty); exit on unknown ids."""
    if not ids:
        return list(models.values())
    unknown = [i for i in ids if i not in models]
    if unknown:
        sys.exit(f"unknown model id(s): {', '.join(unknown)} (see `om list`)")
    return [models[i] for i in ids]


def stale_warning(models: dict[str, Model], today: datetime.date | None = None) -> str | None:
    """Return a warning if the newest `pinned` date is more than REFRESH_DAYS ago, else None."""
    if not models:
        return None
    today = today or datetime.date.today()
    newest = max(datetime.date.fromisoformat(m.pinned) for m in models.values())
    age = (today - newest).days
    if age > REFRESH_DAYS:
        return f"WARNING: catalog last updated {age} days ago ({newest}); time for a refresh (docs/REFRESH.md)"
    return None


def cmd_list(models, args) -> int:
    """Print one row per catalog model, then totals per store and any staleness warning."""
    archive, working = _stores()
    print(f"{'ID':<34} {'TIER':<9} {'ROLE':<10} {'SIZE GB':>8}  {'ARCHIVE':<8} {'WORKING':<8}")
    for m in models.values():
        want = "" if m.on_working or working.status(m) == MISSING else " (not wanted)"
        print(
            f"{m.id:<34} {m.tier:<9} {m.role:<10} {m.total_size / 1e9:>8.2f}  "
            f"{archive.status(m):<8} {working.status(m):<8}{want}"
        )
    total = sum(m.total_size for m in models.values()) / 1e9
    working_total = sum(m.total_size for m in models.values() if m.on_working) / 1e9
    print(f"catalog total {total:.1f} GB; working-store policy share {working_total:.1f} GB")
    if warning := stale_warning(models):
        print(warning)
    return 0


def cmd_fetch(models, args) -> int:
    """Download each selected model into the archive store."""
    from .fetch import fetch_model  # deferred: only these commands need the network stack

    archive, _ = _stores()
    for m in _select(models, args.ids):
        print(f"{m.id}:", flush=True)
        fetch_model(m, archive)
    return 0


def cmd_verify(models, args) -> int:
    """Hash-check every existing copy of the selected models; return 1 if any problem."""
    problems = []
    checked = 0
    for m in _select(models, args.ids):
        for store in _stores():
            if store.status(m) == MISSING:
                continue
            checked += 1
            problems += store.verify(m)
    for p in problems:
        print(f"PROBLEM {p}")
    print(f"checked {checked} copies, {len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_sync(models, args) -> int:
    """Make the working store match the tier policy; return 1 if anything couldn't be done."""
    archive, working = _stores()
    failed = 0
    for m in models.values():
        here = working.status(m)
        if m.on_working and here != PRESENT:
            if archive.status(m) != PRESENT:
                print(f"{m.id}: wanted on working store but not in archive yet (run `om fetch {m.id}`)")
                failed += 1
            elif args.dry_run:
                print(f"{m.id}: would copy to working store")
            else:
                print(f"{m.id}: copying to working store")
                copy_model(m, archive, working)
        elif not m.on_working and here != MISSING:
            if archive.status(m) != PRESENT:
                print(f"{m.id}: not wanted on working store, but archive copy incomplete; keeping it")
                failed += 1
            elif args.dry_run:
                print(f"{m.id}: would remove from working store")
            else:
                print(f"{m.id}: removing from working store")
                working.remove(m)
    known = {m.id for m in models.values()}
    models_dir = working.root / "models"
    if models_dir.is_dir():
        for d in sorted(models_dir.iterdir()):
            if d.is_dir() and d.name not in known:
                print(f"{d.name}: on working store but not in the catalog; left alone")
    return 1 if failed else 0


def cmd_stage(models, args) -> int:
    """Copy each selected model from the archive to the working store."""
    archive, working = _stores()
    for m in _select(models, args.ids):
        print(f"{m.id}:")
        copy_model(m, archive, working)
    return 0


def cmd_unstage(models, args) -> int:
    """Delete each selected model from the working store, if the archive copy is present."""
    archive, working = _stores()
    for m in _select(models, args.ids):
        if archive.status(m) != PRESENT:
            print(f"{m.id}: archive copy is not complete; refusing to delete the working copy")
            return 1
        working.remove(m)
        print(f"{m.id}: removed from working store")
    return 0


def cmd_path(models, args) -> int:
    """Print the main .gguf path of one model, preferring the working store."""
    m = _select(models, [args.id])[0]
    gguf = serve.main_gguf(m)
    if not gguf:
        sys.exit(f"{m.id}: no model .gguf files")
    archive, working = _stores()
    for store in (working, archive):  # the fast SSD copy first
        if store.status(m) == PRESENT:
            print(store.model_dir(m) / gguf)
            return 0
    sys.exit(f"{m.id}: not present in either store (run `om fetch {m.id}`)")


def cmd_serve(models, args) -> int:
    """Write the presets file and replace this process with llama-server in router mode.

    Serves every GGUF model complete on the working store. Exits 1 (without starting
    anything) if the working store isn't mounted, holds no models, or llama-server isn't
    found. With --print-presets, only prints the presets file.
    """
    _, working = _stores()
    if not (working.root / "models").is_dir():
        print(f"working store not found: {working.root / 'models'} (is the drive mounted?)",
              file=sys.stderr)
        return 1
    served = serve.served_models(models, working)
    if not served:
        print("no models on the working store (run `om sync`)", file=sys.stderr)
        return 1
    text = serve.presets_ini(served, working, args.ctx)
    if args.print_presets:
        print(text)
        return 0
    cfg = serve.config_dir()
    cfg.mkdir(parents=True, exist_ok=True)
    presets, key = cfg / "presets.ini", cfg / "llama-server.key"
    presets.write_text(text)
    if serve.ensure_key(key):
        print(f"created a new API key in {key}")
    cmd = serve.server_command(presets, key, args.host, args.port, args.models_max, args.idle)
    print(f"om serve: {len(served)} models on http://{args.host}:{args.port} "
          f"(API key in {key}); {' '.join(cmd)}", flush=True)
    try:
        os.execvp(cmd[0], cmd)  # does not return on success
    except FileNotFoundError:
        print(f"{cmd[0]} not found (brew install llama.cpp, or set LLAMA_SERVER)", file=sys.stderr)
        return 1


def _launchctl(*args) -> subprocess.CompletedProcess:
    """Run launchctl with `args`; return the finished process (never raises on failure)."""
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def cmd_service(models, args) -> int:
    """Install, uninstall, restart or check the login agent that runs `om serve` (launchd)."""
    domain = f"gui/{os.getuid()}"
    target = f"{domain}/{serve.LABEL}"
    plist = Path.home() / "Library" / "LaunchAgents" / f"{serve.LABEL}.plist"
    log = Path.home() / "Library" / "Logs" / "open-models" / "serve.log"

    if args.action == "install":
        om = Path(sys.executable).parent / "om"
        serve_args = ["--host", args.host, "--port", str(args.port), "--ctx", str(args.ctx),
                      "--models-max", str(args.models_max), "--idle", str(args.idle)]
        _launchctl("bootout", target)  # replace any earlier version; fails harmlessly if none
        log.parent.mkdir(parents=True, exist_ok=True)
        plist.parent.mkdir(parents=True, exist_ok=True)
        with open(plist, "wb") as fh:
            plistlib.dump(serve.launch_agent(om, serve_args, log), fh)
        r = _launchctl("bootstrap", domain, str(plist))
        if r.returncode != 0:
            print(f"launchctl bootstrap failed: {r.stderr.strip()}", file=sys.stderr)
            return 1
        print(f"installed {plist}; starts now and at every login. Log: {log}")
        print("check with: om service status")
        return 0
    if args.action == "uninstall":
        _launchctl("bootout", target)
        plist.unlink(missing_ok=True)
        print("uninstalled (stopped, and won't start at login)")
        return 0
    if not plist.exists():
        print("not installed (om service install)")
        return 1
    if args.action == "restart":
        r = _launchctl("kickstart", "-k", target)
        print("restarted" if r.returncode == 0 else f"restart failed: {r.stderr.strip()}")
        return r.returncode
    # status
    info = _launchctl("print", target)
    if info.returncode != 0:
        print(f"installed ({plist}) but not loaded; try: om service install")
        return 1
    fields = dict(line.strip().split(" = ", 1) for line in info.stdout.splitlines()
                  if line.startswith("\t") and " = " in line and line.count("\t") == 1)
    agent_args = plistlib.loads(plist.read_bytes())["ProgramArguments"]
    port = agent_args[agent_args.index("--port") + 1]
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
        health = "answering"
    except OSError as e:
        health = f"not answering ({e})"
    print(f"state: {fields.get('state', '?')}, pid: {fields.get('pid', '-')}, "
          f"last exit code: {fields.get('last exit code', '-')}")
    print(f"server on port {port}: {health}")
    print(f"log: {log}")
    return 0 if health == "answering" else 1


def cmd_pin(models, args) -> int:
    """Make a new catalog entry for a Hugging Face repo; print it, or append it with --append."""
    from .fetch import pin_entry

    if args.id in models:
        sys.exit(f"id '{args.id}' is already in the catalog")
    entry = pin_entry(
        args.repo, args.include, args.id, args.tier, args.format, args.role, args.revision, args.name, args.notes
    )
    if args.append:
        append_entry(args.catalog, entry)
        print(f"{args.id}: appended to {args.catalog} ({sum(f['size'] for f in entry['files']) / 1e9:.2f} GB)")
    else:
        print(yaml.safe_dump([entry], sort_keys=False), end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser; each subparser sets `func` to its `cmd_*` handler."""
    p = argparse.ArgumentParser(prog="om", description="Archive, verify, and run open-weights LLMs.")
    p.add_argument("--catalog", type=Path, default=config.DEFAULT_CATALOG, help="catalog YAML path")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show catalog and where each model is").set_defaults(func=cmd_list)
    for name, func, help_ in [
        ("fetch", cmd_fetch, "download models into the archive"),
        ("verify", cmd_verify, "hash-check existing copies (all models if no ids)"),
        ("stage", cmd_stage, "copy models archive -> working store"),
        ("unstage", cmd_unstage, "remove models from the working store"),
    ]:
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("ids", nargs="*" if name == "verify" else "+")
        sp.set_defaults(func=func)

    sp = sub.add_parser("sync", help="make the working store match the tier policy")
    sp.add_argument("--dry-run", action="store_true", help="only print what would change")
    sp.set_defaults(func=cmd_sync)

    sp = sub.add_parser("path", help="print a model's main .gguf path")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_path)

    def serve_options(sp):
        """Options shared by `serve` and `service install` (which passes them on to serve)."""
        sp.add_argument("--host", default="0.0.0.0",
                        help="address to listen on (default: all; 127.0.0.1 = this Mac only)")
        sp.add_argument("--port", type=int, default=8080)
        sp.add_argument("--ctx", type=int, default=8192, help="context size per model, tokens")
        sp.add_argument("--models-max", type=int, default=1, help="models loaded at once")
        sp.add_argument("--idle", type=int, default=300,
                        help="unload a model after this many idle seconds (0 = never)")

    sp = sub.add_parser("serve", help="serve the working-store models (llama-server router mode)")
    serve_options(sp)
    sp.add_argument("--print-presets", action="store_true",
                    help="print the generated model presets and exit")
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("service", help="run `om serve` at login (macOS launchd agent)")
    sp.add_argument("action", choices=("install", "uninstall", "status", "restart"))
    serve_options(sp)
    sp.set_defaults(func=cmd_service)

    sp = sub.add_parser("pin", help="make a catalog entry for a Hugging Face repo")
    sp.add_argument("repo", help="e.g. Qwen/Qwen3-0.6B-GGUF")
    sp.add_argument("--id", required=True, help="catalog id, e.g. qwen3-0.6b-q8")
    sp.add_argument("--include", nargs="+", required=True, help="glob patterns of files to keep")
    sp.add_argument("--tier", required=True, choices=TIERS)
    sp.add_argument("--format", required=True, choices=FORMATS)
    sp.add_argument("--role", default="chat", choices=ROLES)
    sp.add_argument("--revision", default="main", help="branch, tag, or commit (resolved to a commit)")
    sp.add_argument("--name", help="display name (default: repo name)")
    sp.add_argument("--notes", default="", help="free-text note stored with the entry")
    sp.add_argument("--append", action="store_true", help="append to the catalog instead of printing")
    sp.set_defaults(func=cmd_pin)
    return p


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, load the catalog, and run the chosen subcommand; returns the exit code."""
    args = build_parser().parse_args(argv)
    models = load_catalog(args.catalog)
    return args.func(models, args)


if __name__ == "__main__":
    sys.exit(main())
