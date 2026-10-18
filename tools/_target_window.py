"""自检用的目标窗口：独立进程，方便验证跨进程居中。"""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QWidget

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("Aplomb Test Target")
window.resize(640, 420)
window.move(60, 60)
label = QLabel("Aplomb 居中自检目标窗口\n这个窗口应当被精确移到屏幕正中。", window)
label.setGeometry(20, 20, 600, 380)
window.show()
QTimer.singleShot(9000, app.quit)
sys.exit(app.exec())
