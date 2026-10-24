<p align="center">
  <img src="assets/aplomb.png" width="96" alt="Aplomb logo">
</p>

<h1 align="center">Aplomb</h1>

<p align="center">
  <b>Precision window centering for Windows</b><br>
  <sub>Three configurable global shortcuts · pixel-perfect alignment · thumbnail picker · system tray</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.1-blue?style=flat-square" alt="Version 1.1.1">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/framework-PySide6-41CD52?style=flat-square&logo=qt" alt="PySide6">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License">
</p>

<p><a href="README.md">简体中文</a> · <b>English</b></p>

## Overview

**Aplomb** means both composure and plumb alignment. The application follows the same idea: stay out of the way and put windows exactly where they belong.

Aplomb lives in the system tray and centers windows through three optional global shortcuts. It also includes a thumbnail picker for arranging several windows, a centering-memory list that keeps your apps centered, an ignore list, and light and dark themes. It does not poll the window list while idle, and its per-user installer does not require administrator privileges.

![Aplomb settings in dark mode](screenshots/general-dark.png)

## Why another window-centering tool?

On Windows, `GetWindowRect` includes the invisible shadow drawn by the Desktop Window Manager. Centering that rectangle can leave the visible window a few pixels high and to the left.

Aplomb reads `DWMWA_EXTENDED_FRAME_BOUNDS`, aligns the visible frame, and then compensates for the shadow offset. The result is repeatable, pixel-accurate centering. You can disable this correction in Settings for comparison.

## Features

- **Three focused actions:** center the active window, choose windows to center, or center every eligible window.
- **Centering memory:** apps you center are remembered, and their new windows are re-centered automatically in about a tenth of a second. If the app repositions its own window afterwards, Aplomb pulls it back — and stops the moment you drag the window yourself. Event-driven (`SetWinEventHook`), with no polling while idle. The toggle and the remembered list live together on the Program lists page in Settings.
- **Unassigned shortcuts by default:** Aplomb does not claim global key combinations until you record them in Settings. Each shortcut can also be cleared instantly.
- **Thumbnail picker:** filter by title or process name, navigate with the keyboard, and select multiple windows with `Ctrl` + click.
- **Multi-monitor awareness:** each window is centered on the display that currently contains it.
- **Automatic exclusions:** skips full-screen, maximized, shell, ignored, and unresponsive windows.
- **Program lists:** an ignore list plus the remembered list of the centering memory, each manageable by picking from open windows or choosing an executable. The remembered list updates in real time while the settings window is open.
- **System, light, and dark themes:** a restrained interface with flat colors, thin borders, and rounded corners.
- **Low idle overhead:** hotkey-driven operation with no continuous window polling.

## Using the picker

- Start typing to filter by window title or process name.
- Use the arrow keys to move, `Enter` to center, and `Esc` to cancel and return focus to the original window.
- Hold `Ctrl` while clicking to select and center multiple windows at once.

![Aplomb window picker](screenshots/picker-dark.png)

## Installation

### Installer

Download `Aplomb-Setup-1.1.1.exe` from [Releases](../../releases).

- Installs to `%LOCALAPPDATA%\Programs\Aplomb` without a UAC prompt.
- Can create a desktop shortcut and start Aplomb when you sign in.
- Adds Start menu and Windows uninstall entries.
- Keeps settings in `%APPDATA%\Aplomb` when the application is uninstalled.

### Portable build

Download `Aplomb-1.1.1-portable.zip`, extract it, and run `Aplomb.exe`.

