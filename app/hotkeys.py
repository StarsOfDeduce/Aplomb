"""全局快捷键：RegisterHotKey + Qt 原生事件过滤。

用 RegisterHotKey 而不是键盘钩子，是因为它零轮询、零额外线程，
系统直接把按键消息投递到我们的隐藏窗口，空闲时 CPU 占用是 0。
"""

from __future__ import annotations

import ctypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from . import win32api as W

MODIFIER_ORDER = ("Ctrl", "Alt", "Shift", "Win")

_MOD_BITS = {
    "Ctrl": W.MOD_CONTROL,
    "Alt": W.MOD_ALT,
    "Shift": W.MOD_SHIFT,
    "Win": W.MOD_WIN,
}

_NAMED_KEYS = {
    "Space": 0x20, "Tab": 0x09, "Enter": 0x0D, "Backspace": 0x08,
    "Insert": 0x2D, "Delete": 0x2E, "Home": 0x24, "End": 0x23,
    "PageUp": 0x21, "PageDown": 0x22,
    "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28,
    "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
    "\\": 0xDC, ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
}

_VK_NAMES = {v: k for k, v in _NAMED_KEYS.items()}


def parse_hotkey(spec: str) -> tuple[int, int] | None:
    """'Ctrl+Alt+C' -> (modifiers, vk)；无法解析返回 None。"""
    if not spec:
        return None
    parts = [p.strip() for p in spec.replace(" ", "").split("+") if p.strip()]
    if len(parts) < 2:
        return None

    mods = 0
    key = ""
    for part in parts:
        low = part.lower()
        if low in ("ctrl", "control"):
            mods |= W.MOD_CONTROL
        elif low == "alt":
            mods |= W.MOD_ALT
        elif low == "shift":
            mods |= W.MOD_SHIFT
        elif low in ("win", "meta", "super"):
            mods |= W.MOD_WIN
        else:
            key = part

    if not key or mods == 0:
        return None
    # 只有 Shift 的组合会抢占正常打字，不接受
    if not mods & (W.MOD_CONTROL | W.MOD_ALT | W.MOD_WIN):
        return None

    if len(key) == 1:
        ch = key.upper()
        if ch.isalnum():
            return mods, ord(ch)
        vk = _NAMED_KEYS.get(key)
        return (mods, vk) if vk else None

    upper = key.upper()
    if upper.startswith("F") and upper[1:].isdigit():
        num = int(upper[1:])
        if 1 <= num <= 24:
            return mods, 0x70 + num - 1

    for name, code in _NAMED_KEYS.items():
        if name.upper() == upper:
            return mods, code

    return None


def format_hotkey(mods: int, vk: int) -> str:
    """(modifiers, vk) -> 'Ctrl+Alt+C'。"""
    parts = [name for name in MODIFIER_ORDER if mods & _MOD_BITS[name]]
    if not parts:
        return ""
    if 0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39:
        parts.append(chr(vk))
    elif 0x70 <= vk <= 0x87:
        parts.append(f"F{vk - 0x70 + 1}")
    else:
        parts.append(_VK_NAMES.get(vk, ""))
    if not parts[-1]:
        return ""
    return "+".join(parts)


class HotkeyManager(QObject, QAbstractNativeEventFilter):
    triggered = Signal(str)

    def __init__(self, hwnd_provider, parent: QObject | None = None) -> None:
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._hwnd = hwnd_provider
        self._registered: dict[int, str] = {}
        self._next_id = 1
        self._specs: dict[str, str] = {}
        self._last: tuple[int, int] | None = None

    # ------------------------------------------------------------------ #
    def register(self, action: str, spec: str) -> bool:
        """注册一个快捷键。同名 action 会被替换。"""
        self.unregister(action)
        parsed = parse_hotkey(spec)
        if parsed is None:
            return False
        mods, vk = parsed
        hotkey_id = self._next_id
        self._next_id += 1
        if not W.user32.RegisterHotKey(self._hwnd, hotkey_id, mods | W.MOD_NOREPEAT, vk):
            return False
        self._registered[hotkey_id] = action
        self._specs[action] = spec
        return True

    def unregister(self, action: str) -> None:
        for hotkey_id, name in list(self._registered.items()):
            if name == action:
                W.user32.UnregisterHotKey(self._hwnd, hotkey_id)
                del self._registered[hotkey_id]
                self._specs.pop(action, None)

    def unregister_all(self) -> None:
        for hotkey_id in list(self._registered):
            W.user32.UnregisterHotKey(self._hwnd, hotkey_id)
        self._registered.clear()
        self._specs.clear()

    def is_registered(self, action: str) -> bool:
        return action in self._specs

    # ------------------------------------------------------------------ #
    def nativeEventFilter(self, event_type, message):
        try:
            # 只认 windows_generic_MSG。同一条 WM_HOTKEY 也会以
            # windows_dispatcher_MSG 再送一遍，两边都处理就会触发两次，
            # 表现为"浮层刚打开就被自己关掉"。
            if bytes(event_type) != b"windows_generic_MSG":
                return False, 0

            msg = ctypes.cast(int(message), ctypes.POINTER(W.MSG)).contents
            if msg.message != W.WM_HOTKEY:
                return False, 0

            # 同一条消息可能被回调多次，用 (id, 时间戳) 去重
            stamp = (int(msg.wParam), int(msg.time))
            if stamp == self._last:
                return False, 0
            self._last = stamp

            action = self._registered.get(int(msg.wParam))
            if action:
                self.triggered.emit(action)
        except Exception:
            pass
        return False, 0
