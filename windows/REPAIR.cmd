@echo off
setlocal
title Zillion Worker Repair
echo [1/4] Stopping ALL ArenaBridge workers...
if exist "%USERPROFILE%\arenabridge\stop_worker.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\arenabridge\stop_worker.ps1"
) else (
  echo (no stop script - killing all python)
  taskkill /F /IM python.exe 2>nul
  taskkill /F /IM pythonw.exe 2>nul
  taskkill /F /IM python3.13.exe 2>nul
  taskkill /F /IM python3.exe 2>nul
)
timeout /t 3 /nobreak >nul
echo [2/4] Downloading latest worker.py (v4.5.2, single-instance lock)...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/limar01/zillion-restore/main/phone/worker.py' -OutFile $env:USERPROFILE\arenabridge\worker.py -UseBasicParsing"
echo [3/4] Installing hidden launcher + logon autostart (no admin needed)...
(
echo @echo off
echo set ZILLION_LANE=win
echo set BRIDGE_CWD=%%USERPROFILE%%\arenabridge
echo cd /d "%%USERPROFILE%%\arenabridge"
echo start "ArenaBridge Worker" /min pythonw worker.py
) > "%USERPROFILE%\arenabridge\start_worker_hidden.cmd"
schtasks /create /tn ZillionWorker /tr "%USERPROFILE%\arenabridge\start_worker_hidden.cmd" /sc onlogon /f 2>nul
if %ERRORLEVEL%==0 (echo AUTOSTART_OK) else (echo AUTOSTART_SKIPPED ^(manual start still works^))
echo [4/4] Starting ONE hidden worker (pythonw, no window to close by accident)...
set ZILLION_LANE=win
set BRIDGE_CWD=%USERPROFILE%\arenabridge
cd /d "%USERPROFILE%\arenabridge"
start "ArenaBridge Worker" /min pythonw worker.py
timeout /t 5 /nobreak >nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'CommandLine like ''%worker.py%''' | Where-Object { $_.Name -like 'python*' } | Measure-Object | ForEach-Object { Write-Output ('REAL_WORKERS=' + $_.Count) }"
echo.
echo DONE - REAL_WORKERS should be 1. Tell the agent: lane up
pause
