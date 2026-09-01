@echo off
REM Closes running Work Buddy pythonw instances.
taskkill /F /FI "WINDOWTITLE eq Work Buddy" >nul 2>&1
echo Closed Work Buddy.
