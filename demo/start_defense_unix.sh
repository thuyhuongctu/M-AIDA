#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -x ".venv/bin/python" ]; then
  echo "[M-AIDA] Creating local Python environment..."
  python3 -m venv .venv
  .venv/bin/python -m pip install -r backend/requirements.txt
fi
echo "[M-AIDA] Starting Defense App..."
exec .venv/bin/python demo/run_defense.py
