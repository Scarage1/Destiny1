#!/usr/bin/env bash
set -euo pipefail

for p in 3000 8000; do
  lsof -ti tcp:"$p" | xargs -r kill -9 || true
done

echo "Stopped services on ports 3000 and 8000 (if running)."
