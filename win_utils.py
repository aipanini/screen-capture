"""
Windows 窗口管理工具模块。

提供窗口枚举、模糊匹配、置顶、DPI 感知等功能。
所有函数均基于 pywin32 的 win32gui / win32process / win32con。
"""

import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from typing import Optional

import win32api
import win32con
import win32gui
import win32process


@dataclass
class WindowInfo:
    """窗口信息数据类。"""
    hwnd: int          # 窗口句柄
    title: str         # 窗口标题
    class_name: str    # 窗口类名
    pid: int           # 进程 ID
    process_name: str  # 进程名
    is_visible: bool   # 是否可见
    rect: tuple        # (left, top, right, bottom)

    def to_dict(self) -> dict:
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "class_name": self.class_name,
            "pid": self.pid,
            "process_name": self.process_name,
            "is_visible": self.is_visible,
            "rect": list(self.rect),
        }


# ── DPI 感知 ──────────────────────────────────────────────

def enable_dpi_awareness() -> None:
    """启用 PerMonitorV2 DPI 感知，确保高分屏下坐标与截图准确。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


# ── 窗口枚举 ──────────────────────────────────────────────

def _get_process_name(pid: int) -> str:
    """根据 PID 获取进程名。"""
    handle = None
    try:
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        # 用 ctypes 调用 GetModuleFileNameExW（第二个参数传 0 表示主模块）
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.psapi.GetModuleFileNameExW(
            ctypes.c_void_p(int(handle)), ctypes.c_void_p(0), buf, 260
        )
        name = buf.value.split("\\")[-1]
        return name
    except Exception:
        return "unknown"
    finally:
        if handle is not None:
            try:
                ctypes.windll.kernel32.CloseHandle(int(handle))
            except Exception:
                pass


def _enum_callback(hwnd: int, windows: list) -> bool:
    """win32gui.EnumWindows 的回调函数，收集窗口信息。"""
    try:
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        is_visible = bool(win32gui.IsWindowVisible(hwnd))
        rect = win32gui.GetWindowRect(hwnd)

        # 跳过无标题且不可见的窗口（减少噪音）
        if not title and not is_visible:
            return True

        process_name = _get_process_name(pid)

        windows.append(WindowInfo(
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            pid=pid,
            process_name=process_name,
            is_visible=is_visible,
            rect=rect,
        ))
    except Exception:
        pass
    return True


def list_windows(visible_only: bool = True) -> list[WindowInfo]:
    """枚举系统窗口。

    Args:
        visible_only: 是否只返回可见窗口（默认 True）。

    Returns:
        WindowInfo 列表，按标题排序。
    """
    enable_dpi_awareness()
    windows: list[WindowInfo] = []
    win32gui.EnumWindows(_enum_callback, windows)
    if visible_only:
        windows = [w for w in windows if w.is_visible]
    windows.sort(key=lambda w: w.title.lower())
    return windows


# ── 窗口匹配 ──────────────────────────────────────────────

def find_windows(keyword: str, visible_only: bool = True) -> list[WindowInfo]:
    """按标题关键字模糊匹配窗口（不区分大小写）。

    Args:
        keyword: 匹配关键字，窗口标题包含此字符串即命中。
        visible_only: 是否只在可见窗口中搜索（默认 True）。

    Returns:
        匹配的 WindowInfo 列表。
    """
    all_windows = list_windows(visible_only=visible_only)
    if not keyword:
        return all_windows
    keyword_lower = keyword.lower()
    return [w for w in all_windows if keyword_lower in w.title.lower()]


def find_single_window(keyword: str, visible_only: bool = True) -> WindowInfo:
    """查找唯一匹配窗口，多个匹配时抛出 ValueError。

    Args:
        keyword: 匹配关键字。
        visible_only: 是否只在可见窗口中搜索。

    Returns:
        唯一匹配的 WindowInfo。

    Raises:
        ValueError: 无匹配或多个匹配时。
    """
    matches = find_windows(keyword, visible_only)
    if not matches:
        raise ValueError(f"未找到标题包含 '{keyword}' 的窗口")
    if len(matches) > 1:
        titles = [f"  [{w.hwnd}] {w.title} ({w.process_name})" for w in matches]
        raise ValueError(
            f"找到 {len(matches)} 个匹配窗口，请指定更精确的关键字：\n"
            + "\n".join(titles)
        )
    return matches[0]


# ── 窗口置顶 ──────────────────────────────────────────────

def focus_window(window: WindowInfo, restore: bool = False) -> None:
    """将指定窗口置顶到最前端。

    Args:
        window: 目标窗口信息。
        restore: 如果窗口最小化，是否先恢复（默认 False）。
    """
    hwnd = window.hwnd

    if restore:
        # 先尝试恢复最小化/最大化的窗口
        placement = win32gui.GetWindowPlacement(hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    # 设置为前台窗口
    # Windows 限制：只有前台进程才能调用 SetForegroundWindow
    # 通过 AttachThreadInput 绕过此限制
    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        foreground_tid = win32process.GetWindowThreadProcessId(foreground_hwnd)[0]
        current_tid = win32process.GetCurrentThreadId()

        if foreground_tid != current_tid:
            ctypes.windll.user32.AttachThreadInput(foreground_tid, current_tid, True)
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            ctypes.windll.user32.AttachThreadInput(foreground_tid, current_tid, False)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # 备用方案：直接设置
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.SetForegroundWindow(hwnd)

    # 确保窗口不被其他窗口遮挡
    win32gui.BringWindowToTop(hwnd)
