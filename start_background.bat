@echo off
REM Launches Work Buddy in the background using pythonw without locking the terminal.
start "" pythonw "%~dp0main.py"
echo Work Buddy started in background.
