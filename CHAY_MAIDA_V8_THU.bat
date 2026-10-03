@echo off
rem M-AIDA 8.0 CHAY THU MOT MINH tren may Windows: nhap dup tep nay.
rem Che do thu ("mock"): dang nhap bang e-mail bat ky, khong can Supabase, VPS,
rem ten mien hay dich vu gui thu. Chi may nay vao duoc (127.0.0.1); KHONG BAO GIO
rem mo che do nay ra Internet, vi ai cung dang nhap duoc bang e-mail bat ky.
rem Du lieu thu nam o backend\maida_v8_thu.db trong thu muc nay, tach han khoi
rem ban 7.2.3 (thu muc M-AIDA). Ma khoa Claude doc tu ..\M-AIDA\backend\.env,
rem khong chep sang day. Thong bao viet khong dau vi cua so cmd cu hien sai chu co dau.
setlocal
cd /d "%~dp0"
title M-AIDA 8.0 (chay thu)

if not exist "frontend\build\index.html" (
  echo [M-AIDA 8.0] Thieu giao dien da dung san ^(frontend\build^). Thu muc nay chua day du.
  goto :error
)

if exist ".venv\Scripts\python.exe" goto :have_venv
echo [M-AIDA 8.0] Lan dau chay: dang cai moi truong Python rieng cho ban 8.0, mat vai phut...
set "PYV="
py -3.12-64 -c "1" >nul 2>&1 && set "PYV=-3.12-64"
if not defined PYV py -3.11-64 -c "1" >nul 2>&1 && set "PYV=-3.11-64"
if not defined PYV (
  echo.
  echo Khong tim thay Python 3.12 hoac 3.11 ban 64-bit.
  echo Tai ban 64-bit: https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
  goto :error
)
py %PYV% -m venv .venv || goto :error
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || goto :error

:have_venv
rem Ma khoa: lay tu ban 7.2.3 ben canh (chi cac dong LLM_*), neu khong co thi
rem dung backend\.env cua chinh thu muc nay.
set "SRC_ENV=%~dp0..\M-AIDA\backend\.env"
if not exist "%SRC_ENV%" set "SRC_ENV=%~dp0backend\.env"
if not exist "%SRC_ENV%" (
  echo.
  echo [M-AIDA 8.0] Chua co ma khoa Claude. Nhap dup CHAY_MAIDA_WINDOWS.bat trong thu muc
  echo M-AIDA mot lan de nhap ma, roi nhap dup lai tep nay.
  goto :error
)
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%SRC_ENV%") do (
  if /i "%%A"=="LLM_API_KEY" set "LLM_API_KEY=%%B"
  if /i "%%A"=="ANTHROPIC_API_KEY" set "ANTHROPIC_API_KEY=%%B"
  if /i "%%A"=="LLM_MODEL" set "LLM_MODEL=%%B"
  if /i "%%A"=="LLM_PROVIDER" set "LLM_PROVIDER=%%B"
)
".venv\Scripts\python.exe" backend\check_llm.py
if errorlevel 1 (
  echo.
  echo Sua ma khoa trong %SRC_ENV% theo huong dan o tren roi nhap dup lai tep nay.
  goto :error
)

set "MAIDA_AUTH_MODE=mock"
set "MAIDA_INVITED_EMAILS=*"
set "MAIDA_ADMIN_EMAILS=thuyhuongctu@gmail.com"
set "MAIDA_BETA_CREDITS=10"
set "MAIDA_DEMO_MODE=false"
set "MAIDA_DB_PATH=maida_v8_thu.db"
set "MAIDA_FRONTEND_DIR=%~dp0frontend\build"
echo.
echo [M-AIDA 8.0] Dang khoi dong. Trinh duyet se tu mo http://127.0.0.1:8766/
echo Dang nhap bang thuyhuongctu@gmail.com de co vai tro admin (cap tin dung, xem chi phi).
echo Moi luot trich xuat PDF that van tinh tien vao ma khoa Claude.
echo Dong cua so nay la tat M-AIDA 8.0. Ban 7.2.3 (cong 8765) khong bi anh huong.
echo.
start "" cmd /c "timeout /t 6 >nul & start http://127.0.0.1:8766/"
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8766
goto :eof

:error
echo.
echo M-AIDA 8.0 chua chay duoc. Chup man hinh cua so nay gui lai de kiem tra.
pause
exit /b 1
