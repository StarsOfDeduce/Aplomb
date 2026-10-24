"""居中记忆。

用户居中过的程序记进配置；这些程序的新窗口出现时自动再居中。
全程事件驱动、空闲零轮询：名单为空或开关关闭时连钩子都不装。

速度设计（"无感居中"）：
- 显示后 ~80ms 完成第一次居中（低于人眼对新窗口位置的感知阈值）；
- 随后短暂跟踪该窗口（默认 ~2.2s）：应用常在显示后才恢复自己保存的
  位置、盖掉居中，这里监听 LOCATIONCHANGE，被挪动就立刻拉回来
  （合并抖动、限次，防止和应用打架）；
- 用户一旦手动拖动该窗口（MOVESIZESTART），立即停止跟踪 ——
  人的意图永远优先。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer

from . import win32api as W
from . import windows as winlib
from .win32api import (EVENT_OBJECT_SHOW, EVENT_OBJECT_LOCATIONCHANGE,
                       EVENT_SYSTEM_MOVESIZESTART, OBJID_WINDOW,
                       WINEVENT_OUTOFCONTEXT)

FIRST_DELAY_MS = 80        # 显示后多少毫秒完成第一次居中
TRACK_WINDOW_MS = 2200     # 显示后跟踪多久（覆盖应用的"迟到"恢复逻辑）
COALESCE_MS = 40           # 连串移动事件合并成一拍再纠正
MAX_CORRECTIONS = 4        # 一个窗口最多纠正几次（防和应用互相打架）
TOLERANCE_PX = 2           # 偏差多少像素以内视为"没动过"


class _Track:
    """一个被跟踪窗口的状态。"""

    __slots__ = ("set_pos", "corrections", "coalescing", "expire_timer")

    def __init__(self) -> None:
        self.set_pos: tuple[int, int] | None = None
        self.corrections = 0
        self.coalescing = False
        self.expire_timer: QTimer | None = None


class RememberManager(QObject):
    def __init__(self, config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        # 必须持住回调引用，否则 ctypes 回调被垃圾回收后进程直接崩溃
        self._proc = W.WINEVENTPROC(self._on_event)
        self._show_hook = None
        self._track_hooks: list = []
        # 居中结果的记录：hwnd -> (left, top)；也是"在处理中"的标记
        self._pending: set[int] = set()
        # 正在跟踪的窗口：hwnd -> _Track
        self._tracks: dict[int, _Track] = {}
        self.sync()

    # ------------------------------------------------------------------ #
    def sync(self) -> None:
        """按当前配置装/卸事件钩子。"""
        wanted = (
            bool(self.config.get("remember_centered", True))
            and bool(self.config.get("remembered_apps", []))
        )
        if wanted and self._show_hook is None:
            self._show_hook = W.user32.SetWinEventHook(
                EVENT_OBJECT_SHOW, EVENT_OBJECT_SHOW, None,
                self._proc, 0, 0, WINEVENT_OUTOFCONTEXT,
            )
        elif not wanted and self._show_hook is not None:
            W.user32.UnhookWinEvent(self._show_hook)
            self._show_hook = None
        if not wanted:
            for hwnd in list(self._tracks):
                self._stop_tracking(hwnd)

    def record(self, info) -> None:
        """居中成功后调用：把这个程序记进名单（大小写不敏感去重）。"""
        if not self.config.get("remember_centered", True):
            return
        name = getattr(info, "exe_name", "")
        if not name:
            return
        apps = [str(a) for a in self.config.get("remembered_apps", [])]
        if name.lower() not in {a.lower() for a in apps}:
            apps.append(name)
            self.config.set("remembered_apps", apps)
        self.sync()

    # ------------------------------------------------------------------ #
    def _on_event(self, _hook, event, hwnd, id_object, id_child,
                  _thread, _time_ms) -> None:
        # 钩子回调里必须快进快出、绝不抛异常
        try:
            if id_object != OBJID_WINDOW or id_child != 0 or not hwnd:
                return
            hwnd = int(hwnd)
            if event == EVENT_OBJECT_SHOW:
                if hwnd in self._tracks or hwnd in self._pending:
                    return
                if not W.user32.IsWindowVisible(hwnd):
                    return
                self._pending.add(hwnd)
                QTimer.singleShot(FIRST_DELAY_MS, lambda h=hwnd: self._apply(h))
            elif event == EVENT_SYSTEM_MOVESIZESTART:
                # 用户正在手动拖动/调整这个窗口：立刻放手，尊重用户
                if hwnd in self._tracks:
                    self._stop_tracking(hwnd)
            elif event == EVENT_OBJECT_LOCATIONCHANGE:
                track = self._tracks.get(hwnd)
                if track is None or track.coalescing or track.set_pos is None:
                    return
                current = W.get_window_rect(hwnd)
                if current is None:
                    return
                if (abs(current.left - track.set_pos[0]) <= TOLERANCE_PX
                        and abs(current.top - track.set_pos[1]) <= TOLERANCE_PX):
                    return  # 位置还是我们设的（含自己移动产生的事件回声）
                track.coalescing = True
                QTimer.singleShot(COALESCE_MS, lambda h=hwnd: self._correct(h))
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    def _apply(self, hwnd: int) -> None:
        """第一次居中 + 开始跟踪。"""
        try:
            self._apply_inner(hwnd)
        except Exception:
            self._pending.discard(hwnd)
            self._stop_tracking(hwnd)

    def _apply_inner(self, hwnd: int) -> None:
        self._pending.discard(hwnd)
        info = winlib.inspect(hwnd, allow_own=True)
        if info is None or not self._remembered(info):
            return
        # restore=False：自动居中绝不唤醒最小化窗口，只设还原落点
        ok, _ = winlib.center(
            info, self.config.get("pixel_perfect", True), restore=False
        )
        if not ok:
            return
        rect = W.get_window_rect(hwnd)
        track = _Track()
        track.set_pos = (rect.left, rect.top) if rect else None
        self._tracks[hwnd] = track
        self._install_track_hooks()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda h=hwnd: self._stop_tracking(h))
        timer.start(TRACK_WINDOW_MS)
        track.expire_timer = timer

    def _correct(self, hwnd: int) -> None:
        """应用自己挪动了窗口：拉回正中（限次）。"""
        track = self._tracks.get(hwnd)
        if track is None:
            return
        track.coalescing = False
        if track.corrections >= MAX_CORRECTIONS:
            self._stop_tracking(hwnd)
            return
        info = winlib.inspect(hwnd, allow_own=True)
        if info is None or not self._remembered(info):
            self._stop_tracking(hwnd)
            return
        # 用户拖动期间不抢；最小化则只更新还原落点
        winlib.center(info, self.config.get("pixel_perfect", True), restore=False)
        track.corrections += 1
        rect = W.get_window_rect(hwnd)
        if rect is not None:
            track.set_pos = (rect.left, rect.top)

    # ------------------------------------------------------------------ #
    def _install_track_hooks(self) -> None:
        if self._track_hooks:
            return
        for event in (EVENT_OBJECT_LOCATIONCHANGE, EVENT_SYSTEM_MOVESIZESTART):
            hook = W.user32.SetWinEventHook(
                event, event, None, self._proc, 0, 0, WINEVENT_OUTOFCONTEXT
            )
            if hook:
                self._track_hooks.append(hook)

    def _stop_tracking(self, hwnd: int) -> None:
        track = self._tracks.pop(hwnd, None)
        if track is not None and track.expire_timer is not None:
            track.expire_timer.stop()
            track.expire_timer.deleteLater()
        if not self._tracks:
            for hook in self._track_hooks:
                W.user32.UnhookWinEvent(hook)
            self._track_hooks.clear()

    def _remembered(self, info) -> bool:
        # 路径大小写每次枚举可能不同，忽略列表怎么比这里就怎么比
        apps = {str(a).lower() for a in self.config.get("remembered_apps", [])}
        if info.exe_name.lower() not in apps:
            return False
        return not winlib._ignored(info, self.config.get("ignore_list", []))
