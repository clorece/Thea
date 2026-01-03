@echo off
echo ==========================================
echo      RIN - SYSTEM SETUP
echo ==========================================

echo [1/3] Detecting Python...
set CARBON_PYTHON=python

:: Check if python exists
python --version > nul 2>&1
if errorlevel 1 (
    :: Try py launcher
    py --version > nul 2>&1
if errorlevel 1 (
        echo   ! Python not found. Launching installer...
        call python_setup.bat
        echo.
        echo   ! Installation complete?
        echo   ! Press any key to RESTART this setup script and detect the new version.
        pause
        start "" "%~f0"
        exit
    ) else (
        set CARBON_PYTHON=py
    )
)

:: Check Version >= 3.10
echo   - Checking Python version...
%CARBON_PYTHON% -c "import sys; exit(0) if sys.version_info >= (3, 10) else exit(1)"
if errorlevel 1 (
    echo.
    echo   ! Python Version Update Required.
    echo   ! Launching installer for Python 3.11...
    call python_setup.bat
    echo.
    echo   ! Installation complete?
    echo   ! Press any key to RESTART this setup script and detect the new version.
    pause
    start "" "%~f0"
    exit
)
echo   - Python 3.10+ detected.

echo [2/3] Setting up Backend...
cd backend
if not exist venv (
    echo   - Creating virtual environment...
    %CARBON_PYTHON% -m venv venv
)
if not exist venv (
    echo   ! FAIL: Could not create venv.
    pause
    exit /b
)

echo   - Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip > nul 2>&1

echo   - Installing/Updating backend dependencies...
venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
if errorlevel 1 (
    echo   ! FAIL: Backend dependency install failed.
    pause
    exit /b
)

echo   - Configuring system integration (pywin32)...
if exist venv\Scripts\pywin32_postinstall.py (
    venv\Scripts\python.exe venv\Scripts\pywin32_postinstall.py -install -silent > nul 2>&1
)
cd ..

echo [3/3] Setting up Frontend...
echo   - Checking npm...
call npm --version > nul 2>&1
if errorlevel 1 (
    echo   ! CRITICAL: Node.js/npm not found. 
    echo   ! Launching Node.js installer...
    call nodejs_setup.bat
    echo.
    echo   ! Installation complete?
    echo   ! Press any key to RESTART this setup script and detect the new version.
    pause
    start "" "%~f0"
    exit
)

cd frontend
echo   - Installing/Updating frontend dependencies...
call npm install
if errorlevel 1 (
    echo   ! FAIL: Frontend dependency install failed.
    pause
    exit /b
)
cd ..

echo ==========================================
echo ==========================================
echo      SETUP COMPLETE - READY TO START
echo ==========================================
echo.
if not exist GEMINI_API_KEY.txt (
    echo [!] WARNING: GEMINI_API_KEY.txt not found!
    echo     Rin needs an API Key to see and hear.
    echo     Please create 'GEMINI_API_KEY.txt' in this folder and paste your key inside.
    echo.
) else (
    echo [OK] API Key detected.
)

echo You can now run 'start.bat'
pause
