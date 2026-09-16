@echo off
setlocal
title Zillion Worker Repair
echo [1/3] Stopping ALL ArenaBridge workers...
if exist "%USERPROFILE%\arenabridge\stop_worker.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%USERPROFILE%\arenabridge\stop_worker.ps1"
) else (
  echo (no stop script - killing all python)
  taskkill /F /IM python.exe 2>nul
  taskkill /F /IM pythonw.exe 2>nul
)
timeout /t 3 /nobreak >nul
echo [2/3] Downloading latest worker.py (v4.5.2, single-instance lock)...
powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/limar01/zillion-restore/main/phone/worker.py' -OutFile $env:USERPROFILE\arenabridge\worker.py -UseBasicParsing"
echo [3/3] Starting ONE worker...
set ZILLION_LANE=win
set BRIDGE_CWD=%USERPROFILE%\arenabridge
cd /d "%USERPROFILE%\arenabridge"
where python >nul 2>nul
if %ERRORLEVEL%==0 (set PYBIN=python) else (set PYBIN=py -3)
start "ArenaBridge Worker" /min %PYBIN% worker.py
timeout /t 4 /nobreak >nul
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE
tasklist /FI "IMAGENAME eq pythonw.exe" /FO TABLE
echo.
echo DONE - exactly ONE python worker should show above. Tell the agent: lane up
pause
