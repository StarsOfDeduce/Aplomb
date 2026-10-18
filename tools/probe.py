"""开发用：看看当前有没有 Aplomb 在跑，占多少内存、开了哪些窗口。"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import win32api as W


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def memory_mb(pid: int) -> float:
    psapi = ctypes.WinDLL("psapi")
    handle = W.kernel32.OpenProcess(0x0410, False, pid)  # QUERY_INFORMATION|VM_READ
    if not handle:
        return -1
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    W.kernel32.CloseHandle(handle)
    return counters.WorkingSetSize / (1024 * 1024) if ok else -1


def windows_of(pid: int) -> list[tuple[str, int, int]]:
    found = []

    def callback(hwnd, _):
        owner = wintypes.DWORD(0)
        W.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and W.user32.IsWindowVisible(hwnd):
            rect = W.get_window_rect(hwnd)
            if rect and rect.width > 80 and rect.height > 80:
                found.append((W.get_window_text(hwnd) or "(无标题)", rect.width, rect.height))
        return True

    W.user32.EnumWindows(W.WNDENUMPROC(callback), 0)
    return found


def find_aplomb_pids() -> list[int]:
    """按窗口标题找 Aplomb 的实例窗口，反查 pid。"""
    pids = set()

    def callback(hwnd, _):
        title = W.get_window_text(hwnd)
        if title.startswith("Aplomb"):
            owner = wintypes.DWORD(0)
            W.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
            pids.add(owner.value)
        return True

    W.user32.EnumWindows(W.WNDENUMPROC(callback), 0)
    return list(pids)


if __name__ == "__main__":
    pids = find_aplomb_pids()
    if not pids:
        print("没有发现运行中的 Aplomb")
        sys.exit(1)
    for pid in pids:
        print(f"pid={pid}  内存 {memory_mb(pid):.1f} MB")
        for title, w, h in windows_of(pid):
            print(f"    窗口 {w}x{h}  {title}")
