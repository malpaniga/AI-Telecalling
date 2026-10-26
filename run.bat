@echo off
setlocal
cd /d "%~dp0"

REM If user wants separate windows: run.bat -s or run.bat --separate
if "%1"=="--separate" goto separate
if "%1"=="-s" goto separate

REM Run unified runner via virtualenv Python if available, or system Python
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py %*
) else (
    python run.py %*
)
goto :eof

:separate
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py --separate
) else (
    python run.py --separate
)
goto :eof
