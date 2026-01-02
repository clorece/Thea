@echo off
echo ==========================================
echo      RIN - SYSTEM SETUP
echo ==========================================

echo [1/3] Detecting Python...
python --version > nul 2>&1
if not errorlevel 1 (
    set CARBON_PYTHON=python
    echo   - Found 'python' command.
) else (
    py --version > nul 2>&1
    if not errorlevel 1 (
        set CARBON_PYTHON=py
        echo   - Found 'py' launcher.
    ) else (
        echo   ! CRITICAL: Python not found.
        echo   ! Please run 'debug.bat' for troubleshooting instructions.
        pause
        exit /b
    )
)

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
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo   ! FAIL: Backend dependency install failed.
    pause
    exit /b
)
cd ..

echo [3/3] Setting up Frontend...
echo   - Checking npm...
call npm --version > nul 2>&1
if errorlevel 1 (
    echo   ! CRITICAL: Node.js/npm not found. 
    echo   ! Please install Node.js from https://nodejs.org/
    pause
    exit /b
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
echo      SETUP COMPLETE - READY TO START
echo ==========================================
echo You can now run 'start.bat'
pause
