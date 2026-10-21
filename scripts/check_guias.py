"""Revisa las guías de content/guias/ antes de publicarlas.

Comprueba largos, que los enlaces [[ep:]] / [[inv:]] existan, que las citas sean
literales de alguna transcripción y que no aparezcan nombres que no corresponden.

    python scripts/check_guias.py
"""
import json
import re

from check_resumenes import FORBIDDEN, norm
from common import ROOT

MARKER_RE = re.compile(r"\[\[(ep|inv):([^\]|]+)(?:\|[^\]]+)?\]\]")
QUOTE_RE = re.compile(r"<blockquote[^>]*>\s*<p>«(.*?)»</p>", re.S)


def main():
    editorial = json.loads((ROOT / "content" / "episodios.json").read_text(encoding="utf-8"))
    ids = {k for k in editorial if not k.startswith("_")}
    names = {g["name"] for v in editorial.values() if isinstance(v, dict) for g in v.get("guests", [])}
    transcripts = {p.stem: norm(p.read_text(encoding="utf-8")) for p in (ROOT / "content" / "transcripts").glob("*.txt")}
    paths = sorted((ROOT / "content" / "guias").glob("*.json"))
    bad = 0
    for path in paths:
        g = json.loads(path.read_text(encoding="utf-8"))
        problems = []
        body = " ".join(s["html"] for s in g["sections"])
        words = len(g["intro"].split()) + len(re.sub(r"<[^>]+>|\[\[[^\]]+\]\]", " ", body).split())
        if not 1400 <= words <= 2600:
            problems.append(f"{words} palabras")
        if len(g["description"]) > 160:
            problems.append(f"descripción de {len(g['description'])} caracteres")
        for kind, key in MARKER_RE.findall(json.dumps(g, ensure_ascii=False)):
            if (kind == "ep" and key not in ids) or (kind == "inv" and key not in names):
                problems.append(f"enlace sin destino: {kind}:{key}")
        for quote in QUOTE_RE.findall(body):
            if not any(norm(quote) in t for t in transcripts.values()):
                problems.append(f"cita no literal: «{quote[:60]}…»")
        for m in FORBIDDEN.finditer(json.dumps(g, ensure_ascii=False)):
            problems.append(f"nombre no permitido: {m.group(0)}")
        bad += bool(problems)
        print(f"{'✗' if problems else '✓'} {path.stem} ({words} palabras)" + "".join(f"\n    {p}" for p in problems))
    print(f"\n{len(paths)} guías, {bad} con observaciones.")


if __name__ == "__main__":
    main()
