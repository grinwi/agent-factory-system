@echo off
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\bootstrap.py
) else (
  python scripts\bootstrap.py
)

pause
