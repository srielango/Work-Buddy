# Work Buddy 🤖

A lightweight animated desktop companion that tracks your working time.  
Built entirely in Python with Tkinter — no databases, no web tech, just a friendly little bot on your desktop.

![Concept](https://img.shields.io/badge/Platform-Windows%2011-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- **Frameless floating companion** — uses Windows transparency color-keying so the smiley and timer float directly on your desktop without any rectangular window borders or box background
- **Animated companion** — a canvas-drawn bot with blinking, bouncing, idle, and sleeping animations
- **Click-to-expand** — collapsed mode shows just the bot + timer; expanded mode shows full controls
- **Start / Stop** — single toggle button, optional activity/project per session
- **Multiple sessions per day** — all sessions preserved, never overwritten
- **Crash recovery** — active session persisted immediately; recovered on next launch
- **Midnight handling** — sessions auto-close at 23:59:59 if they cross midnight
- **Weekly summary** — daily + project breakdown for the current week
- **Excel export** — monthly workbook with daily sheets + monthly summary
- **Always on top** — unobtrusive, stays visible while you work
- **Minimize to dot** — tiny restore button when hidden; timer keeps running
- **Desktop wandering** — the bot occasionally drifts when idle (can be disabled)

---

## Quick Start

### Prerequisites

- Python 3.10+ (with Tkinter — included in standard Windows installs)
- pip

### Install & Run

```bash
cd "Work Buddy"
pip install -r requirements.txt
python main.py
```

That's it. The bot appears in the bottom-right corner of your screen.

### Usage

1. **Click the bot** to expand the panel
2. *(Optional)* Type or select an **Activity**
3. Click **START** to begin working
4. Click the bot again to collapse — the timer keeps running
5. Click the bot → **STOP** when you're done

**Toolbar buttons** (expanded mode, bottom):
| Button | Action |
|--------|--------|
| 📊 | Weekly summary |
| 📋 | Export to Excel |
| ─ | Minimize (hide) |
| ✕ | Exit |

---

## Data Storage

All data is stored as JSON in:

```
%LOCALAPPDATA%\WorkBuddy\
├── worklog.json      ← work sessions (source of truth)
├── settings.json     ← user preferences
└── workbuddy.log     ← application log
```

On non-Windows systems, data goes to `~/.workbuddy/`.

### JSON Structure

```json
{
  "active_session": {
    "start": "2026-08-31T09:10:00",
    "activity": "Trading Bot"
  },
  "days": {
    "2026-08-31": {
      "sessions": [
        {
          "start": "2026-08-31T09:10:00",
          "end": "2026-08-31T11:40:00",
          "duration_seconds": 9000,
          "activity": "Trading Bot"
        }
      ]
    }
  }
}
```

- Timestamps: ISO 8601, local time
- Duration: integer seconds (never floating-point)
- Writes are **atomic** (temp file + `os.replace`) to prevent corruption
- Corrupt files are **backed up**, never silently overwritten

---

## Excel Reports

Export → select a month → save as `.xlsx`.

Each workbook contains:
- **Monthly Summary** sheet — date, total hours, sessions count
- **One sheet per day** — Start Time, End Time, Hours Spent, Project/Activity, with totals

The Excel file is generated from JSON data and never modifies it.

---

## Project Structure

```
Work Buddy/
├── main.py                     ← entry point
├── requirements.txt
├── build.bat                   ← PyInstaller build script
├── work_buddy/
│   ├── __init__.py
│   ├── app.py                  ← application orchestrator
│   ├── models.py               ← dataclasses, enums, helpers
│   ├── storage.py              ← JSON persistence (atomic writes)
│   ├── timer_engine.py         ← core time-tracking logic
│   ├── settings.py             ← user settings
│   ├── bot_window.py           ← main Tkinter GUI
│   ├── animations.py           ← canvas animation controller
│   ├── summary_window.py       ← weekly summary window
│   ├── excel_export.py         ← openpyxl Excel generation
│   └── logging_config.py       ← logging setup
└── tests/
    ├── test_models.py
    ├── test_storage.py
    ├── test_timer_engine.py
    └── test_excel_export.py
```

---

## Running Tests

```bash
python -m pytest tests/ -v
# or
python -m unittest discover -s tests -v
```

All tests use an injected clock and temporary directories — no dependency on system time.

---

## Building a Windows Executable

```bash
pip install pyinstaller
build.bat
```

The executable will be at `dist/WorkBuddy.exe`.  
No Python installation required on the target machine.

---

## Settings

Stored in `%LOCALAPPDATA%\WorkBuddy\settings.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `always_on_top` | `true` | Keep bot above other windows |
| `animations_enabled` | `true` | Enable/disable all animations |
| `idle_minutes` | `15` | Minutes before bot looks idle |
| `sleep_minutes` | `30` | Minutes before bot falls asleep |
| `bot_x` / `bot_y` | auto | Saved window position |

Edit the file directly to change settings (restart required).

---

## Windows Startup

To start Work Buddy automatically with Windows:

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `WorkBuddy.exe` (or `python main.py`) in the opened folder

---

## Architecture

```
GUI (bot_window, animations, summary_window)
  │
  ▼
TimerEngine (start, stop, tick, queries)
  │
  ├── Storage → worklog.json
  │
  └── ExcelExporter → .xlsx files
```

The time-tracking engine is **fully independent of the GUI** and can be used without Tkinter.  
All elapsed-time calculations use real timestamps (`datetime.now() - start_time`), never incrementing counters.

---

## License

MIT
