"""Win32 绑定层。

这里只做三件事：声明结构体、声明函数原型、提供少量安全的包装。
所有函数都显式声明 argtypes/restype —— 64 位下不声明会截断指针，
导致偶发的崩溃或内存踩踏。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes as w

# --------------------------------------------------------------------------- #
# DLL
# --------------------------------------------------------------------------- #
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t


# --------------------------------------------------------------------------- #
# 结构体
# --------------------------------------------------------------------------- #
class RECT(ctypes.Structure):
    _fields_ = [
        ("left", w.LONG),
        ("top", w.LONG),
        ("right", w.LONG),
        ("bottom", w.LONG),
    ]

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


class POINT(ctypes.Structure):
    _fields_ = [("x", w.LONG), ("y", w.LONG)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", w.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", w.DWORD),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", w.DWORD),
        ("biWidth", w.LONG),
        ("biHeight", w.LONG),
        ("biPlanes", w.WORD),
        ("biBitCount", w.WORD),
        ("biCompression", w.DWORD),
        ("biSizeImage", w.DWORD),
        ("biXPelsPerMeter", w.LONG),
        ("biYPelsPerMeter", w.LONG),
        ("biClrUsed", w.DWORD),
        ("biClrImportant", w.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", w.DWORD * 3)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", w.HWND),
        ("message", w.UINT),
        ("wParam", w.WPARAM),
        ("lParam", w.LPARAM),
        ("time", w.DWORD),
        ("pt", POINT),
    ]


# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_POPUP = 0x80000000
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_NOACTIVATE = 0x08000000

SW_RESTORE = 9
SW_SHOWNOACTIVATE = 4

HWND_TOP = 0
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

GW_HWNDNEXT = 2
GA_ROOT = 2

MONITOR_DEFAULTTONEAREST = 2

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14

PW_RENDERFULLCONTENT = 0x00000002

WM_HOTKEY = 0x0312
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E

SMTO_BLOCK = 0x0001
SMTO_ABORTIFHUNG = 0x0002
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

BI_RGB = 0
DIB_RGB_COLORS = 0

WNDENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)


# --------------------------------------------------------------------------- #
# 函数原型
# --------------------------------------------------------------------------- #
def _proto(fn, args, ret):
    fn.argtypes = args
    fn.restype = ret
    return fn


# 窗口遍历与属性
_proto(user32.EnumWindows, [WNDENUMPROC, w.LPARAM], w.BOOL)
_proto(user32.IsWindow, [w.HWND], w.BOOL)
_proto(user32.IsWindowVisible, [w.HWND], w.BOOL)
_proto(user32.IsIconic, [w.HWND], w.BOOL)
_proto(user32.IsZoomed, [w.HWND], w.BOOL)
_proto(user32.IsHungAppWindow, [w.HWND], w.BOOL)
_proto(user32.GetWindowRect, [w.HWND, ctypes.POINTER(RECT)], w.BOOL)
_proto(user32.GetWindowTextLengthW, [w.HWND], ctypes.c_int)
_proto(user32.GetWindowTextW, [w.HWND, w.LPWSTR, ctypes.c_int], ctypes.c_int)
_proto(user32.GetClassNameW, [w.HWND, w.LPWSTR, ctypes.c_int], ctypes.c_int)
_proto(user32.GetWindowThreadProcessId, [w.HWND, ctypes.POINTER(w.DWORD)], w.DWORD)
_proto(user32.GetForegroundWindow, [], w.HWND)
_proto(user32.FindWindowW, [w.LPCWSTR, w.LPCWSTR], w.HWND)
_proto(user32.PostMessageW, [w.HWND, w.UINT, w.WPARAM, w.LPARAM], w.BOOL)
_proto(user32.SetForegroundWindow, [w.HWND], w.BOOL)
_proto(user32.BringWindowToTop, [w.HWND], w.BOOL)
_proto(user32.SetFocus, [w.HWND], w.HWND)
_proto(user32.AttachThreadInput, [w.DWORD, w.DWORD, w.BOOL], w.BOOL)
_proto(kernel32.GetCurrentThreadId, [], w.DWORD)
_proto(user32.GetWindow, [w.HWND, w.UINT], w.HWND)
_proto(user32.GetAncestor, [w.HWND, w.UINT], w.HWND)
_proto(user32.SetWindowPos, [w.HWND, w.HWND, ctypes.c_int, ctypes.c_int,
                             ctypes.c_int, ctypes.c_int, w.UINT], w.BOOL)
_proto(user32.ShowWindowAsync, [w.HWND, ctypes.c_int], w.BOOL)
_proto(user32.GetCursorPos, [ctypes.POINTER(POINT)], w.BOOL)
_proto(user32.RegisterHotKey, [w.HWND, ctypes.c_int, w.UINT, w.UINT], w.BOOL)
_proto(user32.UnregisterHotKey, [w.HWND, ctypes.c_int], w.BOOL)
_proto(user32.PrintWindow, [w.HWND, w.HDC, w.UINT], w.BOOL)
_proto(user32.SendMessageTimeoutW,
       [w.HWND, w.UINT, w.WPARAM, w.LPARAM, w.UINT, w.UINT,
        ctypes.POINTER(ctypes.c_size_t)], ctypes.c_size_t)

# 显示器
_proto(user32.MonitorFromWindow, [w.HWND, w.DWORD], w.HANDLE)
_proto(user32.GetMonitorInfoW, [w.HANDLE, ctypes.POINTER(MONITORINFO)], w.BOOL)
_proto(user32.MonitorFromPoint, [POINT, w.DWORD], w.HANDLE)

# DWM
_proto(dwmapi.DwmGetWindowAttribute,
       [w.HWND, w.DWORD, ctypes.c_void_p, w.DWORD], ctypes.c_long)

# GDI
_proto(gdi32.CreateCompatibleDC, [w.HDC], w.HDC)
_proto(gdi32.CreateCompatibleBitmap, [w.HDC, ctypes.c_int, ctypes.c_int], w.HBITMAP)
_proto(gdi32.SelectObject, [w.HDC, w.HGDIOBJ], w.HGDIOBJ)
_proto(gdi32.DeleteObject, [w.HGDIOBJ], w.BOOL)
_proto(gdi32.DeleteDC, [w.HDC], w.BOOL)
_proto(gdi32.GetDIBits, [w.HDC, w.HBITMAP, w.UINT, w.UINT, ctypes.c_void_p,
                         ctypes.POINTER(BITMAPINFO), w.UINT], ctypes.c_int)
_proto(user32.GetDC, [w.HWND], w.HDC)
_proto(user32.ReleaseDC, [w.HWND, w.HDC], ctypes.c_int)
_proto(gdi32.SetStretchBltMode, [w.HDC, ctypes.c_int], ctypes.c_int)
_proto(gdi32.StretchBlt, [w.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                          ctypes.c_int, w.HDC, ctypes.c_int, ctypes.c_int,
                          ctypes.c_int, ctypes.c_int, w.DWORD], w.BOOL)

# 进程
_proto(kernel32.OpenProcess, [w.DWORD, w.BOOL, w.DWORD], w.HANDLE)
_proto(kernel32.CloseHandle, [w.HANDLE], w.BOOL)
_proto(kernel32.QueryFullProcessImageNameW,
       [w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)], w.BOOL)

# 64 位下取窗口样式必须用 GetWindowLongPtrW
_get_window_long = getattr(user32, "GetWindowLongPtrW", None) or user32.GetWindowLongW
_proto(_get_window_long, [w.HWND, ctypes.c_int], ctypes.c_ssize_t)
GetWindowLongPtrW = _get_window_long


# --------------------------------------------------------------------------- #
# 安全包装
# --------------------------------------------------------------------------- #
def get_window_text(hwnd: int, timeout_ms: int = 50) -> str:
    """取窗口标题，带超时。

    绝不能用 GetWindowTextW —— 它对别的进程发 WM_GETTEXT 是同步等待，
    目标程序一旦卡住，我们的 UI 线程会跟着一起卡死（真机上遇到过）。
    这里改成 SendMessageTimeout，超时就直接放弃这个窗口。
    """
    result = ctypes.c_size_t(0)
    flags = SMTO_ABORTIFHUNG | SMTO_BLOCK

    ok = user32.SendMessageTimeoutW(
        hwnd, WM_GETTEXTLENGTH, 0, 0, flags, timeout_ms, ctypes.byref(result)
    )
    if not ok or result.value <= 0:
        return ""

    length = min(int(result.value), 1024)
    buf = ctypes.create_unicode_buffer(length + 1)
    ok = user32.SendMessageTimeoutW(
        hwnd, WM_GETTEXT, length + 1,
        ctypes.cast(buf, ctypes.c_void_p).value,
        flags, timeout_ms, ctypes.byref(result),
    )
    if not ok:
        return ""
    return buf.value


def get_class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_process_path(pid: int) -> str:
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = w.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def get_window_rect(hwnd: int) -> RECT | None:
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect


def get_visible_frame(hwnd: int) -> RECT | None:
    """DWM 报告的可见边框 —— 不含窗口阴影。"""
    rect = RECT()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    if hr != 0 or rect.width <= 0 or rect.height <= 0:
        return None
    return rect


def is_cloaked(hwnd: int) -> bool:
    value = w.DWORD(0)
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_CLOAKED, ctypes.byref(value), ctypes.sizeof(value)
    )
    return hr == 0 and value.value != 0


def get_monitor_info(hwnd: int) -> MONITORINFO | None:
    monitor = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not monitor:
        return None
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return info


def set_window_pos(hwnd: int, x: int, y: int, cx: int, cy: int,
                   flags: int = SWP_NOZORDER | SWP_NOACTIVATE) -> bool:
    return bool(user32.SetWindowPos(hwnd, 0, x, y, cx, cy, flags))


def force_foreground(hwnd: int) -> None:
    """把窗口抢到前台。

    全局热键唤起窗口时，我们的进程并不是前台进程，Windows 的前台锁会
    直接拒绝 SetForegroundWindow —— 结果就是浮层弹出来了却收不到键盘。
    把当前线程的输入队列临时挂到前台线程上，就能绕过这个限制。
    """
    if not hwnd:
        return
    foreground = user32.GetForegroundWindow()
    if foreground == hwnd:
        return
    # 前台窗口本身卡死时别去挂它的输入队列，否则可能一起僵住
    if foreground and user32.IsHungAppWindow(foreground):
        user32.BringWindowToTop(hwnd)
        return

    own_thread = kernel32.GetCurrentThreadId()
    fg_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0

    attached = False
    if fg_thread and fg_thread != own_thread:
        attached = bool(user32.AttachThreadInput(own_thread, fg_thread, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetFocus(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(own_thread, fg_thread, False)
