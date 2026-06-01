#!/usr/bin/env bash
# Stop the local GEO stack (leaves Docker + Supabase data intact).
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "▸ stopping web/app/engine ports…"
for p in 3000 5050 8000; do lsof -ti:$p 2>/dev/null | xargs kill 2>/dev/null || true; done
echo "▸ stopping Supabase…"
( cd "$ROOT/platform" && supabase stop >/dev/null 2>&1 || true )
echo "✓ stopped. (Run ./start-all.sh to bring it back.)"
