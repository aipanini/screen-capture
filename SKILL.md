| name | screen-capture |
|---|---|
| description | Captures screenshots (full screen, specific window, or screen region) and brings windows to foreground via CLI. Invoke when user asks to take a screenshot, capture a window, check what's on screen, or bring a window to front. |

# screen-capture

A CLI tool for AI coding agents to capture screenshots on Windows. Supports full screen, specific window (including admin/UAC windows via PrintWindow API), and screen region capture, plus window focus/foreground control.

## Prerequisites

```powershell
pip install Pillow pywin32
```

## CLI Path

```
python cli.py <command> [arguments]
```

## Commands

### list — Enumerate windows

```powershell
python cli.py list                           # table format (default)
python cli.py list --format json             # JSON format for programmatic parsing
python cli.py list --no-visible-filter       # include hidden windows
```

### capture — Screenshot

```powershell
# Full screen
python cli.py capture --screen --output "C:\temp\screenshot.png"
python cli.py capture --screen --clipboard

# Specific window (fuzzy match by title, case-insensitive)
python cli.py capture --window "Chrome" --output "C:\temp\chrome.png"

# Screen region (x, y, width, height)
python cli.py capture --region 0 0 800 600 --output "C:\temp\region.png"

# Multi-monitor
python cli.py capture --screen --monitor 1 --output "C:\temp\monitor2.png"
```

Common flags: `--output PATH` (PNG, auto-generated timestamp if omitted), `--clipboard` (write to clipboard instead of file), `--delay MS` (wait before capturing).

### focus — Bring window to foreground

```powershell
python cli.py focus "Visual Studio Code"
python cli.py focus "Visual Studio Code" --restore   # restore if minimized
```

## Recommended Workflow

1. `list` to discover window titles
2. `focus --restore` if the target window is minimized or obscured
3. `capture --window` to screenshot, using `--delay` if animation/rendering is involved

## Known Limitations

- `--monitor` index follows OS enumeration order, not physical layout
- DirectX/OpenGL exclusive fullscreen apps (e.g. fullscreen games) may not capture correctly
