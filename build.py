"""一键打包。

用法：
    python build.py            打包全部（exe + 便携包 + 安装包）
    python build.py exe        只打 exe
    python build.py portable   只做便携包（需要已有 exe）
    python build.py setup      只做安装包（需要已有 exe）
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
DIST = BASE / "dist"
ICON = ASSETS / "aplomb.ico"

sys.path.insert(0, str(BASE))
from app import __version__  # noqa: E402

EXCLUDES = [
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml", "PySide6.QtDBus",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtPrintSupport",
    "PySide6.QtSvg", "PySide6.QtSvgWidgets", "PySide6.QtUiTools", "PySide6.QtHelp",
    "PySide6.QtConcurrent", "PySide6.QtDesigner", "PySide6.QtSerialPort",
    "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "tkinter", "unittest", "pydoc", "doctest", "email", "http", "xmlrpc", "pdb",
]

PORTABLE_NOTE = """Aplomb · 从容 —— 便携版

这是一个绿色版，不需要安装：
直接双击 Aplomb.exe 即可运行，配置会写在同目录的 data\\ 文件夹里。

目录里的 portable.txt 是「便携模式」标记，删掉它就会改回把配置存到
%APPDATA%\\Aplomb。想让配置跟着 U 盘走，就把它留着。

快捷键默认留空，不会占用系统组合键。
请在「设置 → 快捷键」中按需设置；每项右侧的 × 可以清空快捷键。

程序常驻系统托盘，左键托盘图标打开设置，右键菜单里可以退出。
"""


def log(step: str, message: str) -> None:
    print(f"[{step}] {message}")


# --------------------------------------------------------------------------- #
def ensure_icon() -> None:
    if ICON.exists():
        return
    log("图标", "生成中…")
    subprocess.run([sys.executable, str(BASE / "tools" / "make_icon.py")], check=True)


def build_exe() -> Path:
    log("1/3", "PyInstaller 打包 exe…")
    # 上一版还在托盘里跑着的话，dist/Aplomb.exe 会被占用，PyInstaller 覆盖不了
    subprocess.run(["taskkill", "/F", "/IM", "Aplomb.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    shutil.rmtree(BASE / "build", ignore_errors=True)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--noconsole",
        "--name", "Aplomb",
        f"--icon={ICON}",
        f"--add-data={ASSETS}{os.pathsep}assets",
        "--hidden-import", "PySide6.QtCore",
        str(BASE / "main.py"),
    ]
    for module in EXCLUDES:
        cmd += ["--exclude-module", module]

    result = subprocess.run(cmd, cwd=str(BASE))
    if result.returncode != 0:
        raise SystemExit("打包失败")
    exe = DIST / "Aplomb.exe"
    log("1/3", f"完成：{exe.name} ({exe.stat().st_size / 1048576:.1f} MB)")
    return exe


def build_portable() -> Path:
    log("2/3", "组装便携版…")
    exe = DIST / "Aplomb.exe"
    if not exe.exists():
        raise SystemExit("找不到 dist/Aplomb.exe，先跑一次 build.py exe")

    folder = DIST / f"Aplomb-{__version__}-portable"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)

    shutil.copy2(exe, folder / "Aplomb.exe")
    shutil.copy2(ICON, folder / "aplomb.ico")
    (folder / "portable.txt").write_text(
        "Aplomb portable mode marker\n删除本文件即改回 %APPDATA%\\Aplomb\n", encoding="utf-8"
    )
    (folder / "使用说明.txt").write_text(PORTABLE_NOTE, encoding="utf-8")

    archive = DIST / f"Aplomb-{__version__}-portable.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(folder.iterdir()):
            zf.write(item, f"{folder.name}/{item.name}")

    log("2/3", f"完成：{archive.name} ({archive.stat().st_size / 1048576:.1f} MB)")
    return archive


def ensure_bom(path: Path) -> None:
    """NSIS 读 UTF-8 脚本必须带 BOM，否则中文会报 Bad text encoding。"""
    data = path.read_bytes()
    if not data.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(b"\xef\xbb\xbf" + data)


def build_setup() -> Path:
    log("3/3", "生成安装包…")
    makensis = Path(os.environ.get("NSIS_MAKENSIS", BASE / ".tools" / "nsis" / "makensis.exe"))
    if not makensis.exists():
        raise SystemExit(
            "找不到 makensis.exe。请把 NSIS 解压到 .tools/nsis/，"
            "或用环境变量 NSIS_MAKENSIS 指定路径。"
        )
    if not (DIST / "Aplomb.exe").exists():
        raise SystemExit("找不到 dist/Aplomb.exe，先跑一次 build.py exe")

    subprocess.run([sys.executable, str(BASE / "tools" / "make_installer_assets.py")], check=True)
    ensure_bom(BASE / "installer" / "Aplomb.nsi")
    subprocess.run(
        [str(makensis), f"/DAPP_VERSION={__version__}", "Aplomb.nsi"],
        cwd=str(BASE / "installer"),
        check=True,
    )
    setup = DIST / f"Aplomb-Setup-{__version__}.exe"
    if not setup.exists():
        raise SystemExit("安装包没有生成")
    log("3/3", f"完成：{setup.name} ({setup.stat().st_size / 1048576:.1f} MB)")
    return setup


# --------------------------------------------------------------------------- #
def main() -> int:
    if sys.platform != "win32":
        print("这个打包脚本只适用于 Windows")
        return 1

    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    ensure_icon()
    DIST.mkdir(exist_ok=True)

    if target in ("all", "exe"):
        build_exe()
    if target in ("all", "portable"):
        build_portable()
    if target in ("all", "setup"):
        build_setup()

    shutil.rmtree(BASE / "build", ignore_errors=True)
    (BASE / "Aplomb.spec").unlink(missing_ok=True)

    print("\n产物：")
    for item in sorted(DIST.iterdir()):
        size = item.stat().st_size / 1048576
        print(f"  {item.name:<34} {size:6.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
