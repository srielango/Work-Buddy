"""Windows auto-start management for Work Buddy.

Registers Work Buddy to launch automatically upon Windows user logon using
the standard Windows Registry Run key (HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run).

Uses ``pythonw.exe`` when running from Python source to ensure no black console
window flashes during Windows startup.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("workbuddy")

REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "WorkBuddy"


def _get_launch_command() -> str:
    """Determine the command string to launch Work Buddy without a console."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller .exe
        exe_path = Path(sys.executable).resolve()
        return f'"{exe_path}"'

    # Running from Python source — prefer pythonw.exe over python.exe
    py_dir = Path(sys.executable).parent
    pythonw = py_dir / "pythonw.exe"
    executable = pythonw if pythonw.exists() else Path(sys.executable)

    # Path to main.py
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{executable}" "{main_py}"'


def is_autostart_enabled() -> bool:
    """Check if Work Buddy is currently registered in Windows Startup registry."""
    if sys.platform != "win32":
        return False

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ
        ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except OSError as exc:
        logger.warning("Failed to check autostart registry: %s", exc)
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable Work Buddy starting automatically on Windows logon."""
    if sys.platform != "win32":
        logger.info("Autostart is only supported on Windows")
        return False

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                cmd = _get_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
                logger.info("Auto-start registered in registry: %s", cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                    logger.info("Auto-start removed from registry")
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        logger.error("Failed to update Windows autostart registry: %s", exc)
        return False


def enable_autostart() -> bool:
    return set_autostart(True)


def disable_autostart() -> bool:
    return set_autostart(False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage Work Buddy Windows Auto-Start")
    parser.add_argument(
        "action",
        choices=["enable", "disable", "status"],
        help="Action to perform",
    )
    args = parser.parse_args()

    if args.action == "enable":
        if enable_autostart():
            print("Successfully enabled Work Buddy to start automatically with Windows!")
            print(f"Command: {_get_launch_command()}")
        else:
            print("Failed to enable auto-start.")
    elif args.action == "disable":
        if disable_autostart():
            print("Successfully disabled Work Buddy auto-start.")
        else:
            print("Failed to disable auto-start.")
    elif args.action == "status":
        enabled = is_autostart_enabled()
        print(f"Work Buddy Auto-Start is currently: {'ENABLED' if enabled else 'DISABLED'}")
        if enabled:
            print(f"Launch Command: {_get_launch_command()}")
