"""Lee una transcripción con tiempos copiada del panel «Transcripción» de YouTube.

Acepta los dos formatos que entrega el panel:
- el tiempo en una línea y el texto en la siguiente («0:07» / «me dio raya...»)
- el tiempo pegado al texto, con la etiqueta de accesibilidad
  («0:099 segundosequipos de marketing...»)
"""
import re

STAMP = r"(?:\d+:)?\d{1,2}:\d{2}"
LABEL = r"(?:\d+ horas?,? )?(?:y )?(?:\d+ minutos?(?: y )?)?(?:\d+ segundos?)?"
INLINE_RE = re.compile(rf"^({STAMP}){LABEL}(.*)$")
ALONE_RE = re.compile(rf"^{STAMP}$")


def to_seconds(stamp):
    secs = 0
    for part in stamp.split(":"):
        secs = secs * 60 + int(part)
    return secs


def parse(text):
    """Devuelve [(segundos, texto)]."""
    cues, pending = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Sincronizar con el tiempo"):
            continue
        if ALONE_RE.match(line):
            pending = to_seconds(line)
            continue
        m = INLINE_RE.match(line)
        if pending is None and m and m.group(2).strip():
            cues.append((to_seconds(m.group(1)), m.group(2).strip()))
        elif pending is not None:
            cues.append((pending, line))
            pending = None
        elif cues:
            cues[-1] = (cues[-1][0], cues[-1][1] + " " + line)
    return cues


def fmt(secs):
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
