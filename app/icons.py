"""图标：程序图标从 assets 加载，窗口图标按 exe 缓存。

程序图标是设计稿（assets/icon_source.png）生成的多尺寸 ICO/PNG，
运行时只读文件，不再现画。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QFileInfo, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QFileIconProvider

_ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
_app_icon: QIcon | None = None
_provider: QFileIconProvider | None = None
_window_icons: dict[str, QIcon] = {}
_ICON_CACHE_LIMIT = 96


def asset_dir() -> Path:
    """打包后资源在 _MEIPASS/assets，开发时在项目根目录。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "assets"
    return Path(__file__).resolve().parent.parent / "assets"


def _fallback_icon() -> QIcon:
    """素材缺失时的兜底：一块蓝底圆角方块，至少不会是个空白图标。"""
    icon = QIcon()
    for size in _ICON_SIZES:
        image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        s = float(size)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1F6FEB"))
        painter.drawRoundedRect(QRectF(0, 0, s, s), s * 0.2, s * 0.2)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRect(QRectF(s * 0.33, s * 0.33, s * 0.34, s * 0.34))
        painter.end()
        icon.addPixmap(QPixmap.fromImage(image))
    return icon


def app_icon() -> QIcon:
    global _app_icon
    if _app_icon is not None:
        return _app_icon

    base = asset_dir()
    ico_path = base / "aplomb.ico"
    png_path = base / "aplomb.png"

    icon = QIcon()
    if ico_path.exists():
        # ICO 里已经含 16~256 各档尺寸，Qt 会挑最合适的那一帧
        icon = QIcon(str(ico_path))
    if icon.isNull() and png_path.exists():
        source = QPixmap(str(png_path))
        if not source.isNull():
            for size in _ICON_SIZES:
                icon.addPixmap(
                    source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
    if icon.isNull():
        icon = _fallback_icon()

    _app_icon = icon
    return icon


def _file_icon_provider() -> QFileIconProvider:
    global _provider
    if _provider is None:
        _provider = QFileIconProvider()
    return _provider


def window_icon(exe_path: str) -> QIcon:
    """按可执行文件取图标，带一个固定上限的缓存，避免无限增长。"""
    if not exe_path:
        return app_icon()

    cached = _window_icons.get(exe_path)
    if cached is not None:
        return cached

    icon = QIcon()
    try:
        icon = _file_icon_provider().icon(QFileInfo(exe_path))
    except Exception:
        icon = QIcon()
    if icon.isNull():
        icon = app_icon()

    if len(_window_icons) >= _ICON_CACHE_LIMIT:
        _window_icons.clear()
    _window_icons[exe_path] = icon
    return icon
