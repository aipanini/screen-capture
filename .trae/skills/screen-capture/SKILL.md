---
name: "screen-capture"
description: "Captures screenshots of the full screen, specific windows, or screen regions, and can bring windows to the foreground. Invoke when user asks to take a screenshot, capture a window, check what's on screen, show desktop state, or bring a window to front."
---

# screen-capture（屏幕捕获工具）

供 AI Agent 通过命令行调用的屏幕捕获工具，支持全屏截图、指定窗口截图、区域截图、窗口置顶。

## 依赖

运行前确保已安装依赖：

```powershell
pip install Pillow pywin32
```

## CLI 路径

```
toolkit/screen-capture/cli.py
```

完整路径（按实际项目位置替换）：

```powershell
python <项目根目录>/toolkit/screen-capture/cli.py <命令> [参数]
```

## 可用命令

### 1. list — 列出窗口

查看当前系统有哪些可见窗口（标题、进程名、PID、位置尺寸）。

```powershell
python cli.py list                           # 表格格式（默认）
python cli.py list --format json             # JSON 格式（便于程序解析）
python cli.py list --no-visible-filter       # 显示所有窗口（含隐藏）
```

**JSON 输出示例：**

```json
[
  {
    "hwnd": 67696,
    "title": "TRAE Work CN",
    "class_name": "Chrome_WidgetWin_1",
    "pid": 26556,
    "process_name": "TRAE SOLO CN.exe",
    "is_visible": true,
    "rect": [0, 0, 2562, 1530]
  }
]
```

### 2. capture — 截图

#### 全屏截图

```powershell
python cli.py capture --screen --output "C:\temp\screenshot.png"
python cli.py capture --screen --clipboard              # 写入剪贴板
python cli.py capture --screen --monitor 1 --output ...  # 第二个显示器
```

#### 指定窗口截图

按标题关键字模糊匹配窗口（不区分大小写）。使用 PrintWindow API，可截取包括管理员窗口在内的所有窗口。

```powershell
python cli.py capture --window "Chrome" --output "C:\temp\chrome.png"
python cli.py capture --window "Visual Studio Code" --clipboard
```

如果多个窗口匹配同一关键字，会报错并列出所有匹配项，需要使用更精确的关键字。

#### 区域截图

截取屏幕指定矩形区域（X, Y 为左上角坐标，W, H 为宽高，使用虚拟屏幕坐标）。

```powershell
python cli.py capture --region 0 0 800 600 --output "C:\temp\region.png"
```

#### 通用参数

| 参数 | 说明 |
|------|------|
| `--output PATH` | 输出文件路径（PNG 格式），不指定时自动生成带时间戳的文件名 |
| `--clipboard` | 截图写入系统剪贴板而非保存文件 |
| `--delay MS` | 截图前等待毫秒数（等待窗口动画/渲染完成） |
| `--monitor N` | 全屏模式下的显示器索引（0=主显示器，1=副显示器...） |

### 3. focus — 窗口置顶

将指定窗口置顶到最前端。

```powershell
python cli.py focus "Visual Studio Code"         # 置顶
python cli.py focus "Visual Studio Code" --restore # 最小化则先恢复
```

## 使用流程建议

1. **先 list** 了解当前窗口状态，获取精确的窗口标题
2. **按需 focus** 将目标窗口置顶（如果窗口被遮挡或最小化）
3. **再 capture** 截取需要的画面
4. 通过 `--delay` 参数应对需要等待渲染的场景（如页面加载、动画过渡）

## 已知限制

- 多显示器环境下 `--monitor` 索引基于系统枚举顺序，不保证与物理位置对应
- `PrintWindow` 对 DirectX/OpenGL 全屏独占应用可能无法正常捕获（如全屏游戏）
- 截图文件保存在运行目录下（可通过 `--output` 指定绝对路径）

## 错误处理

- 窗口未找到：提示 `未找到标题包含 'xxx' 的窗口`
- 多个窗口匹配：列出所有匹配窗口，提示指定更精确的关键字
- 窗口最小化截图：建议先 `focus --restore` 再截图
