"""Avisa a Bing (y a los buscadores que usan IndexNow) qué páginas cambiaron.

Bing alimenta a ChatGPT Search y Copilot, así que un aviso rápido acelera que citen
los episodios nuevos. Compara el contenido de cada página con el del último aviso
(data/indexnow.json) y envía solo las que cambiaron. Se ejecuta después de publicar.

    python scripts/build.py && python scripts/indexnow.py
"""
import hashlib
import json
import re
import urllib.request

from common import ROOT, load_config

DIST = ROOT / "dist"
STATE = ROOT / "data" / "indexnow.json"


def page_hash(rel):
    html = (DIST / rel.lstrip("/") / "index.html").read_text(encoding="utf-8")
    # Solo el contenido visible: el schema trae las visitas de YouTube, que cambian todos los días.
    main = re.search(r"<main.*?</main>", html, re.S)
    return hashlib.sha256((main.group(0) if main else html).encode()).hexdigest()[:16]


def main():
    config = load_config()
    key = config.get("indexnow_key")
    if not key:
        return
    base = config["base_url"].rstrip("/")
    sitemap = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    paths = [loc[len(base):] for loc in re.findall(r"<loc>(.*?)</loc>", sitemap)]
    old = json.loads(STATE.read_text()) if STATE.exists() else {}
    new = {rel: page_hash(rel) for rel in paths}
    changed = [base + rel for rel in paths if old.get(rel) != new[rel]]
    if changed:
        body = json.dumps({"host": base.split("://", 1)[1], "key": key,
                           "keyLocation": f"{base}/{key}.txt", "urlList": changed[:10000]}).encode()
        req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"IndexNow: {len(changed)} URLs enviadas (HTTP {resp.status})")
    else:
        print("IndexNow: sin cambios")
    STATE.write_text(json.dumps(new, indent=0, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
