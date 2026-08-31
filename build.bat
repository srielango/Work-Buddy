@echo off
REM Build Work Buddy (PyQt6 Desktop Companion) into a single Windows executable.
REM Requires: pip install pyinstaller PyQt6 openpyxl

echo Building Work Buddy Desktop Companion...
pyinstaller ^
    --name WorkBuddy ^
    --onefile ^
    --windowed ^
    --add-data "work_buddy;work_buddy" ^
    main.py

echo.
echo Done! Executable is in dist\WorkBuddy.exe
pause
