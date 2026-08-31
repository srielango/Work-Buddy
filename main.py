"""Entry point for Work Buddy.

Usage:
    python main.py
"""

from work_buddy.app import WorkBuddyApp


def main() -> None:
    app = WorkBuddyApp()
    app.run()


if __name__ == "__main__":
    main()
