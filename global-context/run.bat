@echo off
REM One-command start for Windows
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
if not exist .venv (
  echo Creating virtual environment ...
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt
if not exist .env copy .env.example .env >nul
python -m gcx setup %*
if "%PORT%"=="" set PORT=8000
python -m gcx serve --port %PORT%
