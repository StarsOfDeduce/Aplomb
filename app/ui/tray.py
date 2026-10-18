"""系统托盘：图标、菜单、气泡提示。"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import APP_NAME, APP_NAME_CN
from ..icons import app_icon


class TrayManager(QObject):
    center_current = Signal()
    center_select = Signal()
    center_all = Signal()
    show_settings = Signal()
    quit_app = Signal()
    autostart_toggled = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(f"{APP_NAME} · {APP_NAME_CN}")

        self.menu = QMenu()
        self.menu.setToolTipsVisible(True)

        self.act_current = QAction("居中当前窗口", self)
        self.act_current.triggered.connect(self.center_current.emit)
        self.menu.addAction(self.act_current)

        self.act_select = QAction("选择窗口居中…", self)
        self.act_select.triggered.connect(self.center_select.emit)
        self.menu.addAction(self.act_select)

        self.act_all = QAction("全部窗口居中", self)
        self.act_all.triggered.connect(self.center_all.emit)
        self.menu.addAction(self.act_all)

        self.menu.addSeparator()

        self.act_settings = QAction("设置…", self)
        self.act_settings.triggered.connect(self.show_settings.emit)
        self.menu.addAction(self.act_settings)

        self.act_autostart = QAction("开机自启", self)
        self.act_autostart.setCheckable(True)
        self.act_autostart.toggled.connect(self.autostart_toggled.emit)
        self.menu.addAction(self.act_autostart)

        self.menu.addSeparator()

        self.act_quit = QAction("退出", self)
        self.act_quit.triggered.connect(self.quit_app.emit)
        self.menu.addAction(self.act_quit)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

    # ------------------------------------------------------------------ #
    def show(self) -> None:
        self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_settings.emit()

    def set_autostart(self, enabled: bool) -> None:
        self.act_autostart.blockSignals(True)
        self.act_autostart.setChecked(enabled)
        self.act_autostart.blockSignals(False)

    def update_labels(self, current: str, select: str, all_: str) -> None:
        self.act_current.setText(f"居中当前窗口\t{current}" if current else "居中当前窗口")
        self.act_select.setText(f"选择窗口居中…\t{select}" if select else "选择窗口居中…")
        self.act_all.setText(f"全部窗口居中\t{all_}" if all_ else "全部窗口居中")
        self.act_current.setEnabled(bool(current))
        self.act_select.setEnabled(bool(select))
        self.act_all.setEnabled(bool(all_))

    def notify(self, title: str, message: str) -> None:
        try:
            self.tray.showMessage(title, message, app_icon(), 2200)
        except Exception:
            pass
