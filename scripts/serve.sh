#!/usr/bin/env bash
# Start, stop or check the chat server (llama-server in router mode) for the working models.
#
# Summary: a stand-in for `om serve` until Stage 5b. `start` runs llama-server in the
# background, detached from the terminal, serving every working-store model under its
# catalog id (loaded on demand, one at a time), with the web chat page and the OpenAI-style
# API on the home network, protected by an API key. docs/SERVING.md ("Using the chat from
# another computer") explains the key and the browser's first visit. Tested by
# tests/test_serve.py with a fake llama-server.
#
# Details:
# - start:   refuses if something already listens on the port, or if the working store
#            isn't mounted. Creates the API key file if it's missing (random, readable only
#            by you). Starts with nohup, so it keeps running after the terminal or Claude
#            session closes (not after a restart or logout). Waits up to 60 s for /health,
#            then prints the address. Log: <working store>/llama-server.log (overwritten).
# - stop:    stops the llama-server listening on the port, and the per-model servers it
#            started. Refuses if what listens there isn't llama-server.
# - status:  says whether it is running, with its pid, address and loaded models.
# - restart: stop, then start.
# - Settings (environment, defaults in brackets): OM_SERVE_PORT [8080],
#   OM_SERVE_HOST [0.0.0.0, the whole home network; 127.0.0.1 = this Mac only],
#   OM_SERVE_CTX [8192 tokens], OM_SERVE_KEY_FILE [~/.config/open-models/llama-server.key],
#   OPEN_MODELS_WORKING [/Volumes/BackUp_T7/lm-storage, as for `om`], LLAMA_SERVER
#   [llama-server on PATH, i.e. Homebrew's].
# - Known gap: models start without their catalog flags (--mmproj, --embedding, --ple), so
#   vision and embeddings don't work through it yet (Stage 5b).
# Usage: scripts/serve.sh [start|stop|status|restart]   (default: status)
set -euo pipefail

port=${OM_SERVE_PORT:-8080}
host=${OM_SERVE_HOST:-0.0.0.0}
ctx=${OM_SERVE_CTX:-8192}
key_file=${OM_SERVE_KEY_FILE:-$HOME/.config/open-models/llama-server.key}
working=${OPEN_MODELS_WORKING:-/Volumes/BackUp_T7/lm-storage}
server=${LLAMA_SERVER:-llama-server}
log=$working/llama-server.log

# PID of whatever listens on $port, if anything.
listener() { lsof -nP -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -1; }

# The address other computers use: this Mac's IP on its default network interface.
address() {
  local ip=127.0.0.1
  if [ "$host" != 127.0.0.1 ]; then
    local ifc
    ifc=$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')
    ip=$(ipconfig getifaddr "${ifc:-en0}" 2>/dev/null || echo "<this Mac's address>")
  fi
  echo "http://$ip:$port"
}

status() {
  local pid
  pid=$(listener)
  if [ -z "$pid" ]; then echo "not running (nothing listens on port $port)"; return 1; fi
  echo "running: pid $pid, $(address)"
  local kids
  # Each loaded model is a child llama-server started with `--alias <catalog id>`.
  kids=$( (pgrep -P "$pid" -lf . 2>/dev/null || true) | (grep -o -- '--alias [^ ]*' || true) \
    | cut -d' ' -f2 | tr '\n' ' ')
  echo "loaded models: ${kids:-none}"
}

start() {
  if pid=$(listener) && [ -n "$pid" ]; then
    echo "already running on port $port (pid $pid); use: $0 restart" >&2; exit 1
  fi
  if [ ! -d "$working/models" ]; then
    echo "working store not found: $working/models (is the drive plugged in?)" >&2; exit 1
  fi
  if [ ! -s "$key_file" ]; then
    mkdir -p "$(dirname "$key_file")"
    (umask 077; python3 -c 'import secrets; print(secrets.token_urlsafe(24))' > "$key_file")
    echo "created a new API key in $key_file"
  fi
  nohup "$server" --models-dir "$working/models" --models-max 1 -c "$ctx" \
    --host "$host" --port "$port" --api-key-file "$key_file" > "$log" 2>&1 < /dev/null &
  local pid=$!
  for _ in $(seq 1 120); do
    if curl -s -o /dev/null -m 1 "http://127.0.0.1:$port/health"; then
      echo "started: pid $pid, $(address)"
      echo "API key: cat $key_file   log: $log"
      return
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "llama-server exited; last lines of $log:" >&2; tail -5 "$log" >&2; exit 1
    fi
    sleep 0.5
  done
  echo "llama-server (pid $pid) did not answer within 60 s; see $log" >&2; exit 1
}

stop() {
  local pid
  pid=$(listener)
  if [ -z "$pid" ]; then echo "not running"; return; fi
  if ! ps -o command= -p "$pid" | grep -q -- "$(basename "$server")"; then
    echo "port $port is used by $(ps -o comm= -p "$pid"), not llama-server; not stopping it" >&2
    exit 1
  fi
  local kids
  kids=$(pgrep -P "$pid" || true)
  kill "$pid"
  for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
  # The per-model servers normally exit with the router; make sure.
  for k in $kids; do kill "$k" 2>/dev/null || true; done
  echo "stopped (pid $pid)"
}

case ${1:-status} in
  start) start ;;
  stop) stop ;;
  status) status ;;
  restart) stop; start ;;
  *) echo "usage: $0 [start|stop|status|restart]" >&2; exit 2 ;;
esac
