@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Local environment not found. Follow the setup instructions in README.md.
    pause
    exit /b 1
)
start "DataClean" ".venv\Scripts\pythonw.exe" "main.py" %*
