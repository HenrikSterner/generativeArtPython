"""Små, rene funktioner til pixelmål og fysisk trykstørrelse."""

from atelier.core import MAX_PIXELS, MAX_SIDE

SIZE_PRESETS = {
    "Bred · 1600 × 900": (1600, 900),
    "Kvadrat · 800 × 800": (800, 800),
    "Full HD · 1920 × 1080": (1920, 1080),
    "Stort kvadrat · 2400 × 2400": (2400, 2400),
    "Chapter-art · 2480 × 1110": (2480, 1110),
    "Chapter-art stor · 3000 × 1343": (3000, 1343),
    "A4 stående · 2480 × 3508": (2480, 3508),
    "A4 liggende · 3508 × 2480": (3508, 2480),
}


def pixels_to_cm(pixels, dpi):
    return pixels / dpi * 2.54


def cm_to_pixels(cm, dpi):
    return round(cm / 2.54 * dpi)


def checked_dimensions(width, height):
    if not 64 <= width <= MAX_SIDE or not 64 <= height <= MAX_SIDE:
        raise ValueError("Hver side skal være mellem 64 og 8000 pixels.")
    if width * height > MAX_PIXELS:
        raise ValueError("Billedet må højst indeholde 24 millioner pixels.")
    return width, height
