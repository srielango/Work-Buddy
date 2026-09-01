@echo off
REM Removes Work Buddy from Windows startup.
echo Disabling Work Buddy Windows Auto-Start...
python -m work_buddy.autostart disable
echo.
pause
