"""Entry point for Work Buddy Desktop Companion.

Usage:
    python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path when launched by Windows Startup from other directories
_project_root = str(Path(__file__).resolve().parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from work_buddy.pyqt_app import WorkBuddyAppQt


def main() -> None:
    app = WorkBuddyAppQt()
    app.run()


if __name__ == "__main__":
    main()
