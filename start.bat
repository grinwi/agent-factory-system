@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\run_local.py
) else (
  python scripts\run_local.py
)

pause
