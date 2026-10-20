"""Descarga los subtítulos de YouTube (manuales o automáticos) como transcripción.

La transcripción es el texto que más ayuda al SEO y a la aprobación de AdSense
(contenido original y extenso). Córrelo desde tu computador: YouTube suele bloquear
las descargas desde servidores como GitHub Actions.

    pip install yt-dlp
    python scripts/fetch_transcripts.py            # solo los que faltan
    python scripts/fetch_transcripts.py --limit 20
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from common import ROOT, load_config, load_episodes

OUT = ROOT / "content" / "transcripts"


def vtt_to_text(vtt):
    lines, last = [], None
    for line in vtt.splitlines():
        line = line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        # Los subtítulos automáticos repiten cada línea al menos dos veces.
        if line and line != last:
            lines.append(line)
            last = line
    # Las marcas de sonido que no aportan al lector se quitan; [risas] y [aplausos] se mantienen.
    text = re.sub(r"\s*\[(?:música|carraspeo|resoplido|ovación)\]", "", " ".join(lines), flags=re.IGNORECASE)
    return to_paragraphs(text)


def to_paragraphs(text, target=90):
    """Párrafos de ~90 palabras que siempre terminan al final de una oración."""
    paragraphs, current = [], []
    for word in text.split():
        current.append(word)
        if len(current) >= target and word[-1] in ".!?…":
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def is_punctuated(text):
    """Los subtítulos automáticos antiguos de YouTube vienen sin puntuación y no se publican."""
    words = len(text.split())
    return words > 0 and sum(text.count(c) for c in ".?!") * 1000 / words >= 15


def fetch(video_id, lang):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([
            "yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
            "--sub-langs", f"{lang}.*,{lang}", "--sub-format", "vtt",
            "-o", f"{tmp}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={video_id}",
        ], check=False, capture_output=True, text=True)
        files = sorted(Path(tmp).glob("*.vtt"))
        if not files:
            detail = ((result.stderr or result.stdout).strip().splitlines() or ["sin detalle"])[-1]
            # En GitHub Actions esto aparece como aviso en el resumen de la ejecución.
            print(f"::warning title={video_id}::{detail[:300]}")
            return None
        return vtt_to_text(files[0].read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    config = load_config()
    lang = config.get("language", "es")
    OUT.mkdir(parents=True, exist_ok=True)
    # Solo los episodios que se publican en el sitio (los Shorts se omiten).
    pending = [e for e in load_episodes()
               if e.get("duration_seconds", 0) >= config["min_duration_seconds"]
               and not (OUT / f"{e['id']}.txt").exists()]
    if args.limit:
        pending = pending[:args.limit]

    for i, ep in enumerate(pending, 1):
        text = fetch(ep["id"], lang)
        status = "ok" if text else "sin subtítulos"
        if text:
            (OUT / f"{ep['id']}.txt").write_text(text + "\n", encoding="utf-8")
        print(f"[{i}/{len(pending)}] {ep['title'][:60]} — {status}")


if __name__ == "__main__":
    main()
