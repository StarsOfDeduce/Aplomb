"""窗口盘点与居中算法。

居中的关键不是把 GetWindowRect 摆中间 —— 那个矩形包含 DWM 画的不可见阴影，
照它居中在视觉上会偏。这里用 DWMWA_EXTENDED_FRAME_BOUNDS 拿到真实可见边框，
再把它对齐到工作区正中，最后把阴影偏移补回去。
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass

from . import win32api as W

# 这些是外壳窗口，不属于"应用窗口"
SHELL_CLASSES = frozenset({
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "MultitaskingViewFrame",
    "ForegroundStaging",
    "Windows.UI.Core.CoreWindow",
    "ApplicationManager_DesktopShellWindow",
    "XamlExplorerHostIslandWindow",
    "Windows.Internal.Shell.TabProxyWindow",
    "TaskListThumbnailWnd",
    "EdgeUiInputTopWndClass",
    "NarratorHelperWindow",
})

# 系统级不可移动的窗口
IMMOVABLE_CLASSES = frozenset({
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "Progman",
    "WorkerW",
})


@dataclass(slots=True)
class WindowInfo:
    hwnd: int
    title: str
    class_name: str
    pid: int
    exe_path: str
    exe_name: str
    rect: W.RECT
    monitor_rect: W.RECT
    work_rect: W.RECT
    minimized: bool
    maximized: bool
    fullscreen: bool

    @property
    def key(self) -> str:
        return f"{self.pid}:{self.title}"


def _own_pid() -> int:
    return ctypes.windll.kernel32.GetCurrentProcessId()


def _own_exe() -> str:
    """打包后指向 Aplomb.exe 本身，开发时为空（不能把所有 python.exe 都排掉）。"""
    return sys.executable.lower() if getattr(sys, "frozen", False) else ""


def _exe_name(path: str) -> str:
    return path.rsplit("\\", 1)[-1] if path else ""


def _is_fullscreen(frame: W.RECT, monitor: W.RECT, style: int) -> bool:
    if not (style & W.WS_POPUP):
        return False
    return (
        abs(frame.left - monitor.left) <= 2
        and abs(frame.top - monitor.top) <= 2
        and abs(frame.right - monitor.right) <= 2
        and abs(frame.bottom - monitor.bottom) <= 2
    )


def inspect(hwnd: int, allow_own: bool = False) -> WindowInfo | None:
    """把 hwnd 变成 WindowInfo，不合格就返回 None。

    allow_own=True 时不排除本程序自己的窗口 —— 用于「用户明确要居中当前窗口」
    这一种情况（焦点就在我们自己的设置界面上）。
    """
    if not hwnd or not W.user32.IsWindow(hwnd):
        return None

    style = W.GetWindowLongPtrW(hwnd, W.GWL_STYLE)
    if not (style & W.WS_VISIBLE):
        return None
    if W.is_cloaked(hwnd):
        return None

    class_name = W.get_class_name(hwnd)
    if class_name in SHELL_CLASSES:
        return None

    ex_style = W.GetWindowLongPtrW(hwnd, W.GWL_EXSTYLE)
    if ex_style & W.WS_EX_TOOLWINDOW and not (ex_style & W.WS_EX_APPWINDOW):
        return None

    # 先判断是否卡死，再去读标题 —— 顺序不能反，读标题会跟目标进程通信
    if W.user32.IsHungAppWindow(hwnd):
        return None

    title = W.get_window_text(hwnd)
    if not title:
        return None

    pid = wintypes.DWORD(0)
    W.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == _own_pid() and not allow_own:
        return None

    rect = W.get_window_rect(hwnd)
    if rect is None or rect.width <= 0 or rect.height <= 0:
        return None

    monitor = W.get_monitor_info(hwnd)
    if monitor is None:
        return None

    frame = W.get_visible_frame(hwnd) or rect
    path = W.get_process_path(pid.value)

    # 本进程，或者另一个 Aplomb 实例 —— 批量操作和列表里都不该出现
    own_exe = _own_exe()
    if not allow_own and own_exe and path and path.lower() == own_exe:
        return None

    return WindowInfo(
        hwnd=hwnd,
        title=title,
        class_name=class_name,
        pid=pid.value,
        exe_path=path,
        exe_name=_exe_name(path),
        rect=rect,
        monitor_rect=monitor.rcMonitor,
        work_rect=monitor.rcWork,
        minimized=bool(W.user32.IsIconic(hwnd)),
        maximized=bool(W.user32.IsZoomed(hwnd)),
        fullscreen=_is_fullscreen(frame, monitor.rcMonitor, style),
    )


def _ignored(info: WindowInfo, ignore_list: list[str]) -> bool:
    if not ignore_list:
        return False
    name = info.exe_name.lower()
    path = info.exe_path.lower()
    for entry in ignore_list:
        e = entry.strip().lower()
        if not e:
            continue
        if e == name or e == path or (name and e in name):
            return True
    return False


def list_windows(ignore_list: list[str] | None = None,
                 include_minimized: bool = True,
                 allow_own: bool = False) -> list[WindowInfo]:
    """按 Z 序（从上到下）枚举可操作的应用窗口。

    allow_own=True 时把 Aplomb 自己的窗口也算进来（设置界面）；
    自己的临时浮层（选择器）因为带 WS_EX_TOOLWINDOW，仍会被过滤掉。
    """
    results: list[WindowInfo] = []
    ignore = ignore_list or []

    def _callback(hwnd, _lparam):
        info = inspect(hwnd, allow_own=allow_own)
        if info is None:
            return True
        if _ignored(info, ignore):
            return True
        if not include_minimized and info.minimized:
            return True
        results.append(info)
        return True

    W.user32.EnumWindows(W.WNDENUMPROC(_callback), 0)
    return results


# --------------------------------------------------------------------------- #
# 居中
# --------------------------------------------------------------------------- #
def _target_rect(info: WindowInfo, pixel_perfect: bool) -> tuple[int, int, int, int]:
    """算目标位置。几何一律现取，不用缓存值 —— 否则连续按两次会算错阴影偏移。"""
    work = info.work_rect
    rect = W.get_window_rect(info.hwnd) or info.rect

    if pixel_perfect:
        frame = W.get_visible_frame(info.hwnd) or rect
        shadow_l = frame.left - rect.left
        shadow_t = frame.top - rect.top
        frame_x = work.left + (work.width - frame.width) // 2
        frame_y = work.top + (work.height - frame.height) // 2
        x = frame_x - shadow_l
        y = frame_y - shadow_t
    else:
        x = work.left + (work.width - rect.width) // 2
        y = work.top + (work.height - rect.height) // 2

    return x, y, rect.width, rect.height


def _restore(hwnd: int) -> None:
    """还原最小化/最大化窗口，并等它真的完成（异步调用，最多等 ~60ms）。"""
    W.user32.ShowWindowAsync(hwnd, W.SW_RESTORE)
    for _ in range(4):
        if not W.user32.IsIconic(hwnd) and not W.user32.IsZoomed(hwnd):
            return
        time.sleep(0.015)


def center(info: WindowInfo, pixel_perfect: bool = True,
           restore: bool = True) -> tuple[bool, str]:
    """把单个窗口居中，返回 (是否成功, 原因)。"""
    if info.class_name in IMMOVABLE_CLASSES:
        return False, "系统窗口不参与居中"
    if info.fullscreen:
        return False, "全屏窗口已跳过"

    hwnd = info.hwnd
    if (info.minimized or info.maximized) and restore:
        _restore(hwnd)
        refreshed = W.get_window_rect(hwnd)
        if refreshed:
            info.rect = refreshed

    x, y, cx, cy = _target_rect(info, pixel_perfect)
    if not W.set_window_pos(hwnd, x, y, cx, cy):
        return False, "系统拒绝了这次移动"
    return True, ""


def belongs_to_us(hwnd: int) -> bool:
    """这个窗口是不是本程序自己的。"""
    if not hwnd:
        return False
    pid = wintypes.DWORD(0)
    W.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == _own_pid()


def center_foreground(pixel_perfect: bool = True) -> tuple[bool, str]:
    """居中前台窗口。

    如果焦点落在 Aplomb 自己身上（比如正在看设置界面），也照样居中它自己 ——
    「把当前这个窗口摆正」是最符合直觉的行为。但批量居中和选择器列表里
    不会包含自己，避免误伤。
    """
    hwnd = W.user32.GetForegroundWindow()
    if not hwnd:
        return False, "没有找到活动窗口"

    info = inspect(hwnd, allow_own=True)
    if info is None:
        # 自己的浮层（选择器等）不参与居中，这种情况静默跳过
        if belongs_to_us(hwnd):
            return False, ""
        return False, "当前窗口不支持居中"
    return center(info, pixel_perfect)


def center_all(pixel_perfect: bool = True,
               ignore_list: list[str] | None = None) -> tuple[int, int]:
    """批量居中。跳过最小化、最大化、全屏窗口 —— 不做惊喜式打扰。

    自己的设置窗口同样会被居中（三种模式行为保持一致）。
    """
    count = 0
    total = 0
    for info in list_windows(ignore_list, include_minimized=False, allow_own=True):
        if info.fullscreen or info.maximized or info.minimized:
            continue
        total += 1
        ok, _ = center(info, pixel_perfect, restore=False)
        if ok:
            count += 1
    return count, total


def activate(hwnd: int) -> None:
    """把窗口带到前台（我们此刻是前台，所以这个调用会被允许）。"""
    W.user32.SetForegroundWindow(hwnd)
