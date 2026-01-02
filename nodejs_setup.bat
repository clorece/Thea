@echo off
echo ==========================================
echo      NODE.JS SETUP
echo ==========================================
echo.
echo It looks like Node.js is missing.
echo Attempting to install Node.js (LTS) using Windows Package Manager (winget)...
echo.

winget install -e --id OpenJS.NodeJS.LTS

if errorlevel 1 (
    echo.
    echo ! Winget installation failed or was cancelled.
    echo ! Opening Node.js download page instead...
    start https://nodejs.org/
) else (
    echo.
    echo ==========================================
    echo      INSTALLATION COMPLETE
    echo ==========================================
    echo ! IMPORTANT: You may need to RESTART your computer 
    echo ! or at least close and reopen this terminal for 
    echo ! changes to take effect.
)
pause
