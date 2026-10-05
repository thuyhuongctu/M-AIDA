@echo off
rem Mo duong link cho nhom chay thu: duong ham Cloudflare (Quick Tunnel, mien phi,
rem khong can tai khoan) noi Internet vao may chu M-AIDA noi bo o cong 8767.
rem Moi lan mo, duong link moi co dang https://<chu ngau nhien>.trycloudflare.com.
rem Dong cua so nay la dong link (M-AIDA tren may van chay).
setlocal
cd /d "%~dp0"
title M-AIDA noi bo - DUONG LINK (dong cua so nay la dong link)

set "CF="
if exist "%~dp0cloudflared.exe" set "CF=%~dp0cloudflared.exe"
if not defined CF where cloudflared >nul 2>&1 && set "CF=cloudflared"
if not defined CF (
  echo [M-AIDA noi bo] Chua co cloudflared.
  echo Cach cai ^(lam mot lan^): mo PowerShell, dan lenh sau roi nhan Enter:
  echo     winget install --id Cloudflare.cloudflared
  echo Cai xong, dong PowerShell va nhap dup lai tep nay.
  goto :error
)

powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8767/api/health -TimeoutSec 3).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo [M-AIDA noi bo] May chu chua chay. Nhap dup CHAY_MAIDA_NOI_BO.bat truoc, doi trinh duyet mo,
  echo roi nhap dup lai tep nay.
  goto :error
)

echo.
echo [M-AIDA noi bo] Dang mo duong link. Tim dong co dang
echo     https://....trycloudflare.com
echo trong khung ben duoi, chep dia chi do gui cho nguoi duoc moi (kem e-mail va mat khau
echo da tao cho ho, gui rieng tung nguoi). Moi lan mo lai, dia chi se khac.
echo.
"%CF%" tunnel --no-autoupdate --url http://127.0.0.1:8767
goto :eof

:error
echo.
pause
exit /b 1
