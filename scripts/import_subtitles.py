"""Convierte los subtítulos descargados de YouTube Studio en transcripciones.

Sube los archivos (.srt, .vtt o .sbv, con cualquier nombre) a content/subtitulos/ y corre:

    python scripts/import_subtitles.py

YouTube Studio descarga todos los archivos con nombres parecidos, así que cada uno se
asocia a su episodio comparando la duración de los subtítulos con la del video.
Los archivos procesados se borran de content/subtitulos/.
"""
import re
import sys
from pathlib import Path

from common import ROOT, load_config, load_episodes
from fetch_transcripts import OUT, vtt_to_text

INBOX = ROOT / "content" / "subtitulos"
TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d{3})|(\d+):(\d{2})[.,](\d{3})")

# Los subtítulos terminan unos segundos antes que el video (créditos, silencio final).
MAX_GAP_SECONDS = 90


def last_timestamp(text):
    secs = 0
    for m in TIME_RE.finditer(text):
        if m.group(1) is not None:
            h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            h, mi, s = 0, int(m.group(5)), int(m.group(6))
        secs = max(secs, h * 3600 + mi * 60 + s)
    return secs


def to_plain_lines(text):
    """Deja solo las líneas de texto de un .srt, .vtt o .sbv."""
    kept = []
    for line in text.splitlines():
        line = line.strip().lstrip("﻿")
        if not line or line.isdigit() or "-->" in line:
            continue
        if re.fullmatch(r"[\d:.,]+", line):  # línea de tiempos del formato .sbv
            continue
        kept.append(line)
    return "WEBVTT\n\n" + "\n".join(kept)


def main():
    config = load_config()
    episodes = [e for e in load_episodes() if e["duration_seconds"] >= config["min_duration_seconds"]]
    files = sorted(p for p in INBOX.glob("*") if p.suffix.lower() in (".srt", ".vtt", ".sbv"))
    if not files:
        sys.exit(f"No hay archivos en {INBOX.relative_to(ROOT)}")

    OUT.mkdir(parents=True, exist_ok=True)
    claimed = {}
    unmatched = []
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        end = last_timestamp(raw)
        candidates = sorted(
            (abs(e["duration_seconds"] - end), e) for e in episodes
            if 0 <= e["duration_seconds"] - end <= MAX_GAP_SECONDS
        ) if end else []
        if not candidates:
            unmatched.append((path.name, end))
            continue
        gap, ep = candidates[0]
        # Dos episodios con casi la misma duración: no adivinar.
        if len(candidates) > 1 and candidates[1][0] - gap < 5:
            unmatched.append((path.name, end))
            continue
        if ep["id"] in claimed:
            print(f"Duplicado: {path.name} y {claimed[ep['id']]} son de «{ep['title']}». Se usa el primero.")
            path.unlink()
            continue
        text = vtt_to_text(to_plain_lines(raw))
        (OUT / f"{ep['id']}.txt").write_text(text + "\n", encoding="utf-8")
        claimed[ep["id"]] = path.name
        path.unlink()
        print(f"OK  {path.name:<28} → {ep['title'][:60]} ({len(text.split())} palabras)")

    for name, end in unmatched:
        print(f"??  {name}: no se encontró un episodio de esa duración ({end // 60} min). Queda en la carpeta.")
    print(f"\n{len(claimed)} transcripciones importadas, {len(unmatched)} sin asociar.")


if __name__ == "__main__":
    main()
