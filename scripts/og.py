"""Imágenes para redes sociales (og:image, 1200x630) con el diseño de la marca."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import ROOT

W, H = 1200, 630
BG = (9, 6, 25)
FONTS = ROOT / "scripts" / "fonts"
GRAD = [(225, 92, 150), (192, 114, 231), (124, 145, 235), (60, 174, 234)]


def _grad(t):
    t = max(0.0, min(1.0, t)) * (len(GRAD) - 1)
    i = min(int(t), len(GRAD) - 2)
    a, b, f = GRAD[i], GRAD[i + 1], t - i
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def _wrap(draw, text, font, max_w):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > max_w:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def make_og(title, kicker, out):
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse((-260, -320, 560, 420), fill=(90, 28, 88))
    d.ellipse((760, 260, 1500, 1000), fill=(20, 60, 110))
    img = glow.filter(ImageFilter.GaussianBlur(150))
    draw = ImageDraw.Draw(img)

    logo = Image.open(ROOT / "static" / "img" / "logo.png").convert("RGBA")
    lw = 74
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(logo, (80, 60), logo)
    draw.text((80 + lw + 20, 60 + logo.height // 2), "EFECTO PODCAST",
              font=ImageFont.truetype(str(FONTS / "InterDisplay-Bold.otf"), 30), fill=(255, 255, 255), anchor="lm")

    kicker_font = ImageFont.truetype(str(FONTS / "InterDisplay-Bold.otf"), 26)
    draw.text((80, 190), kicker.upper(), font=kicker_font, fill=(213, 141, 243))

    for size in range(76, 38, -4):
        font = ImageFont.truetype(str(FONTS / "InterDisplay-Black.otf"), size)
        lines = _wrap(draw, title, font, W - 160)
        if len(lines) <= 4 and len(lines) * size * 1.12 <= 300:
            break
    y = 236
    for line in lines:
        draw.text((80, y), line, font=font, fill=(255, 255, 255))
        y += int(size * 1.12)
    for i in range(240):
        draw.line([(80 + i, H - 70), (80 + i, H - 62)], fill=_grad(i / 239))
    draw.text((W - 80, H - 66), "efectopodcast.com", font=kicker_font, fill=(169, 164, 199), anchor="rm")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=88)
