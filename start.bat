@echo off
REM Lanzador rápido en Windows.
setlocal
cd /d "%~dp0"

if not exist .venv (
  echo [setup] Creando entorno virtual…
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)

if "%1"=="initdb" (
  python init_db_local.py
  goto :eof
)

python run_local.py
endlocal
