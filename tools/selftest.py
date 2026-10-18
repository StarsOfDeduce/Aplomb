"""开发用自检：不依赖托盘，直接验证窗口枚举、居中精度、热键解析。"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QWidget

from app import win32api as W
from app import windows as winlib
from app.hotkeys import HotkeyManager, format_hotkey, parse_hotkey

app = QApplication(sys.argv[:1])

ok = True


def check(name: str, condition: bool, detail: str = "") -> None:
    global ok
    mark = "PASS" if condition else "FAIL"
    if not condition:
        ok = False
    print(f"[{mark}] {name}{(' — ' + detail) if detail else ''}")


# ---------------------------------------------------------------- 热键解析
cases = [
    ("Ctrl+Alt+C", True), ("ctrl+shift+f5", True), ("Alt+Space", True),
    ("Shift+A", False), ("C", False), ("Ctrl+", False), ("Win+`", True),
]
for spec, should in cases:
    parsed = parse_hotkey(spec)
    check(f"解析 {spec}", (parsed is not None) == should)

mods, vk = parse_hotkey("Ctrl+Alt+W")
check("回写格式", format_hotkey(mods, vk) == "Ctrl+Alt+W", format_hotkey(mods, vk))

# ---------------------------------------------------------------- 枚举
windows = winlib.list_windows([], include_minimized=True)
check("枚举到窗口", len(windows) > 0, f"{len(windows)} 个")
for info in windows[:8]:
    print(f"    · {info.title[:40]:<42} {info.exe_name:<22} "
          f"{'最小化' if info.minimized else ('最大化' if info.maximized else '常规')}"
          f"{' 全屏' if info.fullscreen else ''}")

# ---------------------------------------------------------------- 居中
import subprocess
import time

target = subprocess.Popen(
    [sys.executable, str(BASE / "tools" / "_target_window.py")],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)

info = None
deadline = time.time() + 6
while time.time() < deadline:
    app.processEvents()
    for candidate in winlib.list_windows([], include_minimized=True):
        if candidate.title == "Aplomb Test Target":
            info = candidate
            break
    if info is not None:
        break
    time.sleep(0.1)

check("跨进程目标窗口可识别", info is not None)

if info is not None:
    hwnd = info.hwnd
    before = (info.rect.left, info.rect.top)
    success, reason = winlib.center(info, pixel_perfect=True)
    app.processEvents()
    after = W.get_window_rect(hwnd)
    frame = W.get_visible_frame(hwnd)
    work = info.work_rect
    check("居中返回成功", success, reason)

    if frame is not None:
        dx = (frame.left + frame.right) / 2 - (work.left + work.right) / 2
        dy = (frame.top + frame.bottom) / 2 - (work.top + work.bottom) / 2
        check("视觉中心对齐（误差 ≤ 1px）", abs(dx) <= 1 and abs(dy) <= 1,
              f"偏移 dx={dx:.1f} dy={dy:.1f}")
        print(f"    可见边框 {frame.left},{frame.top} {frame.width}x{frame.height} "
              f"| 工作区 {work.left},{work.top} {work.width}x{work.height}")
        print(f"    窗口矩形（含阴影） {after.left},{after.top} {after.width}x{after.height}")
        print(f"    移动前 {before} → 移动后 {(after.left, after.top)}")

    winlib.center(info, pixel_perfect=True)
    app.processEvents()
    again = W.get_window_rect(hwnd)
    check("重复居中不漂移",
          abs(again.left - after.left) <= 1 and abs(again.top - after.top) <= 1,
          f"{(after.left, after.top)} → {(again.left, again.top)}")

    # 关掉阴影修正时应当居中"窗口矩形"而不是"可见边框"
    winlib.center(info, pixel_perfect=False)
    app.processEvents()
    naive = W.get_window_rect(hwnd)
    naive_dx = (naive.left + naive.right) / 2 - (work.left + work.right) / 2
    check("关闭阴影修正后按窗口矩形居中", abs(naive_dx) <= 1,
          f"偏移 dx={naive_dx:.1f}")

# 注意：目标窗口先别关，下面还要验证"不居中自己"之后仍能居中它

# ---------------------------------------------------------------- 不居中自己
from app.ui.settings_window import SettingsWindow
from app.config import Config

settings = SettingsWindow(Config())
settings.show()
app.processEvents()
time.sleep(0.3)
app.processEvents()

own_hwnd = int(settings.winId())
for _ in range(5):
    W.force_foreground(own_hwnd)
    app.processEvents()
    time.sleep(0.12)
    if W.user32.GetForegroundWindow() == own_hwnd:
        break

own_before = W.get_window_rect(own_hwnd)
foreground = W.user32.GetForegroundWindow()
check("焦点已落在自己的设置窗口", foreground == own_hwnd, f"fg={foreground}")

# 先把它挪到一个明显偏心的位置，再验证能否居中自己
W.set_window_pos(own_hwnd, 40, 60, own_before.width, own_before.height)
app.processEvents()
time.sleep(0.15)
app.processEvents()

ok_self, reason_self = winlib.center_foreground(True)
app.processEvents()
own_after = W.get_window_rect(own_hwnd)
own_frame = W.get_visible_frame(own_hwnd) or own_after
own_work = W.get_monitor_info(own_hwnd).rcWork

check("可以居中自己的窗口", ok_self, reason_self)
own_dx = (own_frame.left + own_frame.right) / 2 - (own_work.left + own_work.right) / 2
own_dy = (own_frame.top + own_frame.bottom) / 2 - (own_work.top + own_work.bottom) / 2
check("自己的窗口确实被移到了正中", abs(own_dx) <= 1 and abs(own_dy) <= 1,
      f"偏移 dx={own_dx:.1f} dy={own_dy:.1f}  {(own_after.left, own_after.top)}")
check("默认列表里不包含自己",
      all(w.hwnd != own_hwnd for w in winlib.list_windows([], include_minimized=True)))
check("选择器/批量居中用的列表里包含自己",
      any(w.hwnd == own_hwnd for w in winlib.list_windows([], include_minimized=True, allow_own=True)))

settings.hide()
app.processEvents()

# 焦点回到别的程序时，仍然能正常居中
if info is not None:
    W.user32.SetForegroundWindow(hwnd)
    app.processEvents()
    time.sleep(0.2)
    app.processEvents()
    ok_other, reason_other = winlib.center_foreground(True)
    check("焦点在别的程序上时能居中", ok_other, reason_other)

# ---------------------------------------------------------------- 热键注册
target.terminate()
try:
    target.wait(timeout=3)
except subprocess.TimeoutExpired:
    target.kill()

host = QWidget()
host.setWindowFlags(Qt.Tool)
hwnd = int(host.winId())
manager = HotkeyManager(hwnd)
registered = manager.register("selftest", "Ctrl+Alt+F12")
check("注册全局热键", registered)
manager.unregister_all()
re_registered = manager.register("selftest", "Ctrl+Alt+F12")
check("注销后可再次注册", re_registered)
manager.unregister_all()


def finish() -> None:
    print("\n结果:", "全部通过" if ok else "有失败项")
    app.exit(0 if ok else 1)


QTimer.singleShot(200, finish)
sys.exit(app.exec())
