"""开发用：界面冒烟测试。翻页、开关、改快捷键、切主题、选择器过滤与确认。"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.config import Config
from app.ui import theme
from app.ui.picker import PickerWindow
from app.ui.settings_window import HOTKEY_FIELDS, SettingsWindow

app = QApplication(sys.argv[:1])
app.setQuitOnLastWindowClosed(False)

ok = True


def check(name: str, condition: bool, detail: str = "") -> None:
    global ok
    if not condition:
        ok = False
    print(f"[{'PASS' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")


cfg = Config()
cfg.reset()

settings = SettingsWindow(cfg)
settings.apply_theme("dark")
settings.show()
app.processEvents()

# 标题栏两个控制键：尺寸一致、正方形
mini, close = settings.title_bar.min_button, settings.title_bar.close_button
check("控制键尺寸一致", mini.size() == close.size(), f"{mini.size()} vs {close.size()}")
check("控制键是正方形", mini.width() == mini.height(), f"{mini.width()}x{mini.height()}")
check("控制键垂直对齐", mini.y() == close.y(), f"{mini.y()} vs {close.y()}")

# 翻页
for index in range(4):
    settings.switch_page(index)
    app.processEvents()
    check(f"切到第 {index + 1} 页", settings.stack.currentIndex() == index)

# 开关
settings.switch_page(0)  # 常规页
app.processEvents()
settings.notify_toggle.setChecked(False)
app.processEvents()
check("关闭操作反馈写入配置", cfg.get("show_notifications") is False)
settings.notify_toggle.setChecked(True)
app.processEvents()
check("再打开", cfg.get("show_notifications") is True)

settings.shadow_toggle.setChecked(False)
app.processEvents()
check("关闭阴影修正写入配置", cfg.get("pixel_perfect") is False)
settings.shadow_toggle.setChecked(True)

# 主题切换
settings.theme_segment.set_value("light")
settings._on_theme("light")
app.setStyleSheet(theme.stylesheet("light"))
settings.apply_theme("light")
app.processEvents()
check("切到浅色", cfg.get("theme") == "light")
settings._on_theme("dark")
app.setStyleSheet(theme.stylesheet("dark"))
settings.apply_theme("dark")
app.processEvents()
check("切回深色", cfg.get("theme") == "dark")

# 忽略列表
cfg.set("ignore_list", ["foo.exe", "bar.exe"])
settings.refresh()
check("忽略列表载入", settings.ignore_list.count() == 2)
settings.ignore_list.item(0).setSelected(True)
settings._remove_ignore()
check("移除后剩 1 条", len(cfg.get("ignore_list", [])) == 1, str(cfg.get("ignore_list")))

# 快捷键修改
settings.switch_page(1)  # 快捷键页
app.processEvents()
edit = settings._hotkey_edits["center_all"]
clear = settings._hotkey_clear_buttons["center_all"]
check("空快捷键的清空按钮初始禁用", not clear.isEnabled())

# 走与用户录制完成相同的 changed 信号路径，防止按钮状态只能靠重启刷新。
edit.changed.emit("Ctrl+Alt+K")
app.processEvents()
check("快捷键改后回显", edit.text().replace(" ", "") == "Ctrl+Alt+K", edit.text())
check("刚设置快捷键即可立即清空", clear.isEnabled())

clear.click()
app.processEvents()
check("点击清空按钮写入空快捷键", cfg.get("hotkey_center_all") == "")
check("清空后显示未设置", edit.text() == "未设置", edit.text())
check("清空后按钮禁用", not clear.isEnabled())

cfg.reset_hotkeys()
settings.refresh()
check("恢复默认值为空", all(cfg.get(key) == "" for _, key, _, _ in HOTKEY_FIELDS))

settings.hide()
app.processEvents()

# 选择器
picker = PickerWindow()
picker.apply_theme("dark")
received: list[list[int]] = []
picker.chosen.connect(lambda hwnds: received.append(hwnds))
picker.open(cfg.get("ignore_list", []), True)
app.processEvents()
total = len(picker._cards)
check("选择器载入窗口", total > 0, f"{total} 个")

picker.search.setText("zzzzzz-no-such-window")
app.processEvents()
check("过滤后为空", len(picker._visible) == 0)

picker.search.clear()
app.processEvents()
check("清空过滤后恢复", len(picker._visible) == total)

picker._navigate(1, 0)
app.processEvents()
check("方向键移动选中", picker._current == 1)

picker._commit()
app.processEvents()
check("确认后发出选中", len(received) == 1 and len(received[0]) == 1)
check("确认后浮层关闭", not picker.isVisible())
check("确认后卡片释放", len(picker._cards) == 0)

# 点选卡片之后按回车（用户报过的问题：点了卡片回车没反应）
picker.open(cfg.get("ignore_list", []), False)
app.processEvents()
check("重新打开后卡片就绪", len(picker._cards) >= 2)
if len(picker._cards) >= 2:
    target_hwnd = picker._cards[1].info.hwnd
    picker._on_card_clicked(target_hwnd, False)
    app.processEvents()
    check("点选卡片后焦点回到搜索框", picker.search.hasFocus())

    received.clear()
    QTest.keyClick(picker.search, Qt.Key_Return)
    app.processEvents()
    check("点选后按回车能确认", received == [[target_hwnd]], str(received))

    # 焦点不在搜索框时（比如点了空白处），回车同样要能用
    picker.open(cfg.get("ignore_list", []), False)
    app.processEvents()
    picker.search.clearFocus()
    app.processEvents()
    received.clear()
    QTest.keyClick(picker, Qt.Key_Return)
    app.processEvents()
    check("焦点不在搜索框时回车也能确认", len(received) == 1, str(received))

cfg.reset()
print("\n结果:", "全部通过" if ok else "有失败项")
sys.exit(0 if ok else 1)
