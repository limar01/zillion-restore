@echo off
REM Zillion Restore — Windows Launcher
setlocal
set SCRIPT_DIR=%~dp0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%zillionPS.ps1" %*
endlocal
