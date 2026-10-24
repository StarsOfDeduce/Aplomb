"""配色与样式表。

视觉参考：纯平深色底 + 单一强调色，靠字重、字号、留白和 1px 细线拉层级，
不用渐变、不用毛玻璃、不堆卡片边框。强调色沿用站点的蓝，和图标保持一套。
"""

from __future__ import annotations

from PySide6.QtWidgets import QProxyStyle, QStyle


class NoFocusRectStyle(QProxyStyle):
    """保留控件焦点与键盘操作，只隐藏系统绘制的虚线焦点框。"""

    def drawPrimitive(self, element, option, painter, widget=None) -> None:  # noqa: N802
        if element == QStyle.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)


DARK = {
    "bg": "#171719",
    "panel": "#1E1E21",
    "row_hover": "#1F1F23",
    "divider": "#28282C",
    "divider_strong": "#35353B",
    "text": "#F1F2F4",
    "text_dim": "#8D8F98",
    "text_faint": "#71737C",
    "accent": "#3D7DF6",
    "accent_hover": "#5590FF",
    "accent_press": "#2F6BEA",
    "accent_soft": "#1A2438",
    "accent_text": "#7BA6FF",
    "danger": "#E26060",
    "control": "#232327",
    "control_hover": "#2A2A2F",
    "control_active": "#34343B",
}

LIGHT = {
    "bg": "#F6F7F9",
    "panel": "#FFFFFF",
    "row_hover": "#EFF1F5",
    "divider": "#E3E5EA",
    "divider_strong": "#CDD2DA",
    "text": "#101620",
    "text_dim": "#5C6472",
    "text_faint": "#8B93A1",
    "accent": "#1F6FEB",
    "accent_hover": "#1A63D6",
    "accent_press": "#1757BE",
    "accent_soft": "#E8F0FE",
    "accent_text": "#1757BE",
    "danger": "#C94040",
    "control": "#F0F1F4",
    "control_hover": "#E6E8ED",
    "control_active": "#FFFFFF",
}

_PALETTES = {"dark": DARK, "light": LIGHT}


def palette(mode: str) -> dict:
    return _PALETTES.get(mode, DARK)


