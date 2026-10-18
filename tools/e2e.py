"""端到端：启动真实程序，投递 WM_HOTKEY 触发三个动作，截图并量内存。

注意：这里不用 SendInput 模拟按键 —— 当前桌面有提权的前台进程时，
注入的按键会被 UIPI 丢弃，测不出真实结果。直接投递热键消息更可靠。
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import sysconfig
import time
from ctypes import wintypes
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from app import win32api as W
from tools.probe import memory_mb

OUT = BASE / "preview"
OUT.mkdir(exist_ok=True)
WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010


def visible_windows(pid: int) -> list[tuple[str, int, int]]:
    found = []

    def callback(hwnd, _):
        owner = wintypes.DWORD(0)
        W.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and W.user32.IsWindowVisible(hwnd):
            rect = W.get_window_rect(hwnd)
            if rect and rect.width > 80:
                found.append((W.get_window_text(hwnd) or "(无标题)", rect.width, rect.height))
        return True

    W.user32.EnumWindows(W.WNDENUMPROC(callback), 0)
    return found


def find_by_prefix(prefix: str) -> int:
    hit = []

    def callback(hwnd, _):
        if W.get_window_text(hwnd).startswith(prefix):
            hit.append(hwnd)
            return False
        return True

    W.user32.EnumWindows(W.WNDENUMPROC(callback), 0)
    return hit[0] if hit else 0


def main() -> int:
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])

    env = os.environ.copy()
    env["PYTHONPATH"] = sysconfig.get_paths()["purelib"]
    proc = subprocess.Popen(
        [getattr(sys, "_base_executable", sys.executable), str(BASE / "main.py")],
        env=env,
    )
    print(f"启动 pid={proc.pid}")
    time.sleep(3.5)

    if proc.poll() is not None:
        print("进程提前退出，退出码:", proc.returncode)
        return 1

    host = find_by_prefix("Aplomb::SingleInstance")
    print(f"宿主窗口={host}  可见窗口={visible_windows(proc.pid)}")
    print(f"内存: {memory_mb(proc.pid):.1f} MB")

    def shot(name: str) -> None:
        QGuiApplication.primaryScreen().grabWindow(0).save(str(OUT / name))

    shot("e2e_1_settings.png")

    # 收起设置
    settings = W.user32.FindWindowW(None, "Aplomb")
    if settings:
        W.user32.PostMessageW(settings, WM_CLOSE, 0, 0)
    time.sleep(0.8)
    print(f"收起设置后 内存 {memory_mb(proc.pid):.1f} MB, 可见 {visible_windows(proc.pid)}")

    # 呼出选择器
    W.user32.PostMessageW(host, WM_HOTKEY, 2, 0)
    time.sleep(1.8)
    print(f"选择器: {visible_windows(proc.pid)}  内存 {memory_mb(proc.pid):.1f} MB")
    shot("e2e_2_picker.png")

    # 再按一次关闭
    W.user32.PostMessageW(host, WM_HOTKEY, 2, 0)
    time.sleep(0.6)
    print(f"关闭后: {visible_windows(proc.pid)}")

    # 居中当前 / 全部居中
    W.user32.PostMessageW(host, WM_HOTKEY, 1, 0)
    time.sleep(1.0)
    shot("e2e_3_centered.png")
    W.user32.PostMessageW(host, WM_HOTKEY, 3, 0)
    time.sleep(1.4)
    shot("e2e_4_all.png")

    print(f"结束内存: {memory_mb(proc.pid):.1f} MB")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("已退出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
