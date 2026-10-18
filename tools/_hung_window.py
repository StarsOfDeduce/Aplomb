"""自检用：一个会"卡死"的窗口。

显示出来之后直接阻塞主线程、不再处理消息，用来验证 Aplomb 枚举窗口时
不会被这种进程拖住。
"""

from __future__ import annotations

import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QWidget

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("Aplomb Hung Target")
window.resize(500, 360)
window.move(200, 160)
QLabel("这个窗口会停止响应消息", window).setGeometry(20, 20, 460, 60)
window.show()

QTimer.singleShot(600, lambda: time.sleep(25))  # 卡死 25 秒
sys.exit(app.exec())
