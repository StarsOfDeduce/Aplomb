<p align="center">
  <img src="assets/aplomb.png" width="96" alt="Aplomb 图标">
</p>

<h1 align="center">Aplomb · 从容</h1>

<p align="center">
  <b>为 Windows 而生的精准窗口居中工具</b><br>
  <sub>三个可配置的全局快捷键 · 像素级对齐 · 缩略图选择器 · 居中记忆 · 系统托盘常驻</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.1.1-blue?style=flat-square" alt="版本 1.1.1">
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows" alt="Windows">
  <img src="https://img.shields.io/badge/framework-PySide6-41CD52?style=flat-square&logo=qt" alt="PySide6">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT 许可证">
</p>

<p align="center"><b>简体中文</b> · <a href="README.en.md">English</a></p>

## 简介

**Aplomb**（从容）一词兼有"沉着"与"铅垂"之意，这个程序也是同样的态度：安静待命，把窗口放到它该在的位置。

Aplomb 常驻系统托盘，通过三个可选的全局快捷键居中窗口。它还带一个缩略图选择器用于批量整理窗口、一份让常用程序始终保持居中的"居中记忆"名单、一份忽略名单，以及浅色/深色主题。空闲时不轮询窗口列表，安装包按用户安装、不需要管理员权限。

![Aplomb 深色模式设置界面](screenshots/general-dark.png)

## 为什么再造一个窗口居中工具？

在 Windows 上，`GetWindowRect` 返回的矩形包含桌面窗口管理器（DWM）绘制的不可见阴影。直接把这个矩形摆到正中，可见窗口会偏上偏左几个像素。

Aplomb 读取 `DWMWA_EXTENDED_FRAME_BOUNDS` 拿到真实可见边框，按可见边框对齐，再补偿阴影偏移。结果是可重复、像素级精确的居中。你可以在设置里关掉这个修正做对比。

## 功能特性

- **三个专注的动作**：居中当前窗口、选择窗口居中、全部窗口居中。
- **居中记忆**：居中过的程序会被记住，它们的新窗口在约 0.1 秒内自动回到屏幕正中；如果程序随后又挪动了自己的窗口，Aplomb 会立刻拉回——而你手动拖动的那一刻它就会放手。事件驱动（`SetWinEventHook`），空闲零轮询。开关和名单都在设置的「程序名单」页。
- **默认不占用快捷键**：不录制就不注册任何全局组合键，每项也可以随时清空。
- **缩略图选择器**：按标题或进程名过滤，键盘导航，`Ctrl` + 点击多选。
- **多显示器感知**：每个窗口都居中到它当前所在的屏幕。
- **自动排除**：跳过全屏、最大化、外壳、已忽略和失去响应的窗口。
- **程序名单**：忽略名单与居中记忆名单双列表管理，可从当前打开的窗口中挑选，也可手动选择 exe；设置窗口开着时，名单实时更新。
- **系统 / 浅色 / 深色主题**：克制的界面语言——扁平配色、细边框、圆角。
- **低空闲开销**：热键驱动，空闲时不做任何窗口轮询。

## 选择器的用法

- 直接打字即可按窗口标题或进程名过滤。
- 方向键移动，`Enter` 居中，`Esc` 取消并把焦点还给原窗口。
- 按住 `Ctrl` 点击可多选，一次居中多个窗口。

![Aplomb 窗口选择器](screenshots/picker-dark.png)

## 安装

### 安装包

从 [Releases](../../releases) 下载 `Aplomb-Setup-1.1.1.exe`。

- 安装到 `%LOCALAPPDATA%\Programs\Aplomb`，全程无 UAC 弹窗。
- 可创建桌面快捷方式、开机自启。
- 自动添加开始菜单与 Windows 卸载项。
- 卸载时保留 `%APPDATA%\Aplomb` 中的设置。

### 便携版

下载 `Aplomb-1.1.1-portable.zip`，解压后直接运行 `Aplomb.exe`。