_QSS = """
QWidget {
    color: $text;
    font-size: 15px;
}

#Root {
    background: transparent;
}

#WindowBody {
    background: $bg;
    border: 1px solid $divider;
    border-radius: 12px;
}

/* ---------- 标题栏 ---------- */
#TitleBar {
    background: transparent;
}
#AppName {
    font-size: 16px;
    font-weight: 600;
    color: $text;
}

/* ---------- 顶部标签 ---------- */
QPushButton#Tab {
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 1px 9px 1px;
    color: $text_dim;
    font-size: 15px;
}
QPushButton#Tab:hover {
    color: $text;
}
QPushButton#Tab:checked {
    color: $text;
    border-bottom: 2px solid $accent;
}

/* ---------- 文案层级 ---------- */
#PageKicker {
    font-size: 12px;
    color: $text_faint;
}
#PageTitle {
    font-size: 24px;
    font-weight: 700;
    color: $text;
}
#PageDesc {
    font-size: 14px;
    color: $text_dim;
}
#SectionTitle {
    font-size: 13px;
    color: $text_faint;
}
#RowTitle {
    font-size: 15px;
    color: $text;
}
#RowDesc {
    font-size: 13px;
    color: $text_faint;
}
#Divider {
    background: $divider;
    max-height: 1px;
    border: none;
}

/* ---------- 设置行 ---------- */
QWidget#Row {
    background: transparent;
    border-radius: 6px;
}
QWidget#Row:hover {
    background: $row_hover;
}

/* ---------- 快捷键按钮 ---------- */
QPushButton#HotkeyButton {
    background: $control;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 14px;
    color: $text;
}
QPushButton#HotkeyButton:hover {
    background: $control_hover;
    border-color: $divider_strong;
}
QPushButton#HotkeyButton[recording="true"] {
    background: $accent_soft;
    border-color: $accent;
    color: $accent_text;
}
QPushButton#HotkeyButton[invalid="true"] {
    border-color: $danger;
    color: $danger;
}

/* ---------- 按钮 ---------- */
QPushButton#GhostButton {
    background: transparent;
    border: 1px solid $divider_strong;
    border-radius: 6px;
    padding: 6px 14px;
    color: $text_dim;
    font-size: 14px;
}
QPushButton#GhostButton:hover {
    background: $row_hover;
    color: $text;
    border-color: $accent;
}
QPushButton#GhostButton:disabled {
    color: $text_faint;
    border-color: $divider;
}
QPushButton#PrimaryButton {
    background: $accent;
    border: 1px solid $accent;
    border-radius: 6px;
    padding: 6px 16px;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background: $accent_hover;
    border-color: $accent_hover;
}
QPushButton#PrimaryButton:pressed {
    background: $accent_press;
}
QPushButton#LinkButton {
    background: transparent;
    border: none;
    color: $accent_text;
    font-size: 14px;
    padding: 2px 0;
}
QPushButton#LinkButton:hover {
    color: $accent_hover;
}

/* ---------- 输入框 ---------- */
QLineEdit {
    background: $control;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: $accent;
    selection-color: #FFFFFF;
}
QLineEdit:focus {
    border-color: $accent;
}

/* ---------- 列表 ---------- */
#ListFrame {
    background: transparent;
    border: 1px solid $divider;
    border-radius: 8px;
}
QListWidget {
    background: transparent;
    border: none;
    padding: 6px;
    outline: none;
}
QListWidget::item {
    border-radius: 5px;
    padding: 8px 8px;
    color: $text;
}
QListWidget::item:hover {
    background: $row_hover;
}
QListWidget::item:selected {
    background: $accent_soft;
    color: $accent_text;
}

/* ---------- 滚动条 ---------- */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: $divider_strong;
    border-radius: 3px;
    min-height: 26px;
}
QScrollBar::handle:vertical:hover {
    background: $text_faint;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QToolTip {
    background: $control_hover;
    color: $text;
    border: 1px solid $divider_strong;
    border-radius: 5px;
    padding: 4px 8px;
}

/* ---------- 分段选择 ---------- */
#SegBar {
    background: $control;
    border: none;
    border-radius: 6px;
}
QPushButton#SegItem {
    background: transparent;
    border: none;
    border-radius: 5px;
    padding: 5px 13px;
    color: $text_dim;
    font-size: 14px;
}
QPushButton#SegItem:hover {
    color: $text;
}
QPushButton#SegItem:checked {
    background: $control_active;
    color: $text;
    font-weight: 600;
}

/* ---------- 窗口选择器 ---------- */
#PickerBody {
    background: $panel;
    border: 1px solid $divider_strong;
    border-radius: 14px;
}
QLineEdit#SearchBox {
    background: transparent;
    border: none;
    padding: 0px;
    font-size: 17px;
    color: $text;
}
#PickerHint {
    color: $text_faint;
    font-size: 13px;
}
#PickerEmpty {
    color: $text_faint;
    font-size: 15px;
}
QFrame#ThumbCard {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 10px;
}
QFrame#ThumbCard:hover {
    background: $row_hover;
}
QFrame#ThumbCard[selected="true"] {
    background: $accent_soft;
    border: 1px solid $accent;
}
#CardTitle {
    font-size: 14px;
    color: $text;
}
#CardSubtitle {
    font-size: 12px;
    color: $text_faint;
}

/* ---------- 状态文字 ---------- */
#StatusOk {
    font-size: 13px;
    color: $accent_text;
}
#StatusWarn {
    font-size: 13px;
    color: $danger;
}
#AboutName {
    font-size: 20px;
    font-weight: 700;
    color: $text;
}

/* ---------- 托盘菜单 ---------- */
QMenu {
    background: $panel;
    border: 1px solid $divider_strong;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    padding: 7px 30px 7px 12px;
    border-radius: 5px;
    color: $text;
    font-size: 14px;
}
QMenu::item:selected {
    background: $accent_soft;
    color: $accent_text;
}
QMenu::item:disabled {
    color: $text_faint;
}
QMenu::separator {
    height: 1px;
    background: $divider;
    margin: 5px 8px;
}
"""


def stylesheet(mode: str) -> str:
    tokens = palette(mode)
    qss = _QSS
    # 先替换长键名，避免 $text 把 $text_dim 提前吃掉
    for key in sorted(tokens, key=len, reverse=True):
        qss = qss.replace("$" + key, tokens[key])
    return qss
