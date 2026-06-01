#!/usr/bin/env bash
# GEO-SEO CRM — stop the local server
PORT=5050
if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
  lsof -ti tcp:"$PORT" | xargs kill -9 2>/dev/null || true
  echo "✓ Stopped GEO-SEO CRM on port $PORT"
else
  echo "Nothing running on port $PORT"
fi
