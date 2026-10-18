"""由 design/icon_source.png 生成程序图标。

产物：
    assets/aplomb.ico   多尺寸 ICO（exe / 安装包 / 快捷方式用）
    assets/aplomb.png   256×256 透明 PNG（运行时加载用）

源图是透明底的纯平双色几何图形，这里只做裁剪、留白和高质量缩放。
设计源图放在 design/ 下，不随程序打包。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent.parent
ASSETS = BASE / "assets"
SOURCE = BASE / "design" / "icon_source.png"
SIZES = (256, 128, 64, 48, 40, 32, 24, 20, 16)
MARGIN = 0.045  # 四周留白比例，避免图形贴边


def load_master() -> Image.Image:
    image = Image.open(SOURCE).convert("RGBA")
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)

    # 裁成正方形并留白，保证各尺寸下重心一致
    side = max(image.size)
    canvas_side = int(round(side * (1 + MARGIN * 2)))
    canvas = Image.new("RGBA", (canvas_side, canvas_side), (0, 0, 0, 0))
    canvas.paste(
        image,
        ((canvas_side - image.width) // 2, (canvas_side - image.height) // 2),
        image,
    )
    return canvas


def main() -> int:
    if not SOURCE.exists():
        print("缺少源图:", SOURCE)
        return 1

    master = load_master()
    frames = {}
    for size in SIZES:
        frames[size] = master.resize((size, size), Image.LANCZOS)

    frames[256].save(ASSETS / "aplomb.png", format="PNG")
    frames[256].save(
        ASSETS / "aplomb.ico",
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=[frames[s] for s in SIZES if s != 256],
    )

    print("已生成:", ASSETS / "aplomb.ico", "|", ASSETS / "aplomb.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
