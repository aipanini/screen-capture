# screen-capture（屏幕捕获工具）

供 AI 代码开发 Agent 通过命令行调用的屏幕捕获工具。支持全屏截图、指定窗口截图（含管理员窗口）、区域截图、窗口置顶等功能。

## 功能

### 命令一览

```powershell
# 列出所有可见窗口（标题、句柄、进程名）
python cli.py list [--visible-only] [--format json|table]

# 全屏截图
python cli.py capture --screen [--monitor 0|1] [--output PATH] [--clipboard] [--delay MS]

# 指定窗口截图
python cli.py capture --window "关键字" [--output PATH] [--clipboard] [--delay MS]

# 指定区域截图
python cli.py capture --region X Y W H [--output PATH] [--clipboard] [--delay MS]

# 窗口置顶
python cli.py focus "关键字" [--restore]
```

### 功能详情

| 命令 | 说明 |
|------|------|
| `list` | 枚举系统所有窗口，默认只显示可见窗口（`--visible-only` 默认开启），输出支持表格（默认）和 JSON 格式 |
| `capture --screen` | 全屏截图，支持多显示器选择（`--monitor` 指定显示器索引） |
| `capture --window` | 按标题关键字模糊匹配窗口截图，使用 `PrintWindow` API 可截取包括 UAC 管理员窗口在内的所有窗口 |
| `capture --region` | 截取屏幕指定矩形区域（左上角坐标 + 宽高） |
| `focus` | 将指定窗口置顶到最前端，`--restore` 参数可将最小化窗口恢复 |
| `--clipboard` | 截图直接写入系统剪贴板，不保存文件 |
| `--delay` | 截图前等待毫秒数（窗口动画/渲染完成后截图） |
| `--output` | 截图保存路径（PNG 格式），不指定时自动生成带时间戳的文件名 |

### 技术实现

- **全屏截图**：`PIL.ImageGrab.grab()` — 利用系统原生截屏能力
- **窗口截图**：`win32gui.PrintWindow()` + `PW_RENDERFULLCONTENT` — 与微信截图同方案，可截取管理员窗口
- **窗口管理**：`pywin32`（`win32gui` / `win32process` / `win32con`）— 窗口枚举、匹配、置顶、恢复
- **DPI 感知**：启用 `PerMonitorV2` DPI 感知，高分屏缩放下坐标与截图准确

### 窗口匹配规则

- 使用**标题模糊匹配**：窗口标题包含指定关键字即命中（不区分大小写）
- 如果多个窗口匹配，列出所有匹配项供选择
- 关键字为空时 `list` 返回全部窗口

### 已知限制

- 多显示器环境下 `--monitor` 索引基于系统枚举顺序，不保证与物理位置对应（可通过 `list` 的输出确认）
- `PrintWindow` 对某些使用 DirectX/OpenGL 全屏独占的应用可能无法正常捕获（如全屏游戏）

## 技术栈

- Python 3.10+
- Pillow（图像处理）
- pywin32（Windows API 调用）

## 安装

```powershell
cd toolkit/screen-capture
pip install -r requirements.txt
```

## 使用示例

```powershell
# 查看当前有哪些窗口
python cli.py list

# 以 JSON 格式输出（便于 AI 解析）
python cli.py list --format json

# 截全屏，保存到指定路径
python cli.py capture --screen --output C:\temp\fullscreen.png

# 截取 Chrome 窗口
python cli.py capture --window "Chrome" --output C:\temp\chrome.png

# 截取屏幕左上角 800x600 区域，延迟 500ms 等窗口渲染完
python cli.py capture --region 0 0 800 600 --output C:\temp\region.png --delay 500

# 将 VS Code 窗口置到最前端
python cli.py focus "Visual Studio Code"

# 将最小化的 VS Code 恢复并置顶
python cli.py focus "Visual Studio Code" --restore

# 截图直接写入剪贴板
python cli.py capture --screen --clipboard
```

## 项目结构

```
screen-capture/
├── SKILL.md               # 标准 skill 定义（skills.sh 生态）
├── README.md              # 本文档
├── .gitignore
├── requirements.txt
├── cli.py                 # CLI 入口（argparse 命令解析）
├── win_utils.py           # Windows 窗口管理（枚举、匹配、置顶、DPI）
└── capture.py             # 截图逻辑（全屏/窗口/区域/剪贴板）
```

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-07-23 | 初始创建：全屏/窗口/区域截图、窗口枚举与置顶、多显示器、剪贴板输出 |