便携版的设置保存在旁边的 `data\` 目录。删掉 `portable.txt` 即可改回把设置存到 `%APPDATA%\Aplomb`。

### 从源码运行

要求：Windows 10 或 11，Python 3.10 及以上。

```powershell
git clone https://github.com/StarsOfDeduce/Aplomb.git
cd Aplomb
python -m pip install -r requirements.txt
python main.py
```

## 配置

- 安装版：`%APPDATA%\Aplomb\config.json`
- 便携版：`<程序目录>\data\config.json`

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

## 构建

```powershell
python -m pip install -r requirements-dev.txt
python build.py            # exe + 便携包 + 安装包
python build.py exe        # 仅 exe
python build.py portable   # 仅便携包
python build.py setup      # 仅安装包
```

构建产物输出到 `dist/`。

`requirements.txt` 与 `requirements-dev.txt` 是带哈希锁定的完整依赖清单。升级依赖时，修改对应的 `.in` 文件后重新生成：

```powershell
python -m pip install pip-tools
pip-compile --allow-unsafe --generate-hashes --strip-extras -o requirements.txt requirements.in
pip-compile --allow-unsafe --generate-hashes --strip-extras -o requirements-dev.txt requirements-dev.in
```

安装包使用 [NSIS](https://nsis.sourceforge.io/) 构建。把 NSIS 解压到 `.tools/nsis/`，或通过环境变量指向已有安装：

```powershell
$env:NSIS_MAKENSIS = "C:/Program Files (x86)/NSIS/makensis.exe"
python build.py setup
```

## 截图

| 快捷键设置 | 浅色主题 |
| :--- | :--- |
| ![快捷键设置](screenshots/hotkeys-dark.png) | ![浅色主题](screenshots/general-light.png) |

| 程序名单 | 从打开的窗口中选择 |
| :--- | :--- |
| ![程序名单](screenshots/lists-dark.png) | ![窗口选择](screenshots/chooser-dark.png) |

## 项目结构

```text
Aplomb/
├── app/
│   ├── win32api.py           # ctypes 声明与安全的 Win32 封装
│   ├── windows.py            # 窗口盘点、过滤与居中算法
│   ├── remember.py           # 事件驱动的居中记忆
│   ├── hotkeys.py            # RegisterHotKey 与原生事件过滤
│   ├── thumbnails.py         # PrintWindow 缩略图捕获
│   ├── icons.py              # 应用图标加载与缓存
│   ├── config.py             # 原子化 JSON 配置与便携模式
│   ├── autostart.py          # 每用户 HKCU Run 自启
│   └── ui/                   # 设置、选择器、托盘、主题与控件
├── installer/                # NSIS 脚本与生成的安装图
├── assets/                   # 运行时图标与图片
├── design/                   # 图标源文件
├── screenshots/
├── tools/                    # 测试、冒烟检查与构建辅助
├── main.py
├── build.py
├── requirements.in
├── requirements.txt
├── requirements-dev.in
└── requirements-dev.txt
```

## 开发自检

```powershell
python tools/selftest.py    # 居中精度、热键、自身窗口处理
python tools/ui_smoke.py    # 设置与选择器交互检查
python tools/e2e.py         # 真实进程的热键到居中全流程（含截图）
python tools/hang_probe.py  # 启动耗时与 UI 线程响应
```

## 实现说明

- 每次操作都重新读取窗口几何；复用旧矩形会让连续居中产生漂移。
- 最小化窗口绝不用 `GetWindowRect` 测量——它返回 (-32000, -32000) 的屏外"停车位"和残影尺寸。真实还原矩形来自 `GetWindowPlacement`，还原位置也用 `SetWindowPlacement` 写回，目标程序不可能因 Aplomb 的移动而存下损坏的几何信息。
- 还原窗口会先等待完成；目标进程忙不过来时，只设置还原落点，绝不在过渡状态移动窗口。
- 纯移动带 `SWP_NOSIZE`，目标应用不会收到多余的 `WM_SIZE`。
- 阴影补偿设有合理上限；当 `GetWindowRect` 与 DWM 边框严重不一致时（例如 DPI 虚拟化），退回普通矩形居中，宁可不够准也不乱飞。
- 进程在创建任何窗口之前自行申报 per-monitor-v2 DPI 感知——坐标是物理像素是"合同规定"，而不是 Qt 的隐式行为。
- 居中记忆监听 `EVENT_OBJECT_SHOW`，约 80ms 后完成居中，随后短暂跟踪 `EVENT_OBJECT_LOCATIONCHANGE`：程序自己挪动了窗口就立刻拉回（几十毫秒内）。`EVENT_SYSTEM_MOVESIZESTART` 一出现立即停止跟踪，用户的拖动永远优先。每个窗口最多纠正数次、只跟踪几秒。
- 设置页面把布局尺寸提示钉在固定窗口可视区之下。只要任一页面的首选高度超过可视区，Qt 就会在几何校验（如拖动窗口）时放大这个"固定尺寸"的半透明窗口——1.1.0 早期构建中被部分用户遇到的"拖动拉伸后卡死"即源于此。
- 窗口标题在确认 `IsHungAppWindow` 之后用 `SendMessageTimeout` 读取，失去响应的程序无法卡死选择器。
- Qt 原生 `WM_HOTKEY` 的重复投递按消息标识与时间戳去重。
- 选择器缩略图及时释放 GDI 资源，浮层关闭时显式清空延迟删除队列。

在 1080p 桌面、7 个已打开窗口下实测：

| 状态 | 内存占用 |
| :--- | :--- |
| PySide6 托盘基线 | 46.8 MB |
| Aplomb 托盘空闲 | 50.9 MB |
| 设置窗口打开 | 约 70 MB |
| 选择器带缩略图打开 | 约 80 MB |
| 14 次选择器开关循环后 | 76.7 MB，稳定 |

## 已知限制

- 仅支持 Windows 10 与 11。
- 独占全屏的窗口不会被移动。
- 居中记忆只在窗口出现后的几秒内跟踪；之后持续自行挪动窗口的程序会被放任，若不希望如此可加入忽略名单。
- 部分 Electron 或硬件加速窗口无法用 `PrintWindow` 捕获，选择器会显示应用图标替代。
- 安装版与便携版不要同时运行。单实例锁会把第二次启动重定向到已有进程。
- 托盘图标深蓝的一半在深色任务栏上 16px 时对比度有限。

## 许可证

[MIT](LICENSE)
