@echo off
echo Starting Backend in DEBUG mode (Visible Console)...
echo.
cd backend
if not exist venv (
    echo ! ERROR: venv missing. Run setup.bat first.
    pause
    exit /b
)
venv\Scripts\python.exe -m uvicorn main:app --reload
pause
