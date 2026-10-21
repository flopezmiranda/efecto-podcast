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

# (video, número, frase, foto, zoom). Las fotos con ropa cambiada se hicieron con IA en Canva.
EPISODES = [
    ("wYvn_DWpl18", 1, "HACKEANDO LA MÚSICA CON [IA]", "chaleco", 1.0),
    ("4cBSKxJolHc", 2, "DE LA PERSEVERANCIA A [MARTE]", "blazer-azul", 1.0),
    ("p79_GEB515o", 3, "¿UN CHIP EN TU [CEREBRO]?", "camisa-celeste", 1.0),
    ("YbI-3aQ7OR8", 4, "NO MÁS [VENTA DE HUMO] EN MARKETING", "polera-gris", 1.0),
    ("n8LxYjIbUCA", 5, "LANZA TU [MVP] HOY MISMO", "camisa-mezclilla", 1.0),
    ("fCGOkxt7zlU", 6, "EL GOL DE [MESSI] QUE CAMBIÓ UN NEGOCIO", "polera-negra", 1.0),
    ("j08Vcm6XAFY", 7, "5 TIPS PARA SER MÁS [PRODUCTIVO]", "camisa-beige", 1.0),
    ("V4BEdzMjixk", 8, "LOS 7 SECRETOS DE [FACEBOOK]", "cuello-alto-negro", 1.0),
    ("bXWRxUJOy70", 9, "[FALABELLA] SE ENAMORÓ DE UNA MALA IDEA", "camisa-rayas", 1.0),
    ("QkoM659gN1Q", 10, "¿ESTAMOS LISTOS PARA TANTA [TECNOLOGÍA]?", "sueter-burdeo", 1.0),
    ("mwaXlEqnlzQ", 11, "NO TODO ES [SABER]", "blazer-azul", 1.25),
    ("NF46uDl243M", 12, "¡CRINGE! QUE NO TE FRENE EL [QUÉ DIRÁN]", "camisa-mezclilla", 1.25),
]

# Posición de la cara en cada foto (fracción del ancho y del alto), para encuadrar.
FACES = {
    "chaleco": (0.394, 0.38),
    "camisa-beige": (0.388, 0.34),
    "polera-gris": (0.368, 0.34),
    "camisa-celeste": (0.389, 0.31),
    "camisa-rayas": (0.331, 0.30),
    "sueter-burdeo": (0.35, 0.32),
    "cuello-alto-negro": (0.40, 0.29),
    "camisa-mezclilla": (0.375, 0.30),
    "polera-negra": (0.40, 0.31),
    "blazer-azul": (0.40, 0.38),
}


def gradient_color(t):
    t = max(0.0, min(1.0, t)) * (len(GRAD) - 1)
    i = min(int(t), len(GRAD) - 2)
    a, b, f = GRAD[i], GRAD[i + 1], t - i
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def photo_layer(base, name, zoom):
    """Funde la foto con el fondo de la marca: a la derecha, difuminada y desvanecida hacia el texto."""
    import numpy as np
    photo = Image.open(PHOTOS / f"felipe-{name}.jpg").convert("RGB")
    scale = H * 1.05 * zoom / photo.height
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS)
    fx, fy = FACES[name]
    # Coloca la cara en el tercio derecho del cuadro.
    ox, oy = round(0.28 * W - fx * photo.width), round(0.42 * H - fy * photo.height)
    ox = min(ox, 0)                             # que la foto llegue al borde izquierdo
    oy = min(0, max(oy, H - photo.height))      # y cubra todo el alto
    layer = Image.new("RGB", (W, H), BG)
    layer.paste(photo, (ox, oy))
    face = (ox + fx * photo.width, oy + fy * photo.height)

    # La persona apenas suavizada; el estudio, muy difuminado.
    sharp = Image.new("L", (W, H), 0)
    rx, ry = 260 * zoom, 340 * zoom
    ImageDraw.Draw(sharp).ellipse((face[0] - rx, face[1] - ry + 80, face[0] + rx, face[1] + ry + 80), fill=255)
    sharp = sharp.filter(ImageFilter.GaussianBlur(140))
    layer = Image.composite(layer.filter(ImageFilter.GaussianBlur(1)), layer.filter(ImageFilter.GaussianBlur(24)), sharp)
    layer = Image.blend(Image.new("RGB", (W, H), BG), layer, 0.85)  # un poco más oscura, para que mande el texto

    # Se desvanece hacia la derecha (donde va el texto), arriba y abajo, con curvas suaves.
    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)
    x = np.linspace(0, 1, W)
    horiz = smooth((0.66 - x) / 0.34)
    y = np.linspace(0, 1, H)
    vert = smooth((1.0 - y) / 0.38) * (0.55 + 0.45 * smooth(y / 0.30))
    alpha = (np.outer(vert, horiz) * 255).astype("uint8")
    return Image.composite(layer, base, Image.fromarray(alpha))


def background():
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse((850, -350, 1800, 450), fill=(34, 12, 40))     # morado tenue arriba a la derecha
    d.ellipse((700, 380, 1550, 1100), fill=(12, 30, 62))     # azul tenue abajo
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
    img = background()
    if photo:
        img = photo_layer(img, photo, zoom)
    draw = ImageDraw.Draw(img)
    words = tokens(text)
    max_w, x = (560, 650) if photo else (1100, 90)
    for size in range(118, 56, -4):
        font = ImageFont.truetype(FONT, size)
        lines = layout(words, font, max_w, draw)
        widest = max(draw.textlength(w, font=font) for w, _ in words)
        # El bloque cabe entre el logo y el borde inferior.
        if len(lines) <= 4 and widest <= max_w and int(size * 1.08) * len(lines) <= 430:
            break
    # Líneas parejas: el ancho más angosto que no agrega líneas.
    tw = max_w
    while tw > 200 and len(layout(words, font, tw - 10, draw)) == len(lines):
        tw -= 10
    lines = layout(words, font, tw, draw)
    line_h = int(size * 1.08)
    block_h = line_h * len(lines)
    y = (H - block_h) // 2
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
    tag = ImageFont.truetype(FONT_SMALL, 28)
    draw.text((x, bar_y + 26), f"TEMPORADA 1 · EPISODIO {number}", font=tag, fill=MUTED)

    out = ROOT / "content" / "miniaturas" / f"E{number}T1-{vid}.jpg"
    img.save(out, "JPEG", quality=92)
    return out


def main():
    logo = Image.open(ROOT / "static" / "img" / "logo.png").convert("RGBA")
    for vid, number, text, photo, zoom in EPISODES:
        print(render(vid, number, text, photo, zoom, logo).name)


if __name__ == "__main__":
    main()
