@echo off
REM Registers Work Buddy to launch automatically on Windows startup.
echo Enabling Work Buddy Windows Auto-Start...
python -m work_buddy.autostart enable
echo.
pause
