"""设置界面。无边框 + 自绘圆角，顶部标签导航，内容平铺不堆卡片。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, APP_NAME_CN, __version__, autostart
from ..config import Config, config_path
from ..icons import app_icon
from . import theme
from .widgets import (
    ChromeButton,
    HotkeyClearButton,
    HotkeyEdit,
    RowGroup,
    SectionLabel,
    SegmentedControl,
    SettingRow,
    ToggleSwitch,
)
from .window_chooser import WindowChooser

SHADOW = 18
HOTKEY_FIELDS = (
    ("center_current", "hotkey_center_current", "居中当前窗口", "把前台窗口移到所在屏幕正中"),
    ("center_select", "hotkey_center_select", "选择窗口居中", "呼出窗口浮层，挑一个或多个居中"),
    ("center_all", "hotkey_center_all", "全部窗口居中", "批量居中所有普通窗口，跳过全屏与最大化"),
)

PAGES = (
    ("01 / PREFERENCES", "常规"),
    ("02 / SHORTCUTS", "快捷键"),
    ("03 / EXCLUSIONS", "忽略列表"),
    ("04 / ABOUT", "关于"),
)


class TitleBar(QWidget):
    def __init__(self, window: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._window = window
        self._drag_offset: QPoint | None = None
        self.setObjectName("TitleBar")
        self.setFixedHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 14, 0)
        layout.setSpacing(10)

        icon_label = QLabel(self)
        icon_label.setPixmap(app_icon().pixmap(20, 20))
        layout.addWidget(icon_label)

        name = QLabel(APP_NAME, self)
        name.setObjectName("AppName")
        layout.addWidget(name)

        layout.addStretch(1)

        self.min_button = ChromeButton("min", self)
        self.min_button.setToolTip("最小化")
        self.min_button.clicked.connect(window.showMinimized)
        layout.addWidget(self.min_button)

        self.close_button = ChromeButton("close", self)
        self.close_button.setToolTip("收起到托盘（程序继续在后台待命）")
        self.close_button.clicked.connect(window.hide)
        layout.addWidget(self.close_button)

    # 拖动
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class ValueRow(QWidget):
    """左侧标题、右侧值的只读行，长文本从中间省略。"""

    def __init__(self, title: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Row")
        self.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        label = QLabel(title, self)
        label.setObjectName("RowTitle")
        layout.addWidget(label)
        layout.addStretch(1)

        self.value_label = QLabel(self)
        self.value_label.setObjectName("RowDesc")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_label.setToolTip(value)
        self._full_text = value
        layout.addWidget(self.value_label)
        self._elide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        self._elide()
        super().resizeEvent(event)

    def _elide(self) -> None:
        available = max(120, self.width() - 160)
        text = self.fontMetrics().elidedText(self._full_text, Qt.ElideMiddle, available)
        self.value_label.setText(text)


class SettingsWindow(QWidget):
    hotkeys_changed = Signal()
    theme_changed = Signal(str)
    quit_requested = Signal()
    center_current = Signal()
    center_select = Signal()
    center_all = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self._mode = "dark"
        self._centered = False
        self._hotkey_edits: dict[str, HotkeyEdit] = {}
        self._hotkey_clear_buttons: dict[str, HotkeyClearButton] = {}

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setObjectName("Root")

        self._build()
        self.refresh()

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW, SHADOW, SHADOW, SHADOW)

        self.body = QFrame(self)
        self.body.setObjectName("WindowBody")
        self.body.setAttribute(Qt.WA_StyledBackground, True)
        outer.addWidget(self.body)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 8)
        shadow.setColor(Qt.black)
        self.body.setGraphicsEffect(shadow)

        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.title_bar = TitleBar(self, self.body)
        body_layout.addWidget(self.title_bar)

        body_layout.addWidget(self._build_tabs())

        self.stack = QStackedWidget(self.body)
        self.stack.addWidget(self._page_general())
        self.stack.addWidget(self._page_hotkeys())
        self.stack.addWidget(self._page_ignore())
        self.stack.addWidget(self._page_about())
        body_layout.addWidget(self.stack, 1)

        self.setFixedSize(860, 664)

    def _build_tabs(self) -> QWidget:
        bar = QWidget(self.body)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(26)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for index, (_, label) in enumerate(PAGES):
            button = QPushButton(label, bar)
            button.setObjectName("Tab")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, i=index: self.switch_page(i))
            layout.addWidget(button, 0, Qt.AlignBottom)
            self._nav_group.addButton(button, index)
            if index == 0:
                button.setChecked(True)

        layout.addStretch(1)
        bar.setFixedHeight(42)
        return bar

    def switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        button = self._nav_group.button(index)
        if button is not None:
            button.setChecked(True)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _page_shell(index: int, desc: str) -> tuple[QWidget, QVBoxLayout]:
        kicker, title = PAGES[index]
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 20)
        layout.setSpacing(0)

        kicker_label = QLabel(kicker, page)
        kicker_label.setObjectName("PageKicker")
        layout.addWidget(kicker_label)
        layout.addSpacing(7)

        title_label = QLabel(title, page)
        title_label.setObjectName("PageTitle")
        layout.addWidget(title_label)
        layout.addSpacing(7)

        desc_label = QLabel(desc, page)
        desc_label.setObjectName("PageDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        layout.addSpacing(20)
        return page, layout

    # -- 快捷键 --------------------------------------------------------- #
    def _page_hotkeys(self) -> QWidget:
        page, layout = self._page_shell(
            1, "点击右侧按钮后按下组合键即可修改；至少需要包含 Ctrl、Alt 或 Win 之一。"
        )

        group = RowGroup(page)
        for action, key, title, desc in HOTKEY_FIELDS:
            control = QWidget(group)
            control_layout = QHBoxLayout(control)
            control_layout.setContentsMargins(0, 0, 0, 0)
            control_layout.setSpacing(8)

            edit = HotkeyEdit(self.config.get(key, ""), control)
            edit.changed.connect(lambda spec, a=action: self._on_hotkey_edited(a, spec))
            self._hotkey_edits[action] = edit
            control_layout.addWidget(edit)

            clear = HotkeyClearButton(control)
            clear.clicked.connect(lambda _=False, a=action: self._clear_hotkey(a))
            self._hotkey_clear_buttons[action] = clear
            control_layout.addWidget(clear)

            group.add_row(SettingRow(title, desc, control, group))
        layout.addWidget(group)

        layout.addSpacing(14)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(10)

        self.hotkey_status = QLabel("", page)
        self.hotkey_status.setObjectName("StatusOk")
        footer.addWidget(self.hotkey_status, 1)

        reset = QPushButton("恢复默认", page)
        reset.setObjectName("GhostButton")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self._reset_hotkeys)
        footer.addWidget(reset)
        layout.addLayout(footer)

        layout.addSpacing(26)
        layout.addWidget(SectionLabel("小提示", page))
        layout.addSpacing(8)

        tip = QLabel(
            "关闭设置窗口只会把它收回托盘，程序仍在后台待命；要完全退出，"
            "请右键托盘图标选择「退出」。快捷键修改后立即生效。",
            page,
        )
        tip.setObjectName("RowDesc")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        layout.addStretch(1)
        return page

    def _on_hotkey_edited(self, action: str, spec: str) -> None:
        duplicates = [
            a for a, key, _, _ in HOTKEY_FIELDS
            if a != action and self.config.get(key, "") == spec and spec
        ]
        if duplicates:
            self.hotkey_status.setObjectName("StatusWarn")
            self._restyle(self.hotkey_status)
            self.hotkey_status.setText(f"「{spec}」已经分配给其它动作了")
            self.refresh()
            return

        key = next(k for a, k, _, _ in HOTKEY_FIELDS if a == action)
        self.config.set(key, spec)
        self.hotkeys_changed.emit()

    def _clear_hotkey(self, action: str) -> None:
        self._on_hotkey_edited(action, "")
        self.refresh()

    def _reset_hotkeys(self) -> None:
        self.config.reset_hotkeys()
        self.refresh()
        self.hotkeys_changed.emit()

    def notify_hotkey_result(self, failed: list[str]) -> None:
        labels = {a: t for a, _, t, _ in HOTKEY_FIELDS}
        if failed:
            names = "、".join(labels.get(a, a) for a in failed)
            self.hotkey_status.setObjectName("StatusWarn")
            self.hotkey_status.setText(f"{names} 的组合键被其它程序占用，请换一个")
        else:
            self.hotkey_status.setObjectName("StatusOk")
            has_hotkey = any(self.config.get(key, "") for _, key, _, _ in HOTKEY_FIELDS)
            self.hotkey_status.setText("快捷键已生效" if has_hotkey else "当前未启用快捷键")
        self._restyle(self.hotkey_status)

    # -- 常规 ----------------------------------------------------------- #
    def _page_general(self) -> QWidget:
        page, layout = self._page_shell(0, "这些开关即时生效，不需要重启程序。")

        group = RowGroup(page)

        self.autostart_toggle = ToggleSwitch(group)
        self.autostart_toggle.toggled.connect(self._on_autostart)
        group.add_row(SettingRow("开机自启", "登录 Windows 后静默驻留托盘", self.autostart_toggle, group))

        self.notify_toggle = ToggleSwitch(group)
        self.notify_toggle.toggled.connect(
            lambda v: self.config.set("show_notifications", v)
        )
        group.add_row(SettingRow("操作反馈", "居中后在托盘弹出轻提示", self.notify_toggle, group))

        self.shadow_toggle = ToggleSwitch(group)
        self.shadow_toggle.toggled.connect(
            lambda v: self.config.set("pixel_perfect", v)
        )
        group.add_row(SettingRow(
            "像素级阴影修正",
            "按 DWM 的真实可见边框对齐，消掉窗口阴影造成的视觉偏移",
            self.shadow_toggle, group,
        ))

        self.thumb_toggle = ToggleSwitch(group)
        self.thumb_toggle.toggled.connect(
            lambda v: self.config.set("picker_thumbnails", v)
        )
        group.add_row(SettingRow("选择器显示缩略图", "关闭后只显示图标，呼出更快", self.thumb_toggle, group))

        layout.addWidget(group)
        layout.addSpacing(26)
        layout.addWidget(SectionLabel("外观", page))
        layout.addSpacing(10)

        theme_group = RowGroup(page)
        self.theme_segment = SegmentedControl(
            [("system", "跟随系统"), ("light", "浅色"), ("dark", "深色")], theme_group
        )
        self.theme_segment.changed.connect(self._on_theme)
        theme_group.add_row(SettingRow("主题", "设置窗口与选择器的配色", self.theme_segment, theme_group))
        layout.addWidget(theme_group)

        layout.addStretch(1)
        return page

    def _on_autostart(self, enabled: bool) -> None:
        if autostart.set_enabled(enabled):
            self.config.set("autostart", enabled)
        else:
            self.autostart_toggle.blockSignals(True)
            self.autostart_toggle.setChecked(not enabled)
            self.autostart_toggle.blockSignals(False)

    def _on_theme(self, mode: str) -> None:
        self.config.set("theme", mode)
        self.theme_changed.emit(mode)

    # -- 忽略列表 ------------------------------------------------------- #
    def _page_ignore(self) -> QWidget:
        page, layout = self._page_shell(
            2, "列表里的程序不会被任何居中动作移动，也不会出现在选择器里。"
        )

        frame = QFrame(page)
        frame.setObjectName("ListFrame")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)

        self.ignore_list = QListWidget(frame)
        self.ignore_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.ignore_list.setAlternatingRowColors(False)
        frame_layout.addWidget(self.ignore_list)
        layout.addWidget(frame, 1)

        self.ignore_empty = QLabel("还没有忽略任何程序", self.ignore_list.viewport())
        self.ignore_empty.setObjectName("PickerEmpty")
        self.ignore_empty.setAlignment(Qt.AlignCenter)
        self.ignore_empty.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.ignore_list.viewport().installEventFilter(self)

        layout.addSpacing(14)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        pick_button = QPushButton("从窗口选择…", page)
        pick_button.setObjectName("PrimaryButton")
        pick_button.setCursor(Qt.PointingHandCursor)
        pick_button.setToolTip("直接从未关闭的窗口里挑，不用去翻程序路径")
        pick_button.clicked.connect(self._add_ignore_from_windows)
        buttons.addWidget(pick_button)

        add_button = QPushButton("选择程序…", page)
        add_button.setObjectName("GhostButton")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.setToolTip("程序没在运行时，用这个找它的 exe")
        add_button.clicked.connect(self._add_ignore)
        buttons.addWidget(add_button)

        remove_button = QPushButton("移除选中", page)
        remove_button.setObjectName("GhostButton")
        remove_button.setCursor(Qt.PointingHandCursor)
        remove_button.clicked.connect(self._remove_ignore)
        buttons.addWidget(remove_button)

        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _add_ignore_from_windows(self) -> None:
        current = list(self.config.get("ignore_list", []))
        chooser = WindowChooser(current, self)
        chooser.apply_theme(self._mode)
        if chooser.exec() != QDialog.Accepted:
            return

        names = chooser.selected_exe_names()
        if not names:
            return

        merged = list(current)
        existing = {name.lower() for name in merged}
        for name in names:
            if name.lower() not in existing:
                merged.append(name)
                existing.add(name.lower())
        self.config.set("ignore_list", merged)
        self._reload_ignore_list()

    def _add_ignore(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择要忽略的程序", "C:/Program Files",
            "可执行文件 (*.exe);;所有文件 (*.*)",
        )
        if not paths:
            return
        items = list(self.config.get("ignore_list", []))
        for path in paths:
            name = Path(path).name
            if name and name.lower() not in [i.lower() for i in items]:
                items.append(name)
        self.config.set("ignore_list", items)
        self._reload_ignore_list()

    def _remove_ignore(self) -> None:
        selected = {item.text() for item in self.ignore_list.selectedItems()}
        if not selected:
            return
        items = [i for i in self.config.get("ignore_list", []) if i not in selected]
        self.config.set("ignore_list", items)
        self._reload_ignore_list()

    def _reload_ignore_list(self) -> None:
        self.ignore_list.clear()
        for name in self.config.get("ignore_list", []):
            item = QListWidgetItem(name)
            item.setToolTip(name)
            self.ignore_list.addItem(item)
        self._sync_ignore_empty()

    def _sync_ignore_empty(self) -> None:
        self.ignore_empty.setGeometry(self.ignore_list.viewport().rect())
        self.ignore_empty.setVisible(self.ignore_list.count() == 0)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.ignore_list.viewport() and event.type() == QEvent.Resize:
            self._sync_ignore_empty()
        return super().eventFilter(obj, event)

    # -- 关于 ----------------------------------------------------------- #
    def _page_about(self) -> QWidget:
        page, layout = self._page_shell(3, "一个只做一件事的小工具。")

        header = QHBoxLayout()
        header.setSpacing(14)

        icon_label = QLabel(page)
        icon_label.setPixmap(app_icon().pixmap(46, 46))
        header.addWidget(icon_label, 0, Qt.AlignTop)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        name = QLabel(f"{APP_NAME}  ·  {APP_NAME_CN}", page)
        name.setObjectName("AboutName")
        text_box.addWidget(name)
        tag = QLabel("让窗口安静地回到它该在的位置。", page)
        tag.setObjectName("RowDesc")
        text_box.addWidget(tag)
        header.addLayout(text_box, 1)
        layout.addLayout(header)

        layout.addSpacing(22)

        group = RowGroup(page)
        group.add_row(ValueRow("版本", __version__, group))
        group.add_row(ValueRow("配置文件", str(config_path()), group))
        group.add_row(ValueRow("运行方式", "常驻托盘 · 托盘菜单退出", group))
        layout.addWidget(group)

        layout.addSpacing(18)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        open_config = QPushButton("打开配置目录", page)
        open_config.setObjectName("GhostButton")
        open_config.setCursor(Qt.PointingHandCursor)
        open_config.clicked.connect(self._open_config_dir)
        buttons.addWidget(open_config)

        buttons.addStretch(1)

        quit_button = QPushButton("退出 Aplomb", page)
        quit_button.setObjectName("GhostButton")
        quit_button.setCursor(Qt.PointingHandCursor)
        quit_button.clicked.connect(self.quit_requested.emit)
        buttons.addWidget(quit_button)

        layout.addLayout(buttons)
        layout.addStretch(1)
        return page

    def _open_config_dir(self) -> None:
        try:
            os.startfile(str(config_path().parent))  # noqa: S606
        except OSError:
            pass

    # ------------------------------------------------------------------ #
    @staticmethod
    def _restyle(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def refresh(self) -> None:
        """把配置里的值同步到控件上。"""
        for action, key, _, _ in HOTKEY_FIELDS:
            edit = self._hotkey_edits.get(action)
            if edit is not None and not edit.is_recording:
                edit.set_spec(self.config.get(key, ""))
            clear = self._hotkey_clear_buttons.get(action)
            if clear is not None:
                clear.setEnabled(bool(self.config.get(key, "")))

        self.autostart_toggle.blockSignals(True)
        self.autostart_toggle.setChecked(autostart.is_enabled())
        self.autostart_toggle.blockSignals(False)

        self.notify_toggle.setChecked(bool(self.config.get("show_notifications", True)))
        self.shadow_toggle.setChecked(bool(self.config.get("pixel_perfect", True)))
        self.thumb_toggle.setChecked(bool(self.config.get("picker_thumbnails", True)))
        self.theme_segment.set_value(self.config.get("theme", "system"))
        self._reload_ignore_list()

    def apply_theme(self, mode: str) -> None:
        self._mode = mode
        self.title_bar.min_button.apply_theme(mode)
        self.title_bar.close_button.apply_theme(mode)
        for clear in self._hotkey_clear_buttons.values():
            clear.apply_theme(mode)
        for toggle in (self.autostart_toggle, self.notify_toggle,
                       self.shadow_toggle, self.thumb_toggle):
            toggle.apply_theme(mode)
        self.update()

    # ------------------------------------------------------------------ #
    def showEvent(self, event) -> None:  # noqa: N802
        self.refresh()
        if not self._centered:
            screen = QGuiApplication.primaryScreen()
            area = screen.availableGeometry()
            self.move(
                area.x() + (area.width() - self.width()) // 2,
                area.y() + (area.height() - self.height()) // 2,
            )
            self._centered = True
        super().showEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)
