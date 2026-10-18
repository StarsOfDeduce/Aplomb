"""窗口缩略图截取。

内存策略：先用一张与窗口等大的 GDI 位图接住 PrintWindow 的结果，
再用 StretchBlt 缩到目标尺寸，最后只把缩略图那一小块拷进 Python 堆。
这样即使窗口是 4K，托管内存里也只留一张几十 KB 的图。
GDI 位图在函数返回前一定会被 DeleteObject 释放。
"""

from __future__ import annotations

import ctypes

from PySide6.QtGui import QImage

from . import win32api as W

SRCCOPY = 0x00CC0020
HALFTONE = 4
_MAX_SOURCE = 5120  # 超过这个尺寸的窗口不做预览，避免异常大的位图


def capture(hwnd: int, target_w: int, target_h: int) -> QImage | None:
    if target_w <= 0 or target_h <= 0:
        return None
    # PrintWindow 是跨线程同步调用，卡死的窗口会把它一起拖住
    if W.user32.IsHungAppWindow(hwnd):
        return None
    rect = W.get_window_rect(hwnd)
    if rect is None or rect.width <= 0 or rect.height <= 0:
        return None

    src_w, src_h = rect.width, rect.height
    if src_w > _MAX_SOURCE or src_h > _MAX_SOURCE:
        return None

    hdc_screen = W.user32.GetDC(0)
    if not hdc_screen:
        return None

    hdc_src = None
    hdc_dst = None
    bmp_src = None
    bmp_dst = None
    old_src = None
    old_dst = None
    try:
        hdc_src = W.gdi32.CreateCompatibleDC(hdc_screen)
        hdc_dst = W.gdi32.CreateCompatibleDC(hdc_screen)
        if not hdc_src or not hdc_dst:
            return None

        bmp_src = W.gdi32.CreateCompatibleBitmap(hdc_screen, src_w, src_h)
        bmp_dst = W.gdi32.CreateCompatibleBitmap(hdc_screen, target_w, target_h)
        if not bmp_src or not bmp_dst:
            return None

        old_src = W.gdi32.SelectObject(hdc_src, bmp_src)
        old_dst = W.gdi32.SelectObject(hdc_dst, bmp_dst)

        if not W.user32.PrintWindow(hwnd, hdc_src, W.PW_RENDERFULLCONTENT):
            if not W.user32.PrintWindow(hwnd, hdc_src, 0):
                return None

        W.gdi32.SetStretchBltMode(hdc_dst, HALFTONE)
        if not W.gdi32.StretchBlt(hdc_dst, 0, 0, target_w, target_h,
                                  hdc_src, 0, 0, src_w, src_h, SRCCOPY):
            return None

        info = W.BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(W.BITMAPINFOHEADER)
        info.bmiHeader.biWidth = target_w
        info.bmiHeader.biHeight = -target_h  # 负值 = 自上而下
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = W.BI_RGB

        buffer = ctypes.create_string_buffer(target_w * target_h * 4)
        scanned = W.gdi32.GetDIBits(hdc_dst, bmp_dst, 0, target_h, buffer,
                                    ctypes.byref(info), W.DIB_RGB_COLORS)
        if scanned == 0:
            return None

        # 全黑 / 全同色说明 PrintWindow 没拿到内容（部分应用会这样）
        sample = buffer.raw
        step = max(4, (target_w * target_h // 96) * 4)
        first = sample[0:3]
        if all(sample[i:i + 3] == first for i in range(0, len(sample) - 4, step)):
            return None

        image = QImage(buffer.raw, target_w, target_h, target_w * 4,
                       QImage.Format_RGB32)
        return image.copy()
    except Exception:
        return None
    finally:
        if old_src:
            W.gdi32.SelectObject(hdc_src, old_src)
        if old_dst:
            W.gdi32.SelectObject(hdc_dst, old_dst)
        if bmp_src:
            W.gdi32.DeleteObject(bmp_src)
        if bmp_dst:
            W.gdi32.DeleteObject(bmp_dst)
        if hdc_src:
            W.gdi32.DeleteDC(hdc_src)
        if hdc_dst:
            W.gdi32.DeleteDC(hdc_dst)
        if hdc_screen:
            W.user32.ReleaseDC(0, hdc_screen)
