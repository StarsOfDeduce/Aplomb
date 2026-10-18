"""诊断：启动/打开设置的过程中，UI 线程有没有被阻塞。"""

from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import win32api as W

user32 = W.user32
WM_NULL = 0x0000
SMTO_ABORTIFHUNG = 0x0002


def responsive(hwnd: int, timeout_ms: int = 300) -> tuple[bool, float]:
    """用 SendMessageTimeout 探测窗口是否还在处理消息。"""
    result = ctypes.c_size_t(0)
    start = time.perf_counter()
    ok = user32.SendMessageTimeoutW(
        hwnd, WM_NULL, 0, 0, SMTO_ABORTIFHUNG, timeout_ms, ctypes.byref(result)
    )
    return bool(ok), (time.perf_counter() - start) * 1000


def find(prefix: str) -> int:
    hit = []

    def callback(hwnd, _):
        if W.get_window_text(hwnd).startswith(prefix):
            hit.append(hwnd)
            return False
        return True

    user32.EnumWindows(W.WNDENUMPROC(callback), 0)
    return hit[0] if hit else 0


def main() -> int:
    exe = str(BASE / "dist" / "Aplomb.exe")
    t0 = time.perf_counter()
    proc = subprocess.Popen([exe])

    host = 0
    while time.perf_counter() - t0 < 25:
        host = find("Aplomb::SingleInstance")
        if host:
            break
        time.sleep(0.05)
    print(f"宿主窗口出现: {(time.perf_counter() - t0) * 1000:.0f} ms")

    time.sleep(1.0)
    ok, cost = responsive(host)
    print(f"托盘状态响应: {'是' if ok else '否'} ({cost:.0f} ms)")

    # 让已有实例弹出设置（模拟第二次启动）
    t1 = time.perf_counter()
    user32.PostMessageW(host, 0x8000 + 17, 0, 0)

    settings = 0
    while time.perf_counter() - t1 < 15:
        settings = W.user32.FindWindowW(None, "Aplomb")
        if settings:
            break
        time.sleep(0.02)
    print(f"设置窗口出现: {(time.perf_counter() - t1) * 1000:.0f} ms")

    for i in range(6):
        ok, cost = responsive(settings if settings else host)
        print(f"  第 {i + 1} 次探测: {'响应' if ok else '无响应'} ({cost:.0f} ms)")
        time.sleep(0.35)

    proc.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
