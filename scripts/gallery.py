"""Lav kontaktark til visuel kontrol af samtlige presets og kapitler."""

import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw, ImageFont

from atelier.catalog import GENERATORS, preset_config
from atelier.core import render
from atelier.education import CHAPTERS, chapter_config


def contact_sheet(items, destination):
    width, height = 360, 270
    columns = 3
    sheet = Image.new("RGB", (columns * width, ((len(items) + columns - 1) // columns) * height), "#eeece4")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for index, (label, config) in enumerate(items):
        config.update(width=700, height=460)
        picture = Image.open(io.BytesIO(render(config, max_side=350))).convert("RGB")
        x, y = (index % columns) * width, (index // columns) * height
        sheet.paste(picture, (x + 5, y + 5))
        draw.text((x + 8, y + 241), label, fill="#262f2d", font=font)
    sheet.save(destination)


if __name__ == "__main__":
    folder = Path("artifacts")
    folder.mkdir(exist_ok=True)
    items = [(f"{generator} / {name}", preset_config(generator, name))
             for generator, values in GENERATORS.items() for name in values["presets"]]
    for index in range(0, len(items), 12):
        contact_sheet(items[index:index + 12], folder / f"presets-{index // 12 + 1}.png")
    chapters = [(f"{number:02d} / {values[0]}", chapter_config(number)) for number, values in CHAPTERS.items()]
    contact_sheet(chapters[:9], folder / "chapters-1.png")
    contact_sheet(chapters[9:], folder / "chapters-2.png")
    print("Kontaktark gemt i artifacts/.")
