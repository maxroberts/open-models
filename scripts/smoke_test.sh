#!/usr/bin/env bash
# Smoke-test catalog models with llama.cpp: does each one load and produce sane output?
#
# Summary: for each model id given (default: every edge + utility model, i.e. the ones
# runnable on this machine), find its file with `om path` and run it once. Used after
# downloads and in the six-month refresh (docs/REFRESH.md step 5).
#
# Details:
# - chat / code models: `llama-cli` single turn, reasoning off, 48 tokens max; prints
#   the reply and the speed line. "OK" means it ran and exited 0. Whether the answer is
#   sensible is for you to judge from the printed reply.
# - embedding models: `llama-embedding` on one sentence; prints the vector length.
# - Role and tier come from `om list` output (columns 2-3), so this needs the catalog.
# - Does not add model-specific flags from catalog notes (`--mmproj`, `--ple`); mid and
#   frontier models are not expected to run on this machine anyway.
# Usage: scripts/smoke_test.sh [id ...]      (run from the repo root)
set -uo pipefail

listing=$(uv run om list)
if [ $# -eq 0 ]; then
  set -- $(echo "$listing" | awk '$2=="edge" || $2=="utility" {print $1}')
fi

fail=0
for id in "$@"; do
  role=$(echo "$listing" | awk -v id="$id" '$1==id {print $3}')
  model=$(uv run om path "$id") || { echo "FAIL $id: not present"; fail=1; continue; }
  if [ "$role" = "embedding" ]; then
    out=$(llama-embedding -m "$model" -p "The archive must survive without the internet." \
          --embd-output-format array 2>/dev/null </dev/null)
    dims=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)[0]))" 2>/dev/null)
    if [ -n "$dims" ]; then echo "OK   $id: embedding with $dims dimensions"; else echo "FAIL $id"; fail=1; fi
  else
    out=$(llama-cli -m "$model" -st --reasoning off -n 48 --no-display-prompt \
          -p "In one sentence, what is a Raspberry Pi?" 2>/dev/null </dev/null)
    status=$?
    reply=$(echo "$out" | sed -n '/^> /,/^\[ Prompt/p' | sed '1d;$d' | tr -s '\n' ' ' | cut -c1-160)
    speed=$(echo "$out" | grep -o 'Generation: [0-9.]* t/s')
    if [ $status -eq 0 ]; then echo "OK   $id ($speed): $reply"; else echo "FAIL $id (exit $status)"; fail=1; fi
  fi
done
exit $fail
