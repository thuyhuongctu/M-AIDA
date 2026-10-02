@echo off
rem M-AIDA chay that tren may Windows: nhap dup tep nay.
rem Thong bao viet khong dau vi cua so cmd cu hien sai chu co dau.
rem Ma khoa Claude chi nam trong backend\.env tren may nay (git bo qua tep .env),
rem khong bao gio len GitHub.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title M-AIDA

if exist ".venv\Scripts\python.exe" goto :have_venv
echo [M-AIDA] Lan dau chay: dang cai moi truong Python, mat vai phut...
rem Uu tien 3.12 roi 3.11: numpy/scipy ghim trong requirements.txt chua co
rem ban dung san cho Python 3.13, cai se hong giua chung.
rem Chi nhan Python 64-bit: ban 32-bit khong co goi numpy/pandas/scipy dung san,
rem pip se co bien dich tu ma nguon va hong (02/10/2026).
set "PYV="
py -3.12-64 -c "1" >nul 2>&1 && set "PYV=-3.12-64"
if not defined PYV py -3.11-64 -c "1" >nul 2>&1 && set "PYV=-3.11-64"
if not defined PYV (
  echo.
  echo Khong tim thay Python 3.12 hoac 3.11 ban 64-bit.
  echo Ban 32-bit dang co tren may KHONG dung duoc.
  echo Tai ban 64-bit: https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
  echo Khi cai nho tick "Add python.exe to PATH", bam Install Now, roi nhap dup lai tep nay.
  goto :error
)
py %PYV% -m venv .venv || goto :error
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt || goto :error

:have_venv
findstr /r /c:"^LLM_API_KEY=sk-ant-" backend\.env >nul 2>&1 && goto :have_key
echo.
echo [M-AIDA] Chua co ma khoa Claude. Lay ma tai https://console.anthropic.com/settings/keys
echo Dan ma vao duoi day roi nhan Enter. Chu se KHONG hien ra man hinh, day la binh thuong.
:ask_key
set "KEY="
for /f "usebackq delims=" %%K in (`powershell -NoProfile -Command "$s=Read-Host 'Ma khoa (sk-ant-...)' -AsSecureString; $b=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s); [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b)"`) do set "KEY=%%K"
if not defined KEY goto :ask_key
if /i not "!KEY:~0,7!"=="sk-ant-" (
  echo Ma khoa phai bat dau bang sk-ant- . Thu lai.
  goto :ask_key
)
rem Dong trong truoc: neu .env cu khong ket thuc bang xuong dong thi dong moi
rem se dinh vao cuoi dong cu.
>>backend\.env echo.
>>backend\.env echo LLM_PROVIDER=anthropic
>>backend\.env echo LLM_API_KEY=!KEY!
>>backend\.env echo LLM_MODEL=claude-sonnet-5
set "KEY="
echo Da luu ma khoa vao backend\.env tren may nay.

:have_key
rem Kiem tra ma khoa + ma mo hinh bang mot yeu cau 5 token truoc khi mo app.
".venv\Scripts\python.exe" backend\check_llm.py
if errorlevel 1 (
  echo.
  echo Sua backend\.env theo huong dan o tren roi nhap dup lai tep nay.
  goto :error
)
rem Chi nghe tren chinh may nay: backend\.env giu ma khoa that, khong de may
rem khac cung mang Wi-Fi goi vao tieu tien API.
set "MAIDA_HOST=127.0.0.1"
rem Ma PIN 4 chu so, moi lan chay mot ma moi; chi may nay goi duoc nen du an toan.
rem (Ma mac dinh cua demo/run_defense.py la chuoi ngau nhien 6 ky tu, de go nham.)
set /a MAIDA_DEMO_PIN=%random% %% 9000 + 1000
rem O che do demo, khoa quan tri khong duoc dung; dat san de backend khong in
rem "Generated MAIDA admin key" ra man hinh, tranh nham voi ma PIN.
set "MAIDA_ADMIN_KEY=demo-%random%%random%%random%"
echo.
echo [M-AIDA] Dang khoi dong. Trinh duyet se tu mo http://127.0.0.1:8765/
echo Dong cua so nay la tat M-AIDA.
echo.
echo   ==========================================
echo     MA PIN (Presenter PIN):  %MAIDA_DEMO_PIN%
echo   ==========================================
echo   Trinh duyet mo tu dong se nhan ma nay san; chi can nhap lai neu trang hoi.
echo.
start "" cmd /c "timeout /t 5 >nul & start http://127.0.0.1:8765/?pin=%MAIDA_DEMO_PIN%"
".venv\Scripts\python.exe" demo\run_defense.py
goto :eof

:error
echo.
echo M-AIDA chua chay duoc. Chup man hinh cua so nay gui lai de kiem tra.
pause
exit /b 1
