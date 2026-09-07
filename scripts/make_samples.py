#!/usr/bin/env python3
"""make_samples.py: regenerate samples/ and the repo logo with Pillow only.

    python scripts/make_samples.py

Writes:
  samples/clean_300dpi.png      printed paragraph, black on white, ~46 px cap height (300 DPI equivalent)
  samples/noisy_skewed.png      same text, gray paper, 3 degree skew, gaussian noise, slight blur
  samples/screenshot_ui.png     small anti-aliased UI text at 96 DPI (the case Tesseract fails without upscaling)
  samples/ground_truth.txt      transcript for the first two
  samples/ground_truth_ui.txt   transcript for the screenshot
  OCR-Master-Guide.png          logo (transparent, teal)
"""
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "samples")
os.makedirs(S, exist_ok=True)

TEAL, TEAL_DARK, TEAL_LIGHT = (20, 184, 166), (15, 118, 110), (45, 212, 191)

GT = """OCR Master Guide sample page 01
The quick brown fox jumps over the lazy dog. 0123456789
Invoice INV-2026-0907 total: $1,234.56 due 2026-10-01
Serial A7F3-9K2Q-X0LM checksum 0x1F2E3D4C
Tesseract, PaddleOCR, RapidOCR, Surya, olmOCR, OneOCR
Line six ends here; measure CER, not vibes."""

GT_UI = """Settings - Optical character recognition
Language: English (United States)
[ ] Enable table mode    [x] Copy to clipboard
Status: 12 files processed, 0 errors, 3.4 s"""


def font(candidates, size):
    for c in candidates:
        for base in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
                     "/usr/share/fonts/TTF", "/System/Library/Fonts", "/Library/Fonts"):
            p = os.path.join(base, c)
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except OSError:
                    pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


SERIF = ["times.ttf", "georgia.ttf", "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"]
SANS = ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
MONO_BOLD = ["CascadiaCode.ttf", "consolab.ttf", "DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf"]
MONO = ["CascadiaMono.ttf", "consola.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"]


def render_page(text, f, size=(1650, 720), margin=90, spacing=22, fg=(0, 0, 0), bg=(255, 255, 255)):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    d.multiline_text((margin, margin), text, font=f, fill=fg, spacing=spacing)
    return img


def clean():
    f = font(SERIF, 44)
    img = render_page(GT, f)
    img.save(os.path.join(S, "clean_300dpi.png"), dpi=(300, 300))


def noisy(seed=7):
    random.seed(seed)
    f = font(SERIF, 44)
    img = render_page(GT, f, fg=(40, 40, 40), bg=(228, 226, 220))
    img = img.rotate(3.0, resample=Image.BICUBIC, expand=True, fillcolor=(228, 226, 220))
    px = img.load()
    w, h = img.size
    for _ in range(int(w * h * 0.06)):
        x, y = random.randrange(w), random.randrange(h)
        r, g, b = px[x, y]
        n = random.randint(-45, 45)
        px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    # shadow band down the left, like a phone photo near a spine
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(0, 220, 4):
        d.rectangle([i, 0, i + 4, h], fill=(0, 0, 0, max(0, 70 - i // 3)))
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    img.save(os.path.join(S, "noisy_skewed.png"), dpi=(200, 200))


def screenshot():
    f = font(SANS, 13)
    fb = font(SANS, 12)
    img = Image.new("RGB", (640, 200), (243, 243, 243))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 640, 30], fill=(32, 32, 32))
    d.text((10, 8), "Settings - Optical character recognition", font=f, fill=(255, 255, 255))
    d.text((12, 48), "Language: English (United States)", font=f, fill=(20, 20, 20))
    d.rectangle([12, 78, 24, 90], outline=(90, 90, 90))
    d.text((32, 76), "Enable table mode", font=f, fill=(20, 20, 20))
    d.rectangle([196, 78, 208, 90], outline=(90, 90, 90), fill=(15, 118, 110))
    d.text((199, 74), "x", font=fb, fill=(255, 255, 255))
    d.text((216, 76), "Copy to clipboard", font=f, fill=(20, 20, 20))
    d.text((12, 110), "Status: 12 files processed, 0 errors, 3.4 s", font=f, fill=(20, 20, 20))
    d.rectangle([12, 150, 120, 180], fill=(15, 118, 110))
    d.text((40, 158), "Extract", font=f, fill=(255, 255, 255))
    d.rectangle([130, 150, 238, 180], outline=(120, 120, 120))
    d.text((160, 158), "Cancel", font=f, fill=(20, 20, 20))
    img.save(os.path.join(S, "screenshot_ui.png"), dpi=(96, 96))


def logo():
    W, H = 1200, 420
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    big = font(MONO_BOLD, 210)
    small = font(MONO, 54)
    # scan-frame corner brackets
    L = 44
    for (x, y, sx, sy) in ((30, 30, 1, 1), (W - 30, 30, -1, 1), (30, H - 30, 1, -1), (W - 30, H - 30, -1, -1)):
        d.line([(x, y), (x + sx * L, y)], fill=TEAL, width=8)
        d.line([(x, y), (x, y + sy * L)], fill=TEAL, width=8)
    d.text((W / 2, 150), "OCR", font=big, fill=TEAL_DARK, anchor="mm")
    d.text((W / 2, 300), "MASTER GUIDE", font=small, fill=TEAL, anchor="mm")
    # scan line
    d.line([(120, 236), (W - 120, 236)], fill=TEAL_LIGHT + (150,), width=3)
    img.save(os.path.join(ROOT, "OCR-Master-Guide.png"))


def main():
    open(os.path.join(S, "ground_truth.txt"), "w", encoding="utf-8", newline="\n").write(GT + "\n")
    open(os.path.join(S, "ground_truth_ui.txt"), "w", encoding="utf-8", newline="\n").write(GT_UI + "\n")
    clean(); noisy(); screenshot(); logo()
    for f in sorted(os.listdir(S)):
        print("samples/" + f)
    print("OCR-Master-Guide.png")


if __name__ == "__main__":
    main()
