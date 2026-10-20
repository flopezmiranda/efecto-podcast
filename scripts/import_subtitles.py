"""Convierte los subtítulos descargados de YouTube Studio en transcripciones.

Sube los archivos a content/subtitulos/ y corre:

    python scripts/import_subtitles.py

- .txt (transcripción copiada de YouTube): se asocia al episodio por el código del nombre
  del archivo (por ejemplo «E12T2 - ...txt») o, si no tiene código, por el título.
- .srt, .vtt o .sbv (con cualquier nombre): se asocia comparando la duración de los
  subtítulos con la del video, porque YouTube Studio los descarga con nombres parecidos.
Los archivos procesados se borran de content/subtitulos/.
"""
import difflib
import re
import sys
from pathlib import Path

from common import ROOT, load_config, load_episodes, slugify
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


EPISODE_CODE_RE = re.compile(r"^(E\d+T\d+)\b", re.IGNORECASE)


def match_by_code(name, episodes):
    m = EPISODE_CODE_RE.match(name)
    if not m:
        return None
    code = m.group(1).upper()
    found = [e for e in episodes if (EPISODE_CODE_RE.match(e["title"].strip()) or [None, ""])[1].upper() == code]
    return found[0] if len(found) == 1 else None


def match_by_title(name, episodes):
    """Para archivos sin código de episodio: compara el nombre con los títulos."""
    stem = slugify(Path(name).stem, 200)
    scored = sorted(
        ((difflib.SequenceMatcher(None, stem, slugify(e["title"], 200)).ratio(), e) for e in episodes),
        key=lambda c: -c[0],
    )
    best = scored[0]
    if best[0] >= 0.85 and (len(scored) == 1 or best[0] - scored[1][0] >= 0.05):
        return best[1]
    return None


def match_by_duration(raw, episodes):
    end = last_timestamp(raw)
    candidates = sorted(
        ((abs(e["duration_seconds"] - end), e) for e in episodes
         if 0 <= e["duration_seconds"] - end <= MAX_GAP_SECONDS),
        key=lambda c: c[0],
    ) if end else []
    if not candidates:
        return None, f"no se encontró un episodio de esa duración ({end // 60} min)"
    # Dos episodios con casi la misma duración: no adivinar.
    if len(candidates) > 1 and candidates[1][0] - candidates[0][0] < 5:
        return None, "hay dos episodios con casi la misma duración"
    return candidates[0][1], None


def main():
    config = load_config()
    episodes = [e for e in load_episodes() if e["duration_seconds"] >= config["min_duration_seconds"]]
    files = sorted(p for p in INBOX.glob("*") if p.suffix.lower() in (".srt", ".vtt", ".sbv", ".txt"))
    if not files:
        sys.exit(f"No hay archivos en {INBOX.relative_to(ROOT)}")

    OUT.mkdir(parents=True, exist_ok=True)
    claimed = {}
    unmatched = []
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".txt":
            ep = match_by_code(path.name, episodes) or match_by_title(path.name, episodes)
            reason = None if ep else "el nombre no coincide con el código ni con el título de un episodio"
            text_source = "WEBVTT\n\n" + raw
        else:
            ep, reason = match_by_duration(raw, episodes)
            text_source = to_plain_lines(raw)
        if not ep:
            unmatched.append((path.name, reason))
            continue
        if ep["id"] in claimed:
            print(f"Duplicado: {path.name} y {claimed[ep['id']]} son de «{ep['title']}». Se usa el primero.")
            path.unlink()
            continue
        text = vtt_to_text(text_source)
        (OUT / f"{ep['id']}.txt").write_text(text + "\n", encoding="utf-8")
        claimed[ep["id"]] = path.name
        path.unlink()
        print(f"OK  {path.name[:40]:<40} → {ep['title'][:55]} ({len(text.split())} palabras)")

    for name, reason in unmatched:
        print(f"??  {name}: {reason}. Queda en la carpeta.")
    print(f"\n{len(claimed)} transcripciones importadas, {len(unmatched)} sin asociar.")


if __name__ == "__main__":
    main()
