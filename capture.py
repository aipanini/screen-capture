"""
截图核心模块。

提供全屏截图、窗口截图（PrintWindow 方案）、区域截图、剪贴板写入等功能。
"""

import ctypes
import ctypes.wintypes
import io
import os
import time
from datetime import datetime
from typing import Optional

import win32con
import win32gui
from PIL import Image, ImageGrab

from win_utils import WindowInfo, enable_dpi_awareness


# ── PrintWindow 标志 ────────────────────────────────────────

PW_RENDERFULLCONTENT = 2


# ── 自定义 Windows 结构体 ──────────────────────────────────

class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", ctypes.c_long),
        ("bmWidth", ctypes.c_long),
        ("bmHeight", ctypes.c_long),
        ("bmWidthBytes", ctypes.c_long),
        ("bmPlanes", ctypes.c_short),
        ("bmBitsPixel", ctypes.c_short),
        ("bmBits", ctypes.c_void_p),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


DIB_RGB_COLORS = 0


# ── 截图保存/输出 ──────────────────────────────────────────

def _ensure_output_dir(path: str) -> None:
    """确保输出路径的父目录存在。"""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _generate_default_filename() -> str:
    """生成带时间戳的默认文件名。"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"screenshot_{ts}.png"


def save_or_clipboard(
    image: Image.Image,
    output: Optional[str],
    clipboard: bool,
) -> str:
    """将截图保存到文件或写入剪贴板。

    Args:
        image: PIL Image 对象。
        output: 输出文件路径，None 时自动生成。
        clipboard: 是否写入剪贴板。

    Returns:
        实际使用的文件路径（剪贴板模式返回 "<clipboard>"）。
    """
    if clipboard:
        _write_to_clipboard(image)
        return "<clipboard>"

    if output is None:
        output = _generate_default_filename()

    _ensure_output_dir(output)
    image.save(output, "PNG")
    return output


def _write_to_clipboard(image: Image.Image) -> None:
    """将 PIL Image 写入系统剪贴板（BMP 格式 + PNG 格式）。"""
    import win32clipboard

    output = io.BytesIO()
    image.save(output, format="BMP")
    bmp_data = output.getvalue()[14:]  # 跳过 BITMAPFILEHEADER (14 bytes)
    output.close()

    # 同时准备 PNG 格式用于支持 PNG 剪贴板的应用
    png_output = io.BytesIO()
    image.save(png_output, format="PNG")
    png_data = png_output.getvalue()
    png_output.close()

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        # 设置 BMP 格式（兼容性最好）
        win32clipboard.SetClipboardData(win32con.CF_DIB, bmp_data)
        # 尝试设置 PNG 格式（部分应用支持）
        try:
            win32clipboard.SetClipboardData(
                win32clipboard.RegisterClipboardFormat("PNG"),
                png_data,
            )
        except Exception:
            pass
    finally:
        win32clipboard.CloseClipboard()


# ── 全屏截图 ────────────────────────────────────────────────

def capture_screen(monitor: int = 0) -> Image.Image:
    """全屏截图。

    Args:
        monitor: 显示器索引（0=主显示器，1=副显示器...）。

    Returns:
        PIL Image 对象。
    """
    enable_dpi_awareness()
    if monitor == 0:
        return ImageGrab.grab()
    else:
        # 多显示器：使用 EnumDisplayMonitors 获取各显示器区域
        display_monitors = []

        def _monitor_enum(hmonitor, hdc, rect, data):
            display_monitors.append(rect)
            return True

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.POINTER(ctypes.wintypes.RECT),
            ctypes.c_long,
        )
        ctypes.windll.user32.EnumDisplayMonitors(
            None, None, callback_type(_monitor_enum), 0
        )

        if monitor - 1 < len(display_monitors):
            r = display_monitors[monitor - 1]
            bbox = (r.left, r.top, r.right, r.bottom)
        else:
            raise ValueError(f"显示器索引 {monitor} 不存在，当前系统有 {len(display_monitors) + 1} 个显示器")

        return ImageGrab.grab(bbox=bbox)


# ── 窗口截图（PrintWindow 方案）────────────────────────────

def capture_window(window: WindowInfo) -> Image.Image:
    """使用 PrintWindow API 截取指定窗口。

    使用 PW_RENDERFULLCONTENT 标志，与微信截图同方案，
    可截取包括 UAC 管理员窗口在内的绝大多数窗口。

    Args:
        window: 目标窗口信息。

    Returns:
        PIL Image 对象。
    """
    enable_dpi_awareness()
    hwnd = window.hwnd
    rect = win32gui.GetWindowRect(hwnd)
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]

    if width <= 0 or height <= 0:
        raise ValueError(f"窗口 '{window.title}' 的尺寸无效: {width}x{height}")

    # 获取窗口设备上下文
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mem_dc = ctypes.windll.gdi32.CreateCompatibleDC(hwnd_dc)
    bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    old_bmp = ctypes.windll.gdi32.SelectObject(mem_dc, bmp)

    try:
        # 使用 PrintWindow 进行截图
        result = ctypes.windll.user32.PrintWindow(
            hwnd, mem_dc, PW_RENDERFULLCONTENT
        )
        if not result:
            raise RuntimeError(f"PrintWindow 调用失败，窗口句柄: {hwnd}")

        # 从位图获取像素数据
        bmp_info = BITMAP()
        ctypes.windll.gdi32.GetObjectW(bmp, ctypes.sizeof(bmp_info), ctypes.byref(bmp_info))

        bmp_header = BITMAPINFOHEADER()
        bmp_header.biSize = ctypes.sizeof(bmp_header)
        bmp_header.biWidth = bmp_info.bmWidth
        bmp_header.biHeight = -bmp_info.bmHeight  # 自顶向下
        bmp_header.biPlanes = 1
        bmp_header.biBitCount = 32
        bmp_header.biCompression = 0  # BI_RGB

        buffer_size = bmp_info.bmWidth * bmp_info.bmHeight * 4
        buffer = ctypes.create_string_buffer(buffer_size)

        ctypes.windll.gdi32.GetDIBits(
            mem_dc, bmp, 0, bmp_info.bmHeight,
            buffer, ctypes.byref(bmp_header), DIB_RGB_COLORS,
        )

        image = Image.frombytes(
            "RGBA",
            (bmp_info.bmWidth, bmp_info.bmHeight),
            buffer.raw,
        )

        # 去除 Alpha 通道（PrintWindow 输出的 alpha 可能为 0）
        image = image.convert("RGB")

        return image

    finally:
        ctypes.windll.gdi32.SelectObject(mem_dc, old_bmp)
        ctypes.windll.gdi32.DeleteObject(bmp)
        ctypes.windll.gdi32.DeleteDC(mem_dc)
        win32gui.ReleaseDC(hwnd, hwnd_dc)


# ── 区域截图 ────────────────────────────────────────────────

def capture_region(x: int, y: int, w: int, h: int) -> Image.Image:
    """截取屏幕指定矩形区域。

    Args:
        x: 区域左上角 X 坐标（虚拟屏幕坐标）。
        y: 区域左上角 Y 坐标（虚拟屏幕坐标）。
        w: 区域宽度。
        h: 区域高度。

    Returns:
        PIL Image 对象。
    """
    enable_dpi_awareness()
    bbox = (x, y, x + w, y + h)
    return ImageGrab.grab(bbox=bbox)


# ── 统一截图入口 ──────────────────────────────────────────

def do_capture(
    mode: str,
    window: Optional[WindowInfo] = None,
    region: Optional[tuple] = None,
    monitor: int = 0,
    output: Optional[str] = None,
    clipboard: bool = False,
    delay: int = 0,
) -> str:
    """统一截图入口。

    Args:
        mode: 截图模式 "screen" / "window" / "region"。
        window: 窗口截图时的目标窗口（mode="window" 时必需）。
        region: 区域截图时的 (x, y, w, h)（mode="region" 时必需）。
        monitor: 全屏截图时的显示器索引。
        output: 输出文件路径。
        clipboard: 是否写入剪贴板。
        delay: 截图前延迟毫秒数。

    Returns:
        实际输出路径或 "<clipboard>"。
    """
    if delay > 0:
        time.sleep(delay / 1000.0)

    if mode == "screen":
        image = capture_screen(monitor=monitor)
    elif mode == "window":
        if window is None:
            raise ValueError("窗口截图模式需要指定 window 参数")
        image = capture_window(window)
    elif mode == "region":
        if region is None:
            raise ValueError("区域截图模式需要指定 region 参数")
        image = capture_region(*region)
    else:
        raise ValueError(f"未知截图模式: {mode}")

    return save_or_clipboard(image, output, clipboard)
