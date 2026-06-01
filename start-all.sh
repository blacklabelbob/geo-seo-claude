#!/usr/bin/env bash
# Bring up the whole GEO stack locally: Supabase, the FastAPI engine,
# the Flask cockpit (5050), and the Next.js platform (3000).
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "▸ Docker…"
if ! docker info >/dev/null 2>&1; then
  open -a Docker
  echo "  waiting for Docker daemon…"
  for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 3; done
fi

echo "▸ Supabase (geo-platform)…"
( cd platform && supabase start >/dev/null 2>&1 || true )

echo "▸ GEO engine (FastAPI :8000)…"
if ! curl -s -m 2 http://127.0.0.1:8000/health >/dev/null 2>&1; then
  nohup engine/.venv/bin/uvicorn engine.app:app --host 127.0.0.1 --port 8000 > /tmp/geo-engine.log 2>&1 &
fi

echo "▸ Flask cockpit (:5050)…"
lsof -ti:5050 2>/dev/null | xargs kill 2>/dev/null || true
( cd scripts/webapp && nohup ../../.venv/bin/flask run --port 5050 --no-reload > /tmp/geo-flask.log 2>&1 & )

echo "▸ Next.js platform (:3000)…"
lsof -ti:3000 2>/dev/null | xargs kill 2>/dev/null || true
( cd platform && nohup npm run dev > /tmp/geo-next.log 2>&1 & )

sleep 5
echo
echo "✓ Up:"
echo "  Platform (new product) : http://localhost:3000   (login demo@geo.local / geodemo123)"
echo "  Flask cockpit (library): http://localhost:5050"
echo "  Engine API             : http://127.0.0.1:8000/health"
echo "  Supabase Studio        : http://127.0.0.1:54523"
echo
echo "Logs: /tmp/geo-{engine,flask,next}.log   ·   Stop: ./stop-all.sh"
