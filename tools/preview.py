"""开发用：把两个界面渲染成 PNG，方便检查排版。"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

_config_temp = tempfile.TemporaryDirectory(prefix="aplomb-preview-")
os.environ["APLOMB_CONFIG_DIR"] = _config_temp.name

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import win32api as W
from app.config import Config
from app.ui.picker import PickerWindow
from app.ui.settings_window import SettingsWindow
from app.ui.theme import stylesheet
from app.ui import window_chooser as chooser_module
from app.ui.window_chooser import WindowChooser
from app.windows import WindowInfo

mode = sys.argv[1] if len(sys.argv) > 1 else "dark"
only = sys.argv[2] if len(sys.argv) > 2 else "all"

app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)
# 不调用 app.setFont()：显式指定字体会让 Qt 为每个控件解析回退链，实测多占 50MB+
app.setStyleSheet(stylesheet(mode))

out = BASE / "preview"
out.mkdir(exist_ok=True)

cfg = Config()
settings = SettingsWindow(cfg)
settings.apply_theme(mode)
settings.show()

pages = [(0, "general"), (1, "hotkeys"), (2, "ignore"), (3, "about")]
index = {"i": 0}


def next_page() -> None:
    if index["i"] >= len(pages):
        settings.hide()
        if only in ("all", "picker"):
            QTimer.singleShot(120, shot_picker)
        elif only == "chooser":
            QTimer.singleShot(120, shot_chooser)
        else:
            app.quit()
        return
    num, name = pages[index["i"]]
    settings.switch_page(num)
    QTimer.singleShot(180, lambda n=name: capture(n))


def capture(name: str) -> None:
    settings.grab().save(str(out / f"settings_{name}_{mode}.png"))
    index["i"] += 1
    next_page()


def shot_picker() -> None:
    picker = PickerWindow()
    picker.apply_theme(mode)
    picker.open(cfg.get("ignore_list", []), True)

    def done() -> None:
        picker.grab().save(str(out / f"picker_{mode}.png"))
        picker.close_picker()
        if only == "all":
            QTimer.singleShot(80, shot_chooser)
        else:
            QTimer.singleShot(80, app.quit)

    QTimer.singleShot(1400, done)


def shot_chooser() -> None:
    """用匿名的稳定样例生成精确规则选择器截图。"""
    rect = W.RECT(100, 100, 900, 700)
    work = W.RECT(0, 0, 1920, 1040)
    samples = [
        (1001, "记事本", "Notepad", r"C:\Windows\System32\notepad.exe", "notepad.exe"),
        (1002, "浏览器示例", "Chrome_WidgetWin_1", r"C:\Program Files\Browser\browser.exe", "browser.exe"),
        (1003, "计算器", "ApplicationFrameWindow", r"C:\Windows\System32\calc.exe", "calc.exe"),
    ]
    windows = [
        WindowInfo(
            hwnd=hwnd,
            title=title,
            class_name=class_name,
            pid=5000 + hwnd,
            exe_path=exe_path,
            exe_name=exe_name,
            rect=rect,
            monitor_rect=W.RECT(0, 0, 1920, 1080),
            work_rect=work,
            minimized=False,
            maximized=False,
            fullscreen=False,
            style=W.WS_VISIBLE,
            ex_style=W.WS_EX_APPWINDOW,
            owner=0,
        )
        for hwnd, title, class_name, exe_path, exe_name in samples
    ]
    chooser_module.list_windows = lambda *_args, **_kwargs: windows
    chooser_module.automation_eligible = lambda _info: True

    chooser = WindowChooser([], purpose="remember")
    chooser.apply_theme(mode)
    chooser.show()

    def done() -> None:
        chooser.grab().save(str(out / f"chooser_{mode}.png"))
        chooser.close()
        QTimer.singleShot(80, app.quit)

    QTimer.singleShot(300, done)


QTimer.singleShot(300, next_page)
app.exec()
print("preview saved to", out)
