"""Entry point for Work Buddy Desktop Companion.

Usage:
    python main.py
"""

from work_buddy.pyqt_app import WorkBuddyAppQt


def main() -> None:
    app = WorkBuddyAppQt()
    app.run()


if __name__ == "__main__":
    main()
