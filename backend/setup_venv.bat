@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\" (
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create venv. Is Python installed and on PATH?
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Done. Activate later with:  backend\.venv\Scripts\activate.bat
