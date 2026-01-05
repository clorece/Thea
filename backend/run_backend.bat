@echo off
cd /d "%~dp0"
call venv\Scripts\activate

:: Ensure logs folder exists
if not exist ..\logs mkdir ..\logs

:: Run log with timestamp (overwrites previous log on startup)
echo [STARTUP] Backend starting at %DATE% %TIME% > ..\logs\backend.log

:: Clear activity and API usage logs for fresh session
echo. > ..\logs\activity.log
echo. > ..\logs\api_usage.log

:: Force UTF-8 encoding to prevent crash on printing Emojis
set PYTHONIOENCODING=utf-8

:: Run python in unbuffered mode (-u) and append all output to log file
python -u -m uvicorn main:app --reload >> ..\logs\backend.log 2>&1
