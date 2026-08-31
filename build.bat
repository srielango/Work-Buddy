@echo off
REM Build Work Buddy into a single Windows executable.
REM Requires: pip install pyinstaller

echo Building Work Buddy...
pyinstaller ^
    --name WorkBuddy ^
    --onefile ^
    --windowed ^
    --icon=NUL ^
    --add-data "work_buddy;work_buddy" ^
    main.py

echo.
echo Done!  Executable is in dist\WorkBuddy.exe
pause
