"""生成安装程序用的位图：欢迎页图 + 页眉图。

NSIS 的 MUI2 只认 BMP，所以这里用 Qt 渲染再交给 PIL 存成 24 位 BMP。
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

OUT = BASE / "installer"
FONTS = Path("C:/Windows/Fonts")
ICON_PNG = BASE / "assets" / "aplomb.png"

BG = (23, 23, 25)
TEXT = (241, 242, 244)
DIM = (141, 143, 152)
ACCENT = (61, 125, 246)
WHITE = (255, 255, 255)
INK = (16, 22, 32)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def icon_image(size: int) -> Image.Image:
    return Image.open(ICON_PNG).convert("RGBA").resize((size, size), Image.LANCZOS)


def welcome_bitmap(path: Path) -> None:
    width, height = 164, 314
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    icon = icon_image(64)
    image.paste(icon, (22, 30), icon)

    draw.text((22, 112), "Aplomb", font=font("seguisb.ttf", 24), fill=TEXT)
    draw.text((23, 146), "从 容", font=font("msyh.ttc", 13), fill=DIM)

    draw.line([(22, 178), (74, 178)], fill=ACCENT, width=2)

    draw.text((22, 196), "把窗口摆正，", font=font("msyh.ttc", 12), fill=DIM)
    draw.text((22, 216), "仅此而已。", font=font("msyh.ttc", 12), fill=DIM)

    draw.text((22, 276), "v1.0.0", font=font("segoeui.ttf", 9), fill=(94, 96, 104))

    image.save(path, "BMP")


def header_bitmap(path: Path) -> None:
    width, height = 150, 57
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)

    icon = icon_image(30)
    image.paste(icon, (10, 14), icon)

    draw.text((48, 18), "APLOMB", font=font("seguisb.ttf", 13), fill=INK)
    draw.text((49, 35), "窗口居中", font=font("msyh.ttc", 8), fill=(140, 146, 158))

    image.save(path, "BMP")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    welcome_bitmap(OUT / "welcome.bmp")
    header_bitmap(OUT / "header.bmp")
    print("安装素材已生成:", OUT / "welcome.bmp", OUT / "header.bmp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
