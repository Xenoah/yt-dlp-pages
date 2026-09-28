@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  set "YTDLP_PYTHON=py -3"
) else (
  set "YTDLP_PYTHON=python"
)
%YTDLP_PYTHON% -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is required.
  echo Install Python from https://www.python.org/downloads/
  echo Then run this file again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  %YTDLP_PYTHON% -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -c "import yt_dlp" >nul 2>nul
if errorlevel 1 (
  echo Installing yt-dlp in the bridge's own Python environment...
  .venv\Scripts\python.exe -m pip install --upgrade "yt-dlp[default]"
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe bridge.py
pause
exit /b 0
:fail
echo Setup failed. Check your internet connection and Python installation.
pause
exit /b 1
