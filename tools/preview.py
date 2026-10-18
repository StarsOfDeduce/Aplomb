"""开发用：把两个界面渲染成 PNG，方便检查排版。"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.config import Config
from app.ui.picker import PickerWindow
from app.ui.settings_window import SettingsWindow
from app.ui.theme import stylesheet

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
        QTimer.singleShot(80, app.quit)

    QTimer.singleShot(1400, done)


QTimer.singleShot(300, next_page)
app.exec()
print("preview saved to", out)
