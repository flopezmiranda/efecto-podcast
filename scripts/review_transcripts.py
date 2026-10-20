"""Marca frases delicadas en las transcripciones antes de publicarlas.

Busca términos que, fuera del tono de una conversación, pueden leerse como ofensivos
(y que AdSense revisa). No decide nada: muestra cada caso con su contexto para que
una persona lo revise.

    python scripts/review_transcripts.py                 # todas las transcripciones
    python scripts/review_transcripts.py content/pendientes/archivo.txt
"""
import json
import re
import sys
from pathlib import Path

from common import ROOT

TERMS = re.compile(
    r"\b(monos?|monillos?|simios?|negr[oa]s?|indi[oa]s?|sudacas?|chol[oa]s?|mapuchito|"
    r"maric[oó]n\w*|marac[oa]s?|flet[oa]s?|travestis?|mong[oó]lic[oa]s?|mongol[oa]s?|"
    r"retrasad[oa]s?|subnormal\w*|violar|violaci[oó]n|violad[oa]r?|conchetu\w*|culia[od]\w*|"
    r"nazis?|judí[oa]s?)\b",
    re.IGNORECASE,
)

# Usos habituales que no son ofensivos.
BENIGN = re.compile(
    r"blanco y negro|lista[s]? negras?|escenario negro|negro con|ad negro|fondo negro|"
    r"humor negro|mercado negro|buen mono|mono animado de|chino mandarín|hoja negra|blanco negro|la India|hablar de mono|la hemos visto a negra",
    re.IGNORECASE,
)


def review(path, titles):
    text = path.read_text(encoding="utf-8")
    hits = []
    for m in TERMS.finditer(text):
        context = text[max(0, m.start() - 90):m.end() + 70].replace("\n", " ")
        if BENIGN.search(text[max(0, m.start() - 20):m.end() + 20]):
            continue
        hits.append((m.group(0), context))
    if hits:
        print(f"\n{titles.get(path.stem, path.name)}")
        for word, context in hits:
            print(f"  «{word}»: …{context}…")
    return len(hits)


def main():
    titles = {e["id"]: e["title"] for e in json.loads((ROOT / "data" / "episodes.json").read_text())}
    paths = [Path(p) for p in sys.argv[1:]] or sorted((ROOT / "content" / "transcripts").glob("*.txt"))
    total = sum(review(p, titles) for p in paths)
    print(f"\n{total} frases para revisar." if total else "Sin frases delicadas.")


if __name__ == "__main__":
    main()