Portable settings are stored in the adjacent `data\` directory. Delete `portable.txt` if you prefer to store settings in `%APPDATA%\Aplomb` instead.

### Run from source

Requirements: Windows 10 or 11 and Python 3.10 or later.

```powershell
git clone https://github.com/StarsofDeduce/Aplomb.git
cd Aplomb
python -m pip install -r requirements.txt
python main.py
```

## Configuration

- Installed build: `%APPDATA%\Aplomb\config.json`
- Portable build: `<application directory>\data\config.json`

```json
{
  "hotkey_center_current": "",
  "hotkey_center_select": "",
  "hotkey_center_all": "",
  "autostart": false,
  "show_notifications": true,
  "pixel_perfect": true,
  "theme": "system",
  "picker_thumbnails": true,
  "ignore_list": [],
  "remember_centered": true,
  "remembered_apps": []
}
```

## Building

```powershell
python -m pip install -r requirements-dev.txt
python build.py            # executable, portable archive, and installer
python build.py exe        # executable only
python build.py portable   # portable archive only
python build.py setup      # installer only
```

Build output is written to `dist/`.

`requirements.txt` and `requirements-dev.txt` are complete, hash-locked dependency files. To update them, edit the matching `.in` file and regenerate the lock files:

```powershell
python -m pip install pip-tools
pip-compile --allow-unsafe --generate-hashes --strip-extras -o requirements.txt requirements.in
pip-compile --allow-unsafe --generate-hashes --strip-extras -o requirements-dev.txt requirements-dev.in
```

The installer is built with [NSIS](https://nsis.sourceforge.io/). Extract NSIS to `.tools/nsis/`, or point the build to an existing installation:

```powershell
$env:NSIS_MAKENSIS = "C:/Program Files (x86)/NSIS/makensis.exe"
python build.py setup
```

## Screenshots

| Hotkey settings | Light theme |
| :--- | :--- |
| ![Hotkey settings](screenshots/hotkeys-dark.png) | ![Light theme](screenshots/general-light.png) |

| Program lists | Choose from open windows |
| :--- | :--- |
| ![Program lists](screenshots/lists-dark.png) | ![Window chooser](screenshots/chooser-dark.png) |

## Project structure

```text
Aplomb/
├── app/
│   ├── win32api.py           # ctypes declarations and safe Win32 wrappers
│   ├── windows.py            # window discovery, filtering, and centering
│   ├── remember.py           # event-driven centering memory
│   ├── hotkeys.py            # RegisterHotKey and native event filtering
│   ├── thumbnails.py         # PrintWindow thumbnail capture
│   ├── icons.py              # application icon loading and caching
│   ├── config.py             # atomic JSON configuration and portable mode
│   ├── autostart.py          # per-user HKCU Run integration
│   └── ui/                   # settings, picker, tray, theme, and widgets
├── installer/                # NSIS script and generated artwork
├── assets/                   # runtime icons and images
├── design/                   # icon source artwork
├── screenshots/
├── tools/                    # tests, smoke checks, and build helpers
├── main.py
├── build.py
├── requirements.in
├── requirements.txt
├── requirements-dev.in
└── requirements-dev.txt
```

## Development checks

```powershell
python tools/selftest.py    # centering accuracy, hotkeys, and self-window handling
python tools/ui_smoke.py    # settings and picker interaction checks
python tools/e2e.py         # real-process hotkey-to-centering flow with screenshots
python tools/hang_probe.py  # startup time and UI-thread responsiveness
```

## Implementation notes

- Window geometry is read again for every operation; reusing an old rectangle can make repeated centering drift.
- Minimized windows are never measured with `GetWindowRect` — it reports the off-screen parking slot at (-32000, -32000) with a stub size. The real restore rectangle comes from `GetWindowPlacement`, and restore positions are written back with `SetWindowPlacement`, so an app can never save a corrupted geometry from Aplomb's move.
- Restoring a window is awaited before any move; if the target process is still busy, Aplomb sets the restore position instead of moving the window in a transient state.
- Pure moves pass `SWP_NOSIZE` so the target app receives no spurious `WM_SIZE`.
- Shadow compensation is clamped to a sane margin; if `GetWindowRect` and the DWM frame bounds disagree wildly (for example under DPI virtualization), Aplomb falls back to plain rectangle centering instead of producing a wild offset.
- The process declares per-monitor-v2 DPI awareness itself at startup, before any window exists — window coordinates are physical pixels by contract, not by Qt's implicit behavior.
- The centering memory listens for `EVENT_OBJECT_SHOW`, centers after ~80 ms, then briefly watches `EVENT_OBJECT_LOCATIONCHANGE`: if the app repositions its own window, Aplomb pulls it back within tens of milliseconds. `EVENT_SYSTEM_MOVESIZESTART` ends the tracking immediately, so a user drag always wins. Each window is corrected at most a few times and tracked for only a couple of seconds.
- Settings pages pin their layout size hints below the visible area of the fixed-size translucent window. Qt enlarges a fixed frameless translucent window during geometry changes whenever a page's preferred height exceeds the visible area — the stretch-then-freeze some users saw when dragging the settings window in early 1.1.0 builds.
- Window titles are read with `SendMessageTimeout` after checking `IsHungAppWindow`, so an unresponsive application cannot freeze the picker.
- Duplicate Qt native `WM_HOTKEY` deliveries are filtered by message identity and timestamp.
- Picker thumbnails release GDI resources promptly, and deferred Qt deletions are explicitly drained when the picker closes.

Measured on a 1080p desktop with seven open windows:

| State | Memory use |
| :--- | :--- |
| PySide6 tray baseline | 46.8 MB |
| Aplomb idle in the tray | 50.9 MB |
| Settings window open | about 70 MB |
| Picker open with thumbnails | about 80 MB |
| After 14 picker open/close cycles | 76.7 MB, stable |

## Known limitations

- Windows 10 and 11 only.
- Exclusive full-screen windows are intentionally not moved.
- The centering memory tracks a window for only a couple of seconds after it appears; an app that keeps repositioning its window afterwards is left alone, and can be excluded via the ignore list if its behavior is undesirable.
- Some Electron or hardware-accelerated windows cannot be captured with `PrintWindow`; the picker displays the application icon instead.
- Do not run installed and portable builds at the same time. A single-instance lock redirects the second launch to the existing process.
- The dark-blue half of the tray icon has limited contrast on dark taskbars at 16 px.

## License

[MIT](LICENSE)
