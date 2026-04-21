#!/bin/bash
# Run the LLM Bridge on the HOST (not in docker) for local dev, so it uses
# your Mac's already-authenticated `claude` CLI (keychain-backed) instead of
# needing a separate setup-token flow inside the container.
#
# On EC2 the same server.js runs in the container image built from this
# directory — that path does require `claude setup-token` once via SSM exec.
#
# Usage:
#   bash llm-bridge/start.sh          # foreground
#   bash llm-bridge/start.sh --daemon # background, logs to /tmp/llm-bridge.log
#
# Stop the daemon:  kill $(cat /tmp/llm-bridge.pid)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${LLM_BRIDGE_PORT:-8019}"
HOST="${LLM_BRIDGE_HOST:-127.0.0.1}"
PIDFILE=/tmp/llm-bridge.pid
LOGFILE=/tmp/llm-bridge.log

if ! command -v claude >/dev/null 2>&1; then
  echo "claude CLI not on PATH — install via 'npm install -g @anthropic-ai/claude-code' first" >&2
  exit 1
fi

# Refuse to double-start
if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
  echo "✅ llm-bridge already running on http://${HOST}:${PORT}"
  exit 0
fi

export LLM_BRIDGE_PORT="$PORT"
export LLM_BRIDGE_HOST="$HOST"

if [ "${1:-}" = "--daemon" ]; then
  nohup node "$HERE/server.js" > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      echo "✅ llm-bridge running (pid=$(cat "$PIDFILE"), log=$LOGFILE)"
      exit 0
    fi
    sleep 0.5
  done
  echo "❌ failed to start — see $LOGFILE" >&2
  exit 1
fi

exec node "$HERE/server.js"
