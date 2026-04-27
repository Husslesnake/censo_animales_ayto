#!/usr/bin/env bash
# Lanzador rápido en Linux/macOS.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "[setup] Creando entorno virtual…"
  python3 -m venv .venv
  . .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
else
  . .venv/bin/activate
fi

if [ "$1" = "initdb" ]; then
  python init_db_local.py
  exit 0
fi

python run_local.py
