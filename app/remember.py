"""精确、一次性的自动居中规则。

规则由完整可执行文件路径和窗口类名组成，只匹配标准主任务窗口。创建阶段
几何可用时先尝试在显示前居中；否则在 SHOW 事件后尽早执行一次。Aplomb
不会继续跟踪位置，也不会和应用自己的恢复逻辑争抢。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from . import win32api as W
from . import windows as winlib
from .win32api import (
    EVENT_OBJECT_CREATE,
    EVENT_OBJECT_DESTROY,
    EVENT_OBJECT_SHOW,
    OBJID_WINDOW,
    WINEVENT_OUTOFCONTEXT,
    WINEVENT_SKIPOWNPROCESS,
)


def rule_key(rule: dict) -> tuple[str, str]:
    """规则的大小写不敏感唯一键；无效规则返回空键。"""
    if not isinstance(rule, dict):
        return "", ""
    path = winlib.normalized_exe_path(str(rule.get("exe_path", "")))
    class_name = str(rule.get("class_name", "")).strip().casefold()
    return path, class_name


def valid_rules(raw) -> list[dict]:
    """过滤损坏或重复的配置项，不让手改 JSON 影响事件回调。"""
    if not isinstance(raw, list):
        return []
    result: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        key = rule_key(item)
        if not all(key) or key in seen:
            continue
        seen.add(key)
        result.append({
            "exe_path": str(item.get("exe_path", "")).strip(),
            "exe_name": str(item.get("exe_name", "")).strip(),
            "class_name": str(item.get("class_name", "")).strip(),
        })
    return result


def rule_from_info(info) -> dict | None:
    """从用户明确选中的标准主窗口生成精确规则。"""
    if info is None or not winlib.automation_eligible(info):
        return None
    return {
        "exe_path": info.exe_path,
        "exe_name": info.exe_name,
        "class_name": info.class_name,
    }


def add_rule(config, info) -> bool:
    """添加精确规则；旧 exe 名单始终不参与匹配。"""
    rule = rule_from_info(info)
    if rule is None:
        return False

    rules = valid_rules(config.get("remember_rules", []))
    key = rule_key(rule)
    if key in {rule_key(item) for item in rules}:
        return False
    rules.append(rule)
    config.set("remember_rules", rules)
    return True


class RememberManager(QObject):
    rules_changed = Signal()

    def __init__(self, config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        # ctypes 回调必须由 Python 对象持有，否则回收后会导致进程崩溃。
        self._proc = W.WINEVENTPROC(self._on_event)
        self._hook = None
        # pending 保存同一 HWND 当前最晚的阶段；SHOW 可以覆盖尚未处理的 CREATE。
        self._pending: dict[int, int] = {}
        self._handled: set[int] = set()
        self.sync()

    def sync(self) -> None:
        """按总开关和有效规则装卸事件钩子。"""
        wanted = (
            bool(self.config.get("remember_centered", True))
            and bool(valid_rules(self.config.get("remember_rules", [])))
        )
        if wanted and self._hook is None:
            self._hook = W.user32.SetWinEventHook(
                EVENT_OBJECT_CREATE,
                EVENT_OBJECT_SHOW,
                None,
                self._proc,
                0,
                0,
                WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
            )
        elif not wanted and self._hook is not None:
            W.user32.UnhookWinEvent(self._hook)
            self._hook = None
        if not wanted:
            self._pending.clear()
            self._handled.clear()

    def record(self, info) -> None:
        """按独立开关把一次手动单窗口操作收录为精确规则。"""
        if not self.config.get("remember_after_manual_center", False):
            return
        if add_rule(self.config, info):
            self.rules_changed.emit()
            self.sync()

    def _on_event(self, _hook, event, hwnd, id_object, id_child,
                  _thread, _time_ms) -> None:
        # 全局事件回调只做排队，所有检查和移动都回到 Qt 事件循环执行。
        try:
            if id_object != OBJID_WINDOW or id_child != 0 or not hwnd:
                return
            hwnd = int(hwnd)
            if event == EVENT_OBJECT_DESTROY:
                self._pending.pop(hwnd, None)
                self._handled.discard(hwnd)
                return
            if event not in (EVENT_OBJECT_CREATE, EVENT_OBJECT_SHOW):
                return
            if hwnd in self._handled:
                return
            if hwnd in self._pending:
                if event == EVENT_OBJECT_SHOW:
                    self._pending[hwnd] = event
                return
            self._pending[hwnd] = event
            QTimer.singleShot(0, lambda h=hwnd: self._apply(h))
        except Exception:
            pass

    def _apply(self, hwnd: int) -> None:
        event = self._pending.pop(hwnd, None)
        if event is None or hwnd in self._handled:
            return
        shown = event == EVENT_OBJECT_SHOW
        try:
            info = winlib.inspect(
                hwnd,
                allow_own=False,
                require_visible=shown,
                require_title=False,
            )
            if info is None or not winlib.automation_eligible(info):
                if shown:
                    self._handled.add(hwnd)
                return
            if not self._matches(info):
                if shown:
                    self._handled.add(hwnd)
                return

            ok, _ = winlib.center(
                info,
                self.config.get("pixel_perfect", True),
            )
            # CREATE 失败时给 SHOW 一次兜底机会；SHOW 后无论成功与否都不重试。
            if ok or shown:
                self._handled.add(hwnd)
        except Exception:
            if shown:
                self._handled.add(hwnd)

    def _matches(self, info) -> bool:
        if winlib._ignored(info, self.config.get("ignore_list", [])):
            return False
        target = (
            winlib.normalized_exe_path(info.exe_path),
            info.class_name.strip().casefold(),
        )
        return target in {
            rule_key(rule)
            for rule in valid_rules(self.config.get("remember_rules", []))
        }
