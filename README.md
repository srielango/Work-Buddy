# Work Buddy 🐾 🤖 😊

An adorable, interactive animated desktop pet companion that tracks your working time!
Built with **Python** and **PyQt6** featuring true 32-bit transparent rendering, walking physics, multiple pets, customizable themes, child-friendly interactivity, and automatic Windows startup.

![Platform](https://img.shields.io/badge/Platform-Windows%2011-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- 🐶 **4 Adorable Avatars**:
  - **Puppy Dog**: Bouncy floppy ears, wagging tail, cute snout, happy smile & pant when working!
  - **Kitty Cat**: Alert pointy ears, twitching whiskers, waving tail, cat loaf/sleep pose.
  - **Robot Buddy**: Rotating glowing antenna beacon, glowing visor, and hover thrusters.
  - **Smiley Mascot**: Expressive chibi friend with animated blush cheeks.
- 🎨 **6 Customizable Color Themes**:
  - 🟡 Golden Honey, ⚪ Snow White, 🟤 Chocolate Caramel, 🖤 Midnight Slate, 🌸 Sakura Pink, 🟢 Cyber Emerald.
- 🚀 **Windows Auto-Start / Background Companion**:
  - Automatically launches with Windows on user logon without showing a black console window.
  - 1-Click Toggle right in the companion tummy toolbar (`[ 🚀 Auto-Start ]`).
  - Helper batch scripts included (`enable_autostart.bat`, `disable_autostart.bat`).
- 🚶 **Desktop Walking Physics**:
  - Animated 4-phase walking strides across the desktop with directional left/right turning.
  - Can be toggled on/off with one click (`🚶`/`🛑`).
- 💖 **Interactive Petting & Particles**:
  - Left-clicking/petting spawns floating hearts (`❤️`, `💖`) and sparkles (`✨`).
  - Sleeping spawns soft floating `Zzz` letters.
  - **Drag-to-Carry**: Dragging the pet with your mouse shows a cute dangling legs wiggle animation!
- 📟 **Interactive Tummy Gadget (Expanded Mode)**:
  - The pet sits down and reveals its belly clock gadget!
  - Large, high-contrast digital LCD display (`01:42:35`) visible on any desktop background.
  - Big **Belly Button** toggle (`[ ▶ START ]` / `[ ⏹ STOP ]`).
  - Activity / Project selector with task memory.
  - 1-Click Avatar & Color Theme switchers.
  - Today's accumulated time + Weekly summary + Monthly Excel export.
- ⏱️ **Bulletproof Time Tracking**:
  - Real timestamp difference calculations (`datetime.now() - start_time`), never tick-counting.
  - Survives crashes and computer sleep.
  - Midnight auto-close at 23:59:59.
  - Atomic JSON persistence (`worklog.json`).

---

## Quick Start

### 1. Install Requirements

```bash
cd "c:\SourceCode\Work Buddy"
pip install -r requirements.txt
```

### 2. Run Application

```bash
python main.py
```

---

## Enabling / Disabling Windows Auto-Start

You can enable or disable starting with Windows using any of these 3 methods:

1. **Inside the App**: Click the `🚀` button in the pet's expanded toolbar to toggle auto-start on/off.
2. **Double-click batch script**: Run `enable_autostart.bat` or `disable_autostart.bat`.
3. **Command line**:
   ```bash
   python -m work_buddy.autostart enable
   python -m work_buddy.autostart disable
   python -m work_buddy.autostart status
   ```

---

## Controls & Usage

| Action | How-To |
| :--- | :--- |
| **Pet Character** | Left-click the pet to make it happy and spawn hearts (`❤️`) |
| **Expand Tummy Gadget** | Click the pet's head when collapsed |
| **Collapse Back** | Click the pet's head again when expanded |
| **Pick-up & Drag** | Click and hold with the left mouse button to carry the pet |
| **Switch Avatar** | In expanded mode, click `🐶`, `🐱`, `🤖`, or `😊` |
| **Change Color Theme** | In expanded mode, click `🟡`, `⚪`, `🟤`, `🖤`, `🌸`, or `🟢` |
| **Toggle Walking** | Click `🚶` to pause or enable walking across the desktop |
| **Toggle Auto-Start** | Click `🚀` to enable or disable starting automatically with Windows |
| **Start / Stop Work** | Click the big `[ ▶ START ]` / `[ ⏹ STOP ]` button on the belly |
| **Weekly Summary** | Click the `📊` button on the accessory toolbar |
| **Export to Excel** | Click the `📋` button on the accessory toolbar |
| **Minimize / Hide** | Click `─` to minimize to a tiny floating companion dot |
| **Exit** | Click `✕` (safely saves active session if running) |

---

## Data & Persistence

Data is stored safely outside the installation folder in:

```
%LOCALAPPDATA%\WorkBuddy\
├── worklog.json      ← JSON work sessions (source of truth)
├── settings.json     ← Saved avatar, theme, walking, autostart & window position
└── workbuddy.log     ← Application log
```

---

## Running Unit Tests

```bash
python -m unittest discover -s tests -v
```

All 69 test suites cover start/stop, multi-session tracking, today's totals, weekly breakdown, project summary, autostart registry, recovery, midnight rollover, and Excel exports.

---

## Building Executable (`WorkBuddy.exe`)

```bash
pip install pyinstaller
build.bat
```
The standalone executable will be created in `dist\WorkBuddy.exe`.
