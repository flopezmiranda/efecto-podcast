"""Genera las miniaturas de YouTube de la temporada 1 (1280x720, solo tipografía y marca).

Cada texto marca entre [corchetes] la palabra que va destacada en amarillo, como en la temporada 2.

    python scripts/miniaturas.py      # deja los JPG en content/miniaturas/
"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from common import ROOT

FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_SMALL = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
W, H = 1280, 720
BG = (9, 6, 25)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 10)
MUTED = (169, 164, 199)
GRAD = [(225, 92, 150), (192, 114, 231), (124, 145, 235), (60, 174, 234)]

EPISODES = [
    ("wYvn_DWpl18", 1, "HACKEANDO LA MÚSICA CON [IA]"),
    ("4cBSKxJolHc", 2, "DE LA PERSEVERANCIA A [MARTE]"),
    ("p79_GEB515o", 3, "¿UN CHIP EN TU [CEREBRO]?"),
    ("YbI-3aQ7OR8", 4, "NO MÁS [VENTA DE HUMO] EN MARKETING"),
    ("n8LxYjIbUCA", 5, "LANZA TU [MVP] HOY MISMO"),
    ("fCGOkxt7zlU", 6, "EL GOL DE [MESSI] QUE CAMBIÓ UN NEGOCIO"),
    ("j08Vcm6XAFY", 7, "5 TIPS PARA SER MÁS [PRODUCTIVO]"),
    ("V4BEdzMjixk", 8, "LOS 7 SECRETOS DE [FACEBOOK]"),
    ("bXWRxUJOy70", 9, "[FALABELLA] SE ENAMORÓ DE UNA MALA IDEA"),
    ("QkoM659gN1Q", 10, "¿ESTAMOS LISTOS PARA TANTA [TECNOLOGÍA]?"),
    ("mwaXlEqnlzQ", 11, "NO TODO ES [SABER]"),
    ("NF46uDl243M", 12, "¡CRINGE! QUE NO TE FRENE EL [QUÉ DIRÁN]"),
]


def gradient_color(t):
    t = max(0.0, min(1.0, t)) * (len(GRAD) - 1)
    i = min(int(t), len(GRAD) - 2)
    a, b, f = GRAD[i], GRAD[i + 1], t - i
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def background():
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse((-300, -350, 650, 450), fill=(70, 22, 70))     # rosado arriba a la izquierda
    d.ellipse((800, 330, 1650, 1050), fill=(18, 52, 95))     # celeste abajo a la derecha
    return Image.blend(img, glow.filter(ImageFilter.GaussianBlur(170)), 1.0)


def tokens(text):
    """Separa el texto en palabras, marcando las que van entre corchetes."""
    out, hl = [], False
    for word in text.split():
        start, end = word.startswith("["), "]" in word
        hl = hl or start
        out.append((word.replace("[", "").replace("]", ""), hl))
        if end:
            hl = False
    return out


def layout(words, font, max_w, draw):
    lines, line = [], []
    for w in words:
        trial = line + [w]
        if line and draw.textlength(" ".join(x for x, _ in trial), font=font) > max_w:
            lines.append(line)
            line = [w]
        else:
            line = trial
    return lines + [line]


def render(vid, number, text, logo):
    img = background()
    draw = ImageDraw.Draw(img)
    words = tokens(text)
    max_w, x = 1100, 90
    for size in range(150, 60, -4):
        font = ImageFont.truetype(FONT, size)
        lines = layout(words, font, max_w, draw)
        widest = max(draw.textlength(w, font=font) for w, _ in words)
        if len(lines) <= 3 and widest <= max_w:
            break
    line_h = int(size * 1.08)
    block_h = line_h * len(lines)
    y = (H - block_h) // 2 + 20
    for line in lines:
        cx = x
        for word, hl in line:
            draw.text((cx, y), word, font=font, fill=YELLOW if hl else WHITE)
            cx += draw.textlength(word + " ", font=font)
        y += line_h

    # Barra con el degradado de la marca bajo el texto.
    bar_y = y + 18
    for i in range(260):
        draw.line([(x + i, bar_y), (x + i, bar_y + 9)], fill=gradient_color(i / 259))

    # Logo original (sin efectos) y nombre arriba a la izquierda.
    lw = 92
    lg = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(lg, (x, 52), lg)
    small = ImageFont.truetype(FONT_SMALL, 34)
    draw.text((x + lw + 22, 52 + lg.height // 2), "EFECTO PODCAST", font=small, fill=WHITE, anchor="lm")
    tag = ImageFont.truetype(FONT_SMALL, 30)
    draw.text((W - 70, 52 + lg.height // 2), f"T1 · EP {number}", font=tag, fill=MUTED, anchor="rm")

    out = ROOT / "content" / "miniaturas" / f"E{number}T1-{vid}.jpg"
    img.save(out, "JPEG", quality=92)
    return out


def main():
    logo = Image.open(ROOT / "static" / "img" / "logo.png").convert("RGBA")
    for vid, number, text in EPISODES:
        print(render(vid, number, text, logo).name)


if __name__ == "__main__":
    main()
