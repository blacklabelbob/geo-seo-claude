#!/usr/bin/env bash
# GEO-SEO CRM — one-command launcher
# Usage:  ./start.sh
# Starts the Flask CRM dashboard on http://localhost:5050 and opens your browser.

set -euo pipefail
cd "$(dirname "$0")"

PORT=5050
VENV=".venv"
PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

echo "▶ GEO-SEO CRM launcher"

# 1) Make sure the venv + deps exist (only does work the first time)
if [ ! -x "$PY" ]; then
  echo "  • Creating virtualenv…"
  python3 -m venv "$VENV"
fi
if ! "$PY" -c "import flask" >/dev/null 2>&1; then
  echo "  • Installing dependencies…"
  "$PIP" install -q --upgrade pip >/dev/null 2>&1 || true
  "$PIP" install -q flask
fi

# 2) Kill anything already on the port so restarts are clean
if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
  echo "  • Freeing port $PORT…"
  lsof -ti tcp:"$PORT" | xargs kill -9 2>/dev/null || true
  sleep 1
fi

# 3) Launch in the background, log to /tmp
echo "  • Starting server…"
( cd scripts/webapp && "../../$PY" app.py > /tmp/geo-webapp.log 2>&1 & )

# 4) Wait until it answers, then open the browser
for i in $(seq 1 20); do
  if curl -s -o /dev/null "http://localhost:$PORT/"; then
    echo "  ✓ Live at http://localhost:$PORT"
    open "http://localhost:$PORT/" 2>/dev/null || true
    echo ""
    echo "  Logs:  tail -f /tmp/geo-webapp.log"
    echo "  Stop:  ./stop.sh   (or lsof -ti tcp:$PORT | xargs kill)"
    exit 0
  fi
  sleep 0.5
done

echo "  ✗ Server did not come up — check /tmp/geo-webapp.log"
tail -20 /tmp/geo-webapp.log || true
exit 1
