"""配置持久化：一个 JSON 文件，原子写入，不做多余的事。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_DIR_NAME = "Aplomb"
PORTABLE_MARKER = "portable.txt"

DEFAULTS: dict = {
    # 新安装默认不占用任何全局快捷键，由用户按需启用
    "hotkey_center_current": "",
    "hotkey_center_select": "",
    "hotkey_center_all": "",
    "autostart": False,
    "show_notifications": True,
    "pixel_perfect": True,
    "theme": "system",          # system | dark | light
    "picker_thumbnails": True,
    "ignore_list": [],
}


def install_dir() -> Path:
    """程序所在目录（打包后是 exe 所在目录）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def is_portable() -> bool:
    """便携版：exe 旁边有 portable.txt，配置就写在同目录的 data 里。"""
    return (install_dir() / PORTABLE_MARKER).exists()


def config_dir() -> Path:
    if is_portable():
        return install_dir() / "data"
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_DIR_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


class Config:
    def __init__(self) -> None:
        self.path = config_path()
        self._data: dict = dict(DEFAULTS)
        self._first_run = not self.path.exists()
        self.load()
        if self._first_run:
            # 立刻落盘，否则"首次运行"状态会一直保持，每次启动都弹设置
            self.save()

    # ------------------------------------------------------------------ #
    @property
    def first_run(self) -> bool:
        return self._first_run

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, default in DEFAULTS.items():
                    value = raw.get(key, default)
                    # 类型兜底，避免手改配置把程序带崩
                    if isinstance(default, list) and not isinstance(value, list):
                        value = default
                    if isinstance(default, bool) and not isinstance(value, bool):
                        value = default
                    self._data[key] = value
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            # 配置损坏就退回默认值，不影响启动
            self._data = dict(DEFAULTS)

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, self.path)
        except OSError:
            pass

    # ------------------------------------------------------------------ #
    def get(self, key: str, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value, save: bool = True) -> None:
        if self._data.get(key) == value:
            return
        self._data[key] = value
        if save:
            self.save()

    def update(self, values: dict) -> None:
        self._data.update(values)
        self.save()

    def reset_hotkeys(self) -> None:
        for key in ("hotkey_center_current", "hotkey_center_select", "hotkey_center_all"):
            self._data[key] = DEFAULTS[key]
        self.save()

    def reset(self) -> None:
        self._data = dict(DEFAULTS)
        self.save()


def system_prefers_dark() -> bool:
    """读注册表判断系统是深色还是浅色。失败时按深色处理。"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return int(value) == 0
    except OSError:
        return True
