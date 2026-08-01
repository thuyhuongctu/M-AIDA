@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
  echo [M-AIDA] Creating local Python environment...
  py -3.11 -m venv .venv
  if errorlevel 1 goto :error
  ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
  if errorlevel 1 goto :error
)
echo [M-AIDA] Starting Defense App...
".venv\Scripts\python.exe" demo\run_defense.py
goto :eof
:error
echo.
echo M-AIDA could not start. Check Python 3.11+ and internet access for first install.
pause
exit /b 1
