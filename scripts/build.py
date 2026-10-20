"""Genera el sitio estático en dist/ a partir de data/episodes.json."""
import html
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from common import ROOT, load_config, load_episodes, slugify

DIST = ROOT / "dist"
CONTENT = ROOT / "content"
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

URL_RE = re.compile(r"(https?://[^\s<]+[^\s<.,;:!?)\]'\"])")
TIME_RE = re.compile(r"^\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:|]?\s*(.+)$")
HASHTAG_RE = re.compile(r"#([\wáéíóúñü]{3,})", re.IGNORECASE)


def to_seconds(stamp):
    secs = 0
    for part in stamp.split(":"):
        secs = secs * 60 + int(part)
    return secs


def fmt_duration(secs):
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def human_duration(secs):
    h, m = divmod(round(secs / 60), 60)
    return f"{h} h {m} min" if h else f"{m} min"


def iso_duration(secs):
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"PT{h}H{m}M{s}S"


def parse_date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fmt_date(value):
    d = parse_date(value)
    return f"{d.day} de {MONTHS[d.month - 1]} de {d.year}"


def parse_description(text):
    """Separa la descripción en párrafos, capítulos (marcas de tiempo) y hashtags."""
    chapters, kept = [], []
    for line in text.splitlines():
        m = TIME_RE.match(line.strip())
        if m:
            chapters.append({"seconds": to_seconds(m.group(1)), "stamp": m.group(1), "title": m.group(2).strip()})
        else:
            kept.append(line)
    hashtags = [h.lower() for h in HASHTAG_RE.findall(text)]
    body = "\n".join(kept).strip()
    body = re.sub(r"(?<![\w&])#\w+", "", body)
    paragraphs = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        safe = html.escape(block)
        safe = URL_RE.sub(r'<a href="\1" rel="nofollow noopener" target="_blank">\1</a>', safe)
        lines = [l.strip() for l in safe.splitlines() if l.strip()]
        if all(l[:2] in ("* ", "- ", "• ") for l in lines):
            items = "".join(f"<li>{l[2:].strip()}</li>" for l in lines)
            paragraphs.append(Markup(f"<ul>{items}</ul>"))
        elif re.fullmatch(r"[━─—_=\-\s]+", block):
            paragraphs.append(Markup("<hr>"))
        else:
            paragraphs.append(Markup(f"<p>{'<br>'.join(lines)}</p>"))
    return paragraphs, chapters, hashtags


def summary(text, length=155):
    text = re.sub(r"https?://\S+|#\w+", "", text)
    text = " ".join(l for l in text.splitlines() if not TIME_RE.match(l.strip()))
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def read_optional(path):
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def prepare(config):
    episodes = [e for e in load_episodes() if e.get("duration_seconds", 0) >= config["min_duration_seconds"]]
    episodes.sort(key=lambda e: e["published"], reverse=True)

    def topic_key(text):
        return slugify(text, 40).replace("-", "")

    aliases = {topic_key(k): v for k, v in config.get("topic_aliases", {}).items()}
    blocked = {topic_key(t) for t in config.get("topic_blocklist", []) + ["efectopodcast", "podcast"]}
    forced_names = {topic_key(k): v for k, v in config.get("topic_names", {}).items()}

    topic_names = {}
    for ep in episodes:
        paragraphs, chapters, hashtags = parse_description(ep.get("description", ""))
        transcript = read_optional(CONTENT / "transcripts" / f"{ep['id']}.txt")
        ep.update({
            "url": f"/episodios/{ep['slug']}/",
            "paragraphs": paragraphs,
            "chapters": chapters,
            "summary": summary(ep.get("description", "")) or ep["title"],
            "date_human": fmt_date(ep["published"]),
            "date_iso": parse_date(ep["published"]).date().isoformat(),
            "duration": fmt_duration(ep["duration_seconds"]),
            "duration_human": human_duration(ep["duration_seconds"]),
            "duration_iso": iso_duration(ep["duration_seconds"]),
            "transcript": [p for p in re.split(r"\n\s*\n", transcript) if p.strip()],
            "notes": Markup(read_optional(CONTENT / "notes" / f"{ep['id']}.html")),
        })
        # "#saludmental" y la etiqueta "salud mental" son el mismo tema: se agrupan por slug sin guiones.
        # Las etiquetas van primero porque traen espacios y dan mejores nombres.
        topics = []
        for raw in [t.lower() for t in ep.get("tags", [])] + hashtags:
            raw = aliases.get(topic_key(raw), raw)
            key = topic_key(raw)
            if not key or key in topics or key in blocked:
                continue
            topics.append(key)
            if key not in topic_names or (" " in raw and " " not in topic_names[key][1]):
                topic_names[key] = (slugify(raw, 40), raw.strip().capitalize())
            if key in forced_names:
                topic_names[key] = (slugify(forced_names[key], 40), forced_names[key])
        ep["topic_slugs"] = topics

    counts = Counter(t for ep in episodes for t in ep["topic_slugs"])
    topics = {k: {"slug": topic_names[k][0], "name": topic_names[k][1], "url": f"/temas/{topic_names[k][0]}/", "count": c}
              for k, c in counts.items() if c >= config["min_episodes_per_topic"]}
    for ep in episodes:
        ep["topics"] = [topics[k] for k in ep["topic_slugs"] if k in topics][:8]

    by_topic = defaultdict(list)
    for ep in episodes:
        for t in ep["topics"]:
            by_topic[t["slug"]].append(ep)

    index = {e["id"]: e for e in episodes}
    for i, ep in enumerate(episodes):
        scored = Counter()
        for t in ep["topics"]:
            for other in by_topic[t["slug"]]:
                if other is not ep:
                    scored[other["id"]] += 1
        related = [index[x] for x, _ in scored.most_common(6)]
        for other in episodes:
            if len(related) >= 6:
                break
            if other is not ep and other not in related:
                related.append(other)
        ep["related"] = related
        ep["newer"] = episodes[i - 1] if i > 0 else None
        ep["older"] = episodes[i + 1] if i + 1 < len(episodes) else None

    return episodes, sorted(topics.values(), key=lambda t: -t["count"])


