@echo off
:: Weekly AI & Data Engineering Newsletter — Task Scheduler launcher
:: Activates the project virtual environment and runs the newsletter script.
:: Output is appended to newsletter.log in the same folder.

setlocal

:: Resolve the directory this .bat lives in (newsletter/)
set "SCRIPT_DIR=%~dp0"
:: Project root is one level up
set "ROOT_DIR=%SCRIPT_DIR%.."
set "VENV_PYTHON=%ROOT_DIR%\.venv\Scripts\python.exe"
set "LOG_FILE=%SCRIPT_DIR%newsletter.log"

echo [%DATE% %TIME%] Starting newsletter run >> "%LOG_FILE%"

if not exist "%VENV_PYTHON%" (
    echo [%DATE% %TIME%] ERROR: virtual environment not found at %VENV_PYTHON% >> "%LOG_FILE%"
    echo Virtual environment not found. Run: python -m venv .venv
    exit /b 1
)

"%VENV_PYTHON%" "%SCRIPT_DIR%generate_newsletter.py" >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% neq 0 (
    echo [%DATE% %TIME%] ERROR: script exited with code %ERRORLEVEL% >> "%LOG_FILE%"
    exit /b %ERRORLEVEL%
)

echo [%DATE% %TIME%] Newsletter run complete >> "%LOG_FILE%"
endlocal
