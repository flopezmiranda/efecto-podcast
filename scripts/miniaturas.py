"""Genera las miniaturas de YouTube de las temporadas 1 y 2 (1280x720), al estilo de la temporada 2:
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

# Temporada 2: (video, número, frase, foto, zoom, invitado).
EPISODES_T2 = [
    ("tJ37gNshgjQ", 1, "¿ESTAMOS EN EL [LIMBO]?", "camisa-beige", 1.0, ""),
    ("YGUqzNpw4GU", 2, "¿HABLEMOS DE [IA]?", "polera-negra", 1.0, "Rodrigo Rojo"),
    ("F-ZYLWkf1aE", 3, "¿QUÉ HIZO [JAGUAR] CON SU MARCA?", "blazer-azul", 1.0, ""),
    ("ysD1ANMGac8", 4, "¿QUIÉN ES [SPEED]?", "camisa-mezclilla", 1.0, ""),
    ("OIfS359K-1g", 5, "¿FUERA DE AQUÍ, [TIKTOK]?", "cuello-alto-negro", 1.0, ""),
    ("LLutgvMLIbk", 6, "¿COLA DE LEÓN O [CABEZA DE RATÓN]?", "sueter-burdeo", 1.0, "Carolina Matamala"),
    ("8odqP10gjqg", 7, "¿NECESITAS UN [COACH] DE NEGOCIO?", "chaleco", 1.0, "Darío Poblete"),
    ("HLy0pXiYgys", 8, "DE VENDEDOR A [CEO]", "polera-gris", 1.0, "Daniel Cáceres"),
    ("2RSCZ5KAc64", 9, "¿LA IA TE QUITARÁ EL [TRABAJO]?", "camisa-celeste", 1.0, ""),
    ("cJRQMuvzC98", 10, "¿TU NEGOCIO NECESITA UN [INFLUENCER]?", "camisa-rayas", 1.0, ""),
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


def render(vid, number, text, photo, zoom, logo, season=1, guest=""):
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
        if len(lines) <= 4 and widest <= max_w and int(size * 1.08) * len(lines) + (50 if guest else 0) <= 430:
            break
    # Líneas parejas: el ancho más angosto que no agrega líneas.
    tw = max_w
    while tw > 200 and len(layout(words, font, tw - 10, draw)) == len(lines):
        tw -= 10
    lines = layout(words, font, tw, draw)
    line_h = int(size * 1.08)
    block_h = line_h * len(lines)
    kicker_h = 50 if guest else 0
    y = (H - block_h - kicker_h) // 2 + kicker_h
    if guest:
        draw.text((x, y - kicker_h), f"CON {guest.upper()}", font=ImageFont.truetype(FONT_SMALL, 30), fill=(213, 141, 243))
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
    draw.text((x, bar_y + 26), f"TEMPORADA {season} · EPISODIO {number}", font=tag, fill=MUTED)

    out = ROOT / "content" / "miniaturas" / f"E{number}T{season}-{vid}.jpg"
    img.save(out, "JPEG", quality=92)
    return out


CYAN = (94, 211, 255)


def render_t2(vid, number, text, photo, guest, logo):
    """Diseño de la temporada 2: foto a la derecha, número gigante de fondo y título abajo."""
    import numpy as np
    img = Image.new("RGB", (W, H), (6, 8, 26))
    glow = Image.new("RGB", (W, H), (6, 8, 26))
    d = ImageDraw.Draw(glow)
    d.ellipse((-300, 250, 700, 1050), fill=(10, 50, 95))
    d.ellipse((-200, -380, 520, 260), fill=(55, 22, 80))
    img = glow.filter(ImageFilter.GaussianBlur(160))

    # Foto a la derecha, nítida en la persona y difuminada hacia la izquierda y abajo.
    pic = Image.open(PHOTOS / f"felipe-{photo}.jpg").convert("RGB")
    scale = H * 1.08 / pic.height
    pic = pic.resize((round(pic.width * scale), round(pic.height * scale)), Image.LANCZOS)
    fx, fy = FACES[photo]
    ox = max(round(0.72 * W - fx * pic.width), W - pic.width)
    oy = min(0, max(round(0.40 * H - fy * pic.height), H - pic.height))
    layer = Image.new("RGB", (W, H), (6, 8, 26))
    layer.paste(pic, (ox, oy))
    face = (ox + fx * pic.width, oy + fy * pic.height)
    sharp = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sharp).ellipse((face[0] - 250, face[1] - 260, face[0] + 250, face[1] + 420), fill=255)
    sharp = sharp.filter(ImageFilter.GaussianBlur(130))
    layer = Image.composite(layer.filter(ImageFilter.GaussianBlur(1)), layer.filter(ImageFilter.GaussianBlur(26)), sharp)

    def smooth(t):
        t = np.clip(t, 0, 1)
        return t * t * (3 - 2 * t)
    x = np.linspace(0, 1, W)
    y = np.linspace(0, 1, H)
    alpha = np.outer(smooth((1 - y) / 0.42), smooth((x - 0.34) / 0.30)) * 0.92
    img = Image.composite(layer, img, Image.fromarray((alpha * 255).astype("uint8")))

    # Número de episodio gigante, con el degradado de la marca y transparente.
    num = f"{number:02d}"
    big = ImageFont.truetype(FONT, 470)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text((40, -40), num, font=big, fill=255)
    grad = Image.new("RGB", (W, H))
    gd = ImageDraw.Draw(grad)
    for i in range(W):
        gd.line([(i, 0), (i, H)], fill=gradient_color(i / (W * 0.55)))
    img = Image.composite(grad, img, mask.point(lambda v: int(v * 0.30)))

    draw = ImageDraw.Draw(img)
    # Logo original y nombre.
    lw = 70
    lg = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(lg, (64, 44), lg)
    draw.text((64 + lw + 18, 44 + lg.height // 2), "EFECTO PODCAST", font=ImageFont.truetype(FONT_SMALL, 30), fill=WHITE, anchor="lm")
    # Insignia de temporada.
    badge_font = ImageFont.truetype(FONT_SMALL, 24)
    label = "TEMPORADA 2"
    bw = draw.textlength(label, font=badge_font) + 40
    bx, by = W - 64 - bw, 46
    draw.rounded_rectangle((bx, by, bx + bw, by + 46), radius=23, fill=(9, 6, 25), outline=CYAN, width=2)
    draw.text((bx + bw / 2, by + 23), label, font=badge_font, fill=WHITE, anchor="mm")

    # Título abajo a la izquierda.
    words = tokens(text)
    max_w, x0 = 660, 64
    for size in range(112, 56, -4):
        font = ImageFont.truetype(FONT, size)
        lines = layout(words, font, max_w, draw)
        widest = max(draw.textlength(w, font=font) for w, _ in words)
        if len(lines) <= 3 and widest <= max_w:
            break
    tw = max_w
    while tw > 200 and len(layout(words, font, tw - 10, draw)) == len(lines):
        tw -= 10
    lines = layout(words, font, tw, draw)
    line_h = int(size * 1.04)
    y0 = H - 66 - line_h * len(lines)
    if guest:
        draw.text((x0, y0 - 44), f"CON {guest.upper()}", font=ImageFont.truetype(FONT_SMALL, 30), fill=CYAN)
    for line in lines:
        cx = x0
        for word, hl in line:
            draw.text((cx, y0), word, font=font, fill=CYAN if hl else WHITE,
                      stroke_width=2, stroke_fill=(6, 8, 26))
            cx += draw.textlength(word + " ", font=font)
        y0 += line_h
    # Barra de la marca a lo ancho, abajo.
    for i in range(W):
        draw.line([(i, H - 10), (i, H)], fill=gradient_color(i / (W - 1)))

    out = ROOT / "content" / "miniaturas" / f"E{number}T2-{vid}.jpg"
    img.save(out, "JPEG", quality=92)
    return out


def main():
    logo = Image.open(ROOT / "static" / "img" / "logo.png").convert("RGBA")
    for vid, number, text, photo, zoom in EPISODES:
        print(render(vid, number, text, photo, zoom, logo).name)
    for vid, number, text, photo, zoom, guest in EPISODES_T2:
        print(render_t2(vid, number, text, photo, guest, logo).name)


if __name__ == "__main__":
    main()