def write(rel, content):
    path = DIST / rel.lstrip("/")
    if rel.endswith("/"):
        path = path / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    config = load_config()
    base = config["base_url"].rstrip("/")
    episodes, topics = prepare(config)

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["tojson_safe"] = lambda v: Markup(json.dumps(v, ensure_ascii=False).replace("</", "<\\/"))
    env.globals.update(site=config, base=base, year=datetime.now().year, top_topics=topics[:12])

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST / "static")

    sitemap = []

    def render(rel, template, priority="0.5", lastmod=None, index=True, **ctx):
        write(rel, env.get_template(template).render(canonical=base + rel, path=rel, **ctx))
        if index:
            sitemap.append((rel, lastmod, priority))

    per_page = config["episodes_per_page"]
    pages = max(1, math.ceil(len(episodes) / per_page))
    latest = episodes[0]["date_iso"] if episodes else None
    for n in range(1, pages + 1):
        rel = "/" if n == 1 else f"/episodios/pagina/{n}/"
        render(rel, "list.html", "1.0" if n == 1 else "0.4", latest,
               episodes=episodes[(n - 1) * per_page:n * per_page], page=n, pages=pages, topics=topics,
               prev_url=None if n == 1 else ("/" if n == 2 else f"/episodios/pagina/{n - 1}/"),
               next_url=f"/episodios/pagina/{n + 1}/" if n < pages else None)

    for ep in episodes:
        render(ep["url"], "episode.html", "0.8", ep["date_iso"], ep=ep)

    for t in topics:
        eps = [e for e in episodes if t in e["topics"]]
        render(t["url"], "topic.html", "0.6", eps[0]["date_iso"], topic=t, episodes=eps)
    render("/temas/", "topics.html", "0.5", latest, topics=topics)

    for page in sorted((CONTENT / "pages").glob("*.html")):
        title, _, body = page.read_text(encoding="utf-8").partition("\n")
        body = body.replace("{{ email }}", config["contact_email"]).replace("{{ site }}", config["site_name"])
        render(f"/{page.stem}/", "page.html", "0.3", title=title.strip(), body=Markup(body))

    render("/buscar/", "search.html", index=False)
    write("/404.html", env.get_template("404.html").render(canonical=base + "/404.html", path="/404"))

    write("/search.json", json.dumps([
        {"t": e["title"], "u": e["url"], "d": e["date_human"], "s": e["summary"],
         "k": " ".join(t["name"] for t in e["topics"])} for e in episodes], ensure_ascii=False))

    urls = []
    for rel, lastmod, prio in sitemap:
        ep = next((e for e in episodes if e["url"] == rel), None)
        video = ""
        if ep:
            video = (f"<video:video><video:thumbnail_loc>{xml_escape(ep['thumbnail'])}</video:thumbnail_loc>"
                     f"<video:title>{xml_escape(ep['title'])}</video:title>"
                     f"<video:description>{xml_escape(ep['summary'])}</video:description>"
                     f"<video:player_loc>https://www.youtube.com/embed/{ep['id']}</video:player_loc>"
                     f"<video:duration>{ep['duration_seconds']}</video:duration>"
                     f"<video:publication_date>{ep['published']}</video:publication_date></video:video>")
        lm = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        urls.append(f"<url><loc>{base}{rel}</loc>{lm}<priority>{prio}</priority>{video}</url>")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n' + "\n".join(urls) + "\n</urlset>\n")

    write("/robots.txt", f"User-agent: *\nAllow: /\nDisallow: /buscar/\n\nSitemap: {base}/sitemap.xml\n")
    if config.get("adsense_client"):
        pub = config["adsense_client"].replace("ca-", "")
        write("/ads.txt", f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "".join(
        f"<item><title>{xml_escape(e['title'])}</title><link>{base}{e['url']}</link>"
        f"<guid>{base}{e['url']}</guid><pubDate>{parse_date(e['published']).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>"
        f"<description>{xml_escape(e['summary'])}</description></item>" for e in episodes[:50])
    write("/rss.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
          f"<title>{xml_escape(config['site_name'])}</title><link>{base}/</link>"
          f"<description>{xml_escape(config['description'])}</description><language>{config['language']}</language>"
          f"<lastBuildDate>{now}</lastBuildDate>{items}</channel></rss>\n")

    domain = base.split("://", 1)[1]
    if not domain.endswith("github.io"):
        write("/CNAME", domain + "\n")

    print(f"Sitio generado en dist/: {len(episodes)} episodios, {len(topics)} temas, {len(sitemap)} URLs en sitemap")


if __name__ == "__main__":
    main()
