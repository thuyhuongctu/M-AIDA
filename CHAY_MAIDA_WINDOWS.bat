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
set "PYV="
py -3.12 -c "1" >nul 2>&1 && set "PYV=-3.12"
if not defined PYV py -3.11 -c "1" >nul 2>&1 && set "PYV=-3.11"
if not defined PYV (
  echo.
  echo Khong tim thay Python 3.12 hoac 3.11.
  echo Tai Python 3.12 tai https://www.python.org/downloads/windows/
  echo va nho tick "Add python.exe to PATH" khi cai, roi nhap dup lai tep nay.
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
rem Chi nghe tren chinh may nay: backend\.env giu ma khoa that, khong de may
rem khac cung mang Wi-Fi goi vao tieu tien API.
set "MAIDA_HOST=127.0.0.1"
echo.
echo [M-AIDA] Dang khoi dong. Trinh duyet se tu mo http://127.0.0.1:8765/
echo Ma PIN (Presenter PIN) in ben duoi: dung de xac nhan, khoa va xuat du lieu.
echo Dong cua so nay la tat M-AIDA.
start "" cmd /c "timeout /t 5 >nul & start http://127.0.0.1:8765/"
".venv\Scripts\python.exe" demo\run_defense.py
goto :eof

:error
echo.
echo M-AIDA chua chay duoc. Chup man hinh cua so nay gui lai de kiem tra.
pause
exit /b 1
