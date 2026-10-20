"""Revisa los resúmenes de content/resumenes/ antes de publicarlos.

Comprueba la estructura, los largos, que las citas sean literales de la transcripción
y que no aparezcan nombres que no corresponden.

    python scripts/check_resumenes.py
"""
import json
import re

from common import ROOT

FORBIDDEN = re.compile(r"\bMario\b|Saavedra|Efecto ?Wow|(?-i:\bMido\b|\bFuture\b)", re.IGNORECASE)


def norm(text):
    return re.sub(r"\W+", " ", text.lower()).strip()


def check(path):
    problems = []
    data = json.loads(path.read_text(encoding="utf-8"))
    words = sum(len(p.split()) for p in data["resumen"])
    if not 400 <= words <= 700:
        problems.append(f"resumen de {words} palabras")
    if not 5 <= len(data["ideas_clave"]) <= 7:
        problems.append(f"{len(data['ideas_clave'])} ideas clave")
    if not 3 <= len(data["preguntas"]) <= 6:
        problems.append(f"{len(data['preguntas'])} preguntas")
    transcript = norm((ROOT / "content" / "transcripts" / f"{path.stem}.txt").read_text(encoding="utf-8"))
    for c in data["citas"]:
        if norm(c["texto"]) not in transcript:
            problems.append(f"cita no literal: «{c['texto'][:60]}…»")
    for m in FORBIDDEN.finditer(json.dumps(data, ensure_ascii=False)):
        problems.append(f"nombre no permitido: {m.group(0)}")
    return problems


def main():
    paths = sorted((ROOT / "content" / "resumenes").glob("*.json"))
    bad = 0
    for path in paths:
        problems = check(path)
        bad += bool(problems)
        print(f"{'✗' if problems else '✓'} {path.stem}" + "".join(f"\n    {p}" for p in problems))
    print(f"\n{len(paths)} resúmenes, {bad} con observaciones.")


if __name__ == "__main__":
    main()
