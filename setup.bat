@echo off
echo ==========================================
echo      RIN - SYSTEM SETUP
echo ==========================================

echo [1/5] Detecting Python...
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

echo [2/5] Checking Ollama...
ollama --version > nul 2>&1
if errorlevel 1 (
    echo   ! WARNING: Ollama not found!
    echo   ! Please install Ollama from: https://ollama.com/download
    echo   ! After installation, run this setup again.
    echo.
    pause
    exit /b
)
echo   - Ollama detected.

echo   - Pulling required models...
echo   - Downloading gemma3:4b (chat model)...
ollama pull gemma3:4b
echo   - Downloading llama3.2-vision:latest (vision model)...
ollama pull llama3.2-vision:latest
echo   - Models ready.

echo [3/5] Setting up Backend...
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


echo   - Installing PyTorch with CUDA support...
venv\Scripts\python.exe -m pip uninstall -y torch torchvision 2>nul
venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

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

echo [4/5] Building Audio Capture Tool...
:: Check if dotnet is available
dotnet --version > nul 2>&1
if errorlevel 1 (
    echo   ! .NET SDK not found. Installing audio capture pre-built binary...
    :: The tool is already built as self-contained, so this is OK
    if exist tools\AudioCapture\publish\AudioCapture.exe (
        echo   - Pre-built AudioCapture.exe found.
    ) else (
        echo   ! WARNING: AudioCapture.exe not found and .NET not available.
        echo   ! Audio capture may not work. Install .NET 8 SDK to build from source.
    )
) else (
    echo   - .NET detected. Building AudioCapture tool...
    cd tools\AudioCapture
    dotnet publish -c Release -o publish --self-contained true > nul 2>&1
    if errorlevel 1 (
        echo   ! WARNING: AudioCapture build failed. Using pre-built if available.
    ) else (
        echo   - AudioCapture tool built successfully.
    )
    cd ..\..
)

echo [5/5] Setting up Frontend...
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
echo [OK] All dependencies installed.
echo [OK] Ollama models downloaded.
echo [OK] Audio capture tool ready.
echo.
echo You can now run 'start.bat'
pause
