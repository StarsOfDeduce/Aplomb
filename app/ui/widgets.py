"""一组小而克制的自定义控件：开关、快捷键录制、分段选择、设置行。"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..hotkeys import format_hotkey
from ..win32api import MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN
from . import theme


class ToggleSwitch(QAbstractButton):
    """40×22 的滑动开关。位置用属性动画，不用定时器。"""

    _mode = "dark"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(40, 22)

    def _get_knob(self) -> float:
        return self._pos

    def _set_knob(self, value: float) -> None:
        self._pos = value
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802
        super().setChecked(checked)
        self._anim.stop()
        self._pos = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        tokens = theme.palette(self._mode)
        on = self.isChecked()
        track = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)

        if on:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(tokens["accent"]))
        else:
            painter.setPen(QPen(QColor(tokens["divider_strong"]), 1))
            painter.setBrush(QColor(tokens["control"]))
        painter.drawRoundedRect(track, 11, 11)

        diameter = 16.0
        x = 3.0 + self._pos * (self.width() - diameter - 6.0)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(x, 3.0, diameter, diameter))
        painter.end()

    def apply_theme(self, mode: str) -> None:
        self._mode = mode
        self.update()


class HotkeyEdit(QPushButton):
    """点击进入录制状态，按下组合键即生效。"""

    changed = Signal(str)

    def __init__(self, spec: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HotkeyButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(168)
        self.setFocusPolicy(Qt.StrongFocus)
        self._spec = ""
        self._recording = False
        # 等宽字体只在这三个按钮上单独设置，绝不写进 QSS
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        mono.setPixelSize(12)
        self.setFont(mono)
        self.set_spec(spec)
        self.clicked.connect(self.start_recording)

    # -- 状态 ---------------------------------------------------------- #
    @property
    def is_recording(self) -> bool:
        return self._recording

    def set_spec(self, spec: str) -> None:
        self._spec = spec or ""
        self._refresh_text()

    def spec(self) -> str:
        return self._spec

    def _refresh_text(self) -> None:
        if self._recording:
            self.setText("请按下快捷键…")
            return
        if not self._spec:
            self.setText("未设置")
            return
        self.setText(self._spec.replace("+", "  +  "))

    def _set_flag(self, name: str, value: bool) -> None:
        self.setProperty(name, "true" if value else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    # -- 录制 ---------------------------------------------------------- #
    def start_recording(self) -> None:
        if self._recording:
            return
        self._recording = True
        self._set_flag("recording", True)
        self._set_flag("invalid", False)
        self._refresh_text()
        self.setFocus(Qt.OtherFocusReason)

    def stop_recording(self, commit: bool = False) -> None:
        if not self._recording:
            return
        self._recording = False
        self._set_flag("recording", False)
        self._refresh_text()
        if commit:
            self.changed.emit(self._spec)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if not self._recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key_Escape:
            self.stop_recording(commit=False)
            return
        if key in (Qt.Key_Delete, Qt.Key_Backspace):
            self._spec = ""
            self.stop_recording(commit=True)
            return
        if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
            return  # 只按下修饰键时不结束录制

        mods = 0
        qt_mods = event.modifiers()
        if qt_mods & Qt.ControlModifier:
            mods |= MOD_CONTROL
        if qt_mods & Qt.AltModifier:
            mods |= MOD_ALT
        if qt_mods & Qt.ShiftModifier:
            mods |= MOD_SHIFT
        if qt_mods & Qt.MetaModifier:
            mods |= MOD_WIN

        vk = int(event.nativeVirtualKey())
        candidate = format_hotkey(mods, vk)
        # 必须带 Ctrl / Alt / Win，否则会抢占正常打字
        if not candidate or not (mods & (MOD_CONTROL | MOD_ALT | MOD_WIN)):
            self._set_flag("invalid", True)
            return

        self._spec = candidate
        self._set_flag("invalid", False)
        self.stop_recording(commit=True)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        if self._recording:
            self.stop_recording(commit=False)
        super().focusOutEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._recording:
            self.stop_recording(commit=False)
            return
        super().mousePressEvent(event)


class SegmentedControl(QWidget):
    """三选一的分段控件，值用字符串。"""

    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SegBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self._buttons: dict[str, QPushButton] = {}
        for value, label in options:
            button = QPushButton(label)
            button.setObjectName("SegItem")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setAutoExclusive(True)
            button.clicked.connect(lambda _=False, v=value: self._on_click(v))
            layout.addWidget(button)
            self._buttons[value] = button

    def _on_click(self, value: str) -> None:
        self.changed.emit(value)

    def set_value(self, value: str) -> None:
        button = self._buttons.get(value)
        if button and not button.isChecked():
            button.setChecked(True)

    def value(self) -> str:
        for value, button in self._buttons.items():
            if button.isChecked():
                return value
        return ""


class ChromeButton(QAbstractButton):
    """标题栏的最小化 / 关闭。

    不用文字画符号 —— 字体里的 — 和 × 基线和字宽都不一样，
    大小和居中都对不齐。这里直接画线，尺寸、位置完全可控。
    """

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._mode = "dark"
        self.setFixedSize(28, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)

    def apply_theme(self, mode: str) -> None:
        self._mode = mode
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        tokens = theme.palette(self._mode)
        hovered = self.underMouse()
        is_close = self._kind == "close"

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect())
        if hovered:
            background = QColor(tokens["danger"] if is_close else tokens["row_hover"])
            if self.isDown():
                background = background.darker(115)
            painter.setPen(Qt.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 5, 5)

        if is_close and hovered:
            color = QColor("#FFFFFF")
        else:
            color = QColor(tokens["text"] if hovered else tokens["text_faint"])

        center = rect.center()
        if is_close:
            painter.setPen(QPen(color, 1.5, Qt.SolidLine, Qt.RoundCap))
            arm = 4.6
            painter.drawLine(QPointF(center.x() - arm, center.y() - arm),
                             QPointF(center.x() + arm, center.y() + arm))
            painter.drawLine(QPointF(center.x() + arm, center.y() - arm),
                             QPointF(center.x() - arm, center.y() + arm))
        else:
            # 横线按整像素对齐才不糊：落在半像素上会被抗锯齿摊成两行浅灰
            y = round(center.y()) - 0.5
            x = round(center.x())
            painter.setPen(QPen(color, 1.0, Qt.SolidLine, Qt.FlatCap))
            painter.drawLine(QPointF(x - 6, y), QPointF(x + 6, y))
        painter.end()


class SettingRow(QWidget):
    """一行设置：左边标题+说明，右边控件。整行可 hover。"""

    def __init__(self, title: str, desc: str = "",
                 control: QWidget | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Row")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(3)
        label = QLabel(title)
        label.setObjectName("RowTitle")
        text_box.addWidget(label)
        if desc:
            sub = QLabel(desc)
            sub.setObjectName("RowDesc")
            sub.setWordWrap(True)
            text_box.addWidget(sub)
        layout.addLayout(text_box, 1)

        if control is not None:
            control.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            layout.addWidget(control, 0, Qt.AlignVCenter)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Divider")
        self.setFixedHeight(1)


class RowGroup(QWidget):
    """一组设置行，行与行之间用 1px 细线分隔。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def add_row(self, row: QWidget) -> None:
        if self._layout.count() > 0:
            self._layout.addWidget(Divider())
        self._layout.addWidget(row)


class SectionLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("SectionTitle")
