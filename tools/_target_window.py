"""自检用的目标窗口：独立进程，方便验证跨进程居中。"""

from __future__ import annotations

import argparse
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget

parser = argparse.ArgumentParser()
parser.add_argument("--popup", action="store_true")
parser.add_argument("--delay-ms", type=int, default=0)
parser.add_argument("--lifetime-ms", type=int, default=9000)
args = parser.parse_args()

app = QApplication(sys.argv[:1])
window = QWidget()
window.setWindowTitle("Aplomb Test Target")
window.resize(640, 420)
window.move(60, 60)
label = QLabel("Aplomb 居中自检目标窗口\n这个窗口应当被精确移到屏幕正中。", window)
label.setGeometry(20, 20, 600, 380)

notice = None
if args.popup:
    notice = QWidget(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    notice.setWindowTitle("Aplomb Test Notice")
    notice.resize(280, 96)
    notice_label = QLabel("通知测试：它必须留在右下角。", notice)
    notice_label.setGeometry(16, 16, 248, 64)


def show_windows() -> None:
    window.show()
    if notice is not None:
        area = app.primaryScreen().availableGeometry()
        notice.move(area.right() - notice.width() - 24,
                    area.bottom() - notice.height() - 24)
        notice.show()


QTimer.singleShot(max(0, args.delay_ms), show_windows)
QTimer.singleShot(max(args.lifetime_ms, args.delay_ms + 1000), app.quit)
sys.exit(app.exec())
