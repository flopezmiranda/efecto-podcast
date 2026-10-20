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
    text = " ".join(lines)
    # Párrafos de ~6 oraciones para que se lea bien en la página.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return "\n\n".join(" ".join(sentences[i:i + 6]) for i in range(0, len(sentences), 6))


def fetch(video_id, lang):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([
            "yt-dlp", "--skip-download", "--write-subs", "--write-auto-subs",
            "--sub-langs", f"{lang}.*,{lang}", "--sub-format", "vtt",
            "-o", f"{tmp}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={video_id}",
        ], check=False, capture_output=True)
        files = sorted(Path(tmp).glob("*.vtt"))
        return vtt_to_text(files[0].read_text(encoding="utf-8")) if files else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    lang = load_config().get("language", "es")
    OUT.mkdir(parents=True, exist_ok=True)
    pending = [e for e in load_episodes() if not (OUT / f"{e['id']}.txt").exists()]
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
