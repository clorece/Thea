@echo off
cd /d "%~dp0"
call venv\Scripts\activate

:: Ensure logs folder exists
if not exist ..\logs mkdir ..\logs

:: Run log with timestamp
echo [STARTUP] Backend starting at %DATE% %TIME% >> ..\logs\backend.log

:: Run python in unbuffered mode (-u) and append all output to log file
python -u -m uvicorn main:app --reload >> ..\logs\backend.log 2>&1
