"""Genera las miniaturas de YouTube de la temporada 1 (1280x720), al estilo de la temporada 2:
foto del estudio a pantalla completa y la frase abajo, con la palabra clave en amarillo.

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
PHOTOS = ROOT / "content" / "miniaturas" / "fuente"
GRAD = [(225, 92, 150), (192, 114, 231), (124, 145, 235), (60, 174, 234)]

# (video, número, frase, foto, zoom). Cada foto se usa en dos o tres episodios con distinto encuadre.
EPISODES = [
    ("wYvn_DWpl18", 1, "HACKEANDO LA MÚSICA CON [IA]", "chaleco", 1.0),
    ("4cBSKxJolHc", 2, "DE LA PERSEVERANCIA A [MARTE]", "camisa-beige", 1.0),
    ("p79_GEB515o", 3, "¿UN CHIP EN TU [CEREBRO]?", "camisa-celeste", 1.0),
    ("YbI-3aQ7OR8", 4, "NO MÁS [VENTA DE HUMO] EN MARKETING", "polera-gris", 1.0),
    ("n8LxYjIbUCA", 5, "LANZA TU [MVP] HOY MISMO", "camisa-rayas", 1.0),
    ("fCGOkxt7zlU", 6, "EL GOL DE [MESSI] QUE CAMBIÓ UN NEGOCIO", "polera-gris", 1.3),
    ("j08Vcm6XAFY", 7, "5 TIPS PARA SER MÁS [PRODUCTIVO]", "camisa-beige", 1.3),
    ("V4BEdzMjixk", 8, "LOS 7 SECRETOS DE [FACEBOOK]", "chaleco", 1.3),
    ("bXWRxUJOy70", 9, "[FALABELLA] SE ENAMORÓ DE UNA MALA IDEA", "camisa-rayas", 1.3),
    ("QkoM659gN1Q", 10, "¿ESTAMOS LISTOS PARA TANTA [TECNOLOGÍA]?", "camisa-celeste", 1.3),
    ("mwaXlEqnlzQ", 11, "NO TODO ES [SABER]", "chaleco", 1.15),
    ("NF46uDl243M", 12, "¡CRINGE! QUE NO TE FRENE EL [QUÉ DIRÁN]", "polera-gris", 1.15),
]

# Posición de la cara en cada foto (fracción del ancho y del alto), para encuadrar.
FACES = {
    "chaleco": (0.394, 0.38),
    "camisa-beige": (0.388, 0.34),
    "polera-gris": (0.368, 0.34),
    "camisa-celeste": (0.389, 0.31),
    "camisa-rayas": (0.331, 0.30),
}


def gradient_color(t):
    t = max(0.0, min(1.0, t)) * (len(GRAD) - 1)
    i = min(int(t), len(GRAD) - 2)
    a, b, f = GRAD[i], GRAD[i + 1], t - i
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def photo_background(name, zoom):
    """Foto encuadrada en la cara, con el fondo difuminado y oscurecida abajo para el texto."""
    photo = Image.open(PHOTOS / f"felipe-{name}.jpg").convert("RGB")
    scale = max(W / photo.width, H / photo.height) * zoom
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS)
    fx, fy = FACES[name]
    left = min(max(0, round(fx * photo.width - 0.42 * W)), photo.width - W)
    # Con más zoom la cara baja un poco, para que la cabeza no choque con el logo.
    top = min(max(0, round(fy * photo.height - (0.38 + 0.15 * (zoom - 1)) * H)), photo.height - H)
    img = photo.crop((left, top, left + W, top + H))
    face = (fx * photo.width - left, fy * photo.height - top)

    # Difuminado: la persona queda nítida y el resto del estudio se suaviza.
    sharp = Image.new("L", (W, H), 0)
    rx, ry = 300 * zoom, 380 * zoom
    cx, cy = face[0], face[1] + 110 * zoom
    ImageDraw.Draw(sharp).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    sharp = sharp.filter(ImageFilter.GaussianBlur(110))
    img = Image.composite(img, img.filter(ImageFilter.GaussianBlur(14)), sharp)

    # Viñeta suave y degradado oscuro abajo.
    shade = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(shade)
    top_fade = int(H * 0.40)
    for yy in range(top_fade, H):
        d.line([(0, yy), (W, yy)], fill=min(235, int(255 * ((yy - top_fade) / (H - top_fade)) ** 0.8)))
    vignette = Image.new("L", (W, H), 150)
    ImageDraw.Draw(vignette).ellipse((-120, -160, W + 120, H + 60), fill=0)
    vignette = vignette.filter(ImageFilter.GaussianBlur(140))
    shade = Image.fromarray(__import__("numpy").maximum(__import__("numpy").array(shade), __import__("numpy").array(vignette)))
    return Image.composite(Image.new("RGB", (W, H), BG), img, shade)


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


def render(vid, number, text, photo, zoom, logo):
    img = photo_background(photo, zoom) if photo else background()
    draw = ImageDraw.Draw(img)
    words = tokens(text)
    max_w, x = 1120, 80
    for size in range(112, 50, -4):
        font = ImageFont.truetype(FONT, size)
        lines = layout(words, font, max_w, draw)
        widest = max(draw.textlength(w, font=font) for w, _ in words)
        if len(lines) <= 2 and widest <= max_w:
            break
    line_h = int(size * 1.06)
    stroke = max(4, size // 14)
    y = H - 62 - line_h * len(lines)
    for line in lines:
        cx = x
        for word, hl in line:
            draw.text((cx, y), word, font=font, fill=YELLOW if hl else WHITE,
                      stroke_width=stroke, stroke_fill=(0, 0, 0))
            cx += draw.textlength(word + " ", font=font)
        y += line_h

    # Barra con el degradado de la marca bajo el texto.
    bar_y = H - 34
    for i in range(260):
        draw.line([(x + i, bar_y), (x + i, bar_y + 8)], fill=gradient_color(i / 259))

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
    for vid, number, text, photo, zoom in EPISODES:
        print(render(vid, number, text, photo, zoom, logo).name)


if __name__ == "__main__":
    main()
