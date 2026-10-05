@echo off
rem M-AIDA 8.0 CHAY THU NOI BO: may chu tren laptop nay, nguoi khac vao bang
rem duong link do MO_LINK_NOI_BO.bat mo ra. Dang nhap bang e-mail + mat khau cua
rem tai khoan do chi tao tay trong Supabase; chi e-mail trong noi_bo.env moi vao.
rem Du lieu nam o backend\maida_noi_bo.db trong thu muc nay (tach han khoi ban
rem 7.2.3 o thu muc M-AIDA va ban chay thu mot minh M-AIDA-v8-thu).
rem Ma khoa Claude doc tu ..\M-AIDA\backend\.env, khong chep sang day.
rem Thong bao viet khong dau vi cua so cmd cu hien sai chu co dau.
setlocal
cd /d "%~dp0"
title M-AIDA 8.0 (chay thu noi bo) - DUNG DONG CUA SO NAY KHI DANG CHAY THU

if not exist "frontend\build\index.html" (
  echo [M-AIDA noi bo] Thieu giao dien da dung san ^(frontend\build^). Thu muc nay chua day du.
  goto :error
)
if not exist "noi_bo.env" (
  echo [M-AIDA noi bo] Chua co noi_bo.env. Chep noi_bo.env.mau thanh noi_bo.env, dien khoa
  echo Publishable va danh sach e-mail, luu lai, roi nhap dup lai tep nay.
  goto :error
)

if exist ".venv\Scripts\python.exe" goto :have_venv
echo [M-AIDA noi bo] Lan dau chay: dang cai moi truong Python rieng, mat vai phut...
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
rem Ma khoa Claude: chi lay cac dong LLM_* / ANTHROPIC_API_KEY tu ban 7.2.3 ben canh.
set "SRC_ENV=%~dp0..\M-AIDA\backend\.env"
if not exist "%SRC_ENV%" set "SRC_ENV=%~dp0backend\.env"
if not exist "%SRC_ENV%" (
  echo.
  echo [M-AIDA noi bo] Chua co ma khoa Claude. Nhap dup CHAY_MAIDA_WINDOWS.bat trong thu muc
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

rem Cau hinh noi bo: chi nhan dung cac bien duoc phep tu noi_bo.env.
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("noi_bo.env") do (
  if /i "%%A"=="SUPABASE_URL" set "SUPABASE_URL=%%B"
  if /i "%%A"=="SUPABASE_ANON_KEY" set "SUPABASE_ANON_KEY=%%B"
  if /i "%%A"=="MAIDA_INVITED_EMAILS" set "MAIDA_INVITED_EMAILS=%%B"
  if /i "%%A"=="MAIDA_ADMIN_EMAILS" set "MAIDA_ADMIN_EMAILS=%%B"
  if /i "%%A"=="MAIDA_BETA_CREDITS" set "MAIDA_BETA_CREDITS=%%B"
)
set "MAIDA_AUTH_MODE=supabase"
set "MAIDA_LOGIN_METHOD=password"
set "MAIDA_PAYMENTS="
set "DATABASE_URL="
set "MAIDA_DEMO_MODE=false"
set "MAIDA_DB_PATH=maida_noi_bo.db"
set "MAIDA_FRONTEND_DIR=%~dp0frontend\build"
set "MAIDA_MAX_RUNNING_JOBS=2"
set "MAIDA_JOBS_PER_HOUR=10"

".venv\Scripts\python.exe" backend\check_noi_bo.py
if errorlevel 1 goto :error

echo.
echo [M-AIDA noi bo] Dang khoi dong may chu o http://127.0.0.1:8767/ (chi may nay).
echo Buoc tiep theo: nhap dup MO_LINK_NOI_BO.bat de mo duong link cho nhom.
echo Moi luot trich xuat PDF tinh tien vao ma khoa Claude cua chi.
echo Dong cua so nay la tat M-AIDA noi bo. Ban 7.2.3 (cong 8765) va ban thu 8766 khong bi anh huong.
echo.
start "" cmd /c "timeout /t 6 >nul & start http://127.0.0.1:8767/"
cd backend
"..\.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8767
goto :eof

:error
echo.
echo M-AIDA noi bo chua chay duoc. Chup man hinh cua so nay gui lai de kiem tra.
pause
exit /b 1
