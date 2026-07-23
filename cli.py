"""
screen-capture CLI 入口。

命令：
  list     - 列出系统可见窗口
  capture  - 截图（全屏/窗口/区域）
  focus    - 窗口置顶
"""

import argparse
import json
import sys

from win_utils import WindowInfo, find_single_window, focus_window, list_windows
from capture import do_capture


def _display_width(text: str) -> int:
    """计算字符串的显示宽度（中文等宽字符算 2，英文算 1）。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in text)


def _pad_to_display(text: str, width: int) -> str:
    """将文本用空格填充到指定显示宽度。"""
    current = _display_width(text)
    if current >= width:
        return text
    return text + ' ' * (width - current)


def _format_table(windows: list[WindowInfo]) -> str:
    """将窗口列表格式化为对齐表格字符串。"""
    if not windows:
        return "（无可见窗口）"

    # 计算各列最大显示宽度
    max_title_disp = max(_display_width(w.title) for w in windows)
    max_title_disp = min(max_title_disp, 50)  # 标题最多显示 50 字符（显示宽度）
    max_proc_disp = max(_display_width(w.process_name) for w in windows)

    header = (
        f"{'HWND':>10}  "
        f"{_pad_to_display('标题', max_title_disp)}  "
        f"{_pad_to_display('进程', max_proc_disp)}  "
        f"{'PID':>8}  "
        f"{'可见':>4}  "
        f"位置/尺寸"
    )
    sep = "-" * len(header)

    lines = [header, sep]
    for w in windows:
        title_display = w.title[:50] if _display_width(w.title) > 50 else w.title
        visible_mark = "✓" if w.is_visible else "✗"
        rect_str = f"({w.rect[0]},{w.rect[1]} {w.rect[2]-w.rect[0]}x{w.rect[3]-w.rect[1]})"
        line = (
            f"{w.hwnd:10}  "
            f"{_pad_to_display(title_display, max_title_disp)}  "
            f"{_pad_to_display(w.process_name, max_proc_disp)}  "
            f"{w.pid:8}  "
            f"{visible_mark:>4}  "
            f"{rect_str}"
        )
        lines.append(line)

    return "\n".join(lines)


def cmd_list(args):
    """处理 list 命令。"""
    windows = list_windows(visible_only=args.visible_only)

    if args.format == "json":
        data = [w.to_dict() for w in windows]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        count = len(windows)
        print(f"当前共 {count} 个{'可见' if args.visible_only else ''}窗口：\n")
        print(_format_table(windows))


def cmd_capture(args):
    """处理 capture 命令。"""
    mode = None
    window = None
    region = None

    if args.screen:
        mode = "screen"
    elif args.window:
        mode = "window"
        window = find_single_window(args.window)
    elif args.region:
        mode = "region"
        if len(args.region) != 4:
            print("错误：--region 需要 4 个参数：X Y W H", file=sys.stderr)
            sys.exit(1)
        region = tuple(int(v) for v in args.region)
    else:
        print("错误：请指定截图模式 --screen / --window / --region", file=sys.stderr)
        sys.exit(1)

    result = do_capture(
        mode=mode,
        window=window,
        region=region,
        monitor=args.monitor,
        output=args.output,
        clipboard=args.clipboard,
        delay=args.delay,
    )

    if result == "<clipboard>":
        print("截图已写入剪贴板")
    else:
        print(f"截图已保存: {result}")


def cmd_focus(args):
    """处理 focus 命令。"""
    window = find_single_window(args.window)
    focus_window(window, restore=args.restore)
    print(f"已置顶窗口: [{window.hwnd}] {window.title}")


def main():
    parser = argparse.ArgumentParser(
        prog="screen-capture",
        description="屏幕捕获工具 - 供 AI Agent 通过命令行调用",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── list 命令 ──
    list_parser = subparsers.add_parser("list", help="列出系统可见窗口")
    list_parser.add_argument(
        "--visible-only", action="store_true", default=True,
        help="只显示可见窗口（默认开启）",
    )
    list_parser.add_argument(
        "--no-visible-filter", action="store_true", default=False,
        help="显示所有窗口（包括隐藏窗口）",
    )
    list_parser.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="输出格式（默认: table）",
    )
    list_parser.set_defaults(func=cmd_list)

    # ── capture 命令 ──
    cap_parser = subparsers.add_parser("capture", help="截图")
    cap_group = cap_parser.add_mutually_exclusive_group(required=True)
    cap_group.add_argument("--screen", action="store_true", help="全屏截图")
    cap_group.add_argument("--window", type=str, metavar="KEYWORD", help="按关键字匹配窗口截图")
    cap_group.add_argument("--region", nargs=4, metavar=("X", "Y", "W", "H"), help="区域截图（坐标+宽高）")

    cap_parser.add_argument("--monitor", type=int, default=0, help="显示器索引（全屏模式，默认: 0）")
    cap_parser.add_argument("--output", "-o", type=str, default=None, help="输出文件路径（默认自动生成）")
    cap_parser.add_argument("--clipboard", action="store_true", help="截图写入剪贴板而非文件")
    cap_parser.add_argument("--delay", type=int, default=0, help="截图前延迟毫秒数（默认: 0）")
    cap_parser.set_defaults(func=cmd_capture)

    # ── focus 命令 ──
    focus_parser = subparsers.add_parser("focus", help="窗口置顶")
    focus_parser.add_argument("window", type=str, help="窗口标题关键字")
    focus_parser.add_argument("--restore", action="store_true", help="如窗口最小化则先恢复")
    focus_parser.set_defaults(func=cmd_focus)

    args = parser.parse_args()

    # 处理 list 命令的 --no-visible-filter
    if hasattr(args, "no_visible_filter") and args.no_visible_filter:
        args.visible_only = False

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"异常: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
