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
from fetch_transcripts import is_punctuated

DIST = ROOT / "dist"
CONTENT = ROOT / "content"
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

URL_RE = re.compile(r"(https?://[^\s<]+[^\s<.,;:!?)\]'\"])")
TIME_RE = re.compile(r"^\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:|]?\s*(.+)$")
HASHTAG_RE = re.compile(r"#([\wáéíóúñü]{3,})", re.IGNORECASE)
CODE_RE = re.compile(r"^\s*(?:E(\d+)T(\d+)|#EfectoTip \d+|🔴\s*Especial (\w+))\s*[-|–]\s*")


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
        if "efectopodcast.com/episodios/" in line:
            continue  # el enlace de vuelta al sitio que se pega en YouTube
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


def episode_label(title):
    """Temporada y número a partir del código del título de YouTube ("E13T2 - ...")."""
    m = CODE_RE.match(title)
    if not m:
        return None, None, ""
    if m.group(1):
        season, number = int(m.group(2)), int(m.group(1))
        return season, number, f"Temporada {season} · Episodio {number}"
    if m.group(3):
        return None, None, f"Especial {m.group(3)}"
    return None, None, "Efecto Tip"


def prepare(config):
    episodes = [e for e in load_episodes() if e.get("duration_seconds", 0) >= config["min_duration_seconds"]]
    episodes.sort(key=lambda e: e["published"], reverse=True)
    editorial = json.loads(read_optional(CONTENT / "episodios.json") or "{}")
    guests = {}

    def topic_key(text):
        return slugify(text, 40).replace("-", "")

    aliases = {topic_key(k): v for k, v in config.get("topic_aliases", {}).items()}
    blocked = {topic_key(t) for t in config.get("topic_blocklist", []) + ["efectopodcast", "podcast"]}
    forced_names = {topic_key(k): v for k, v in config.get("topic_names", {}).items()}

    topic_names = {}
    for ep in episodes:
        paragraphs, chapters, hashtags = parse_description(ep.get("description", ""))
        transcript = read_optional(CONTENT / "transcripts" / f"{ep['id']}.txt")
        extra = editorial.get(ep["id"], {})
        season, number, label = episode_label(ep["title"])
        title = extra.get("title") or CODE_RE.sub("", ep["title"]).strip()
        slug = extra.get("slug") or slugify(title)
        ep.update({
            "youtube_title": ep["title"],
            "title": title,
            "old_slug": ep["slug"],
            "slug": slug,
            "url": f"/episodios/{slug}/",
            "season": season,
            "number": number,
            "label": label,
            "thumb_small": f"https://i.ytimg.com/vi/{ep['id']}/hqdefault.jpg",
            "paragraphs": paragraphs,
            "chapters": chapters,
            "summary": extra.get("description") or summary(ep.get("description", "")) or title,
            "date_human": fmt_date(ep["published"]),
            "date_iso": parse_date(ep["published"]).date().isoformat(),
            "duration": fmt_duration(ep["duration_seconds"]),
            "duration_human": human_duration(ep["duration_seconds"]),
            "duration_iso": iso_duration(ep["duration_seconds"]),
            "transcript": [p for p in re.split(r"\n\s*\n", transcript) if p.strip()] if is_punctuated(transcript) else [],
            "notes": Markup(read_optional(CONTENT / "notes" / f"{ep['id']}.html")),
            "editorial": json.loads(read_optional(CONTENT / "resumenes" / f"{ep['id']}.json") or "null"),
            "guests": [],
        })
        for g in extra.get("guests", []):
            gslug = slugify(g["name"], 60)
            guest = guests.setdefault(gslug, {"slug": gslug, "name": g["name"], "url": f"/invitados/{gslug}/", "episodes": []})
            guest["role"] = guest.get("role") or g.get("role", "")  # el rol del episodio más reciente
            guest["episodes"].append(ep)
            ep["guests"].append({**guest, "role": g.get("role", "")})
        # "#saludmental" y la etiqueta "salud mental" son el mismo tema: se agrupan por slug sin guiones.
        # Las etiquetas van primero porque traen espacios y dan mejores nombres.
        topics = []
        for raw in [t.lower() for t in extra.get("topics", []) + ep.get("tags", [])] + hashtags:
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

    for t in topics.values():
        t["intro"] = Markup(read_optional(CONTENT / "temas" / f"{t['slug']}.html"))
        t["guests"] = list(dict.fromkeys(g["name"] for ep in by_topic[t["slug"]] for g in ep["guests"]))

    return episodes, sorted(topics.values(), key=lambda t: -t["count"]), sorted(guests.values(), key=lambda g: g["name"])


def redirect_page(target):
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Redirigiendo…</title>'
            f'<link rel="canonical" href="{target}"><meta name="robots" content="noindex">'
            f'<meta http-equiv="refresh" content="0; url={target}"></head>'
            f'<body><script>location.replace("{target}"+location.search+location.hash)</script>'
            f'<p><a href="{target}">Este episodio cambió de dirección</a></p></body></html>')


MARKER_RE = re.compile(r"\[\[(ep|inv):([^\]|]+)(?:\|([^\]]+))?\]\]")


def load_guides(episodes, guests):
    """Guías temáticas de content/guias/*.json. Los marcadores [[ep:ID]] e [[inv:Nombre]] se vuelven enlaces."""
    by_id = {e["id"]: e for e in episodes}
    by_name = {g["name"]: g for g in guests}

    def link(m):
        kind, key, text = m.group(1), m.group(2).strip(), m.group(3)
        target = by_id.get(key) if kind == "ep" else by_name.get(key)
        if not target:
            print(f"  aviso: marcador sin destino {m.group(0)}")
            return html.escape(text or key)
        label = text or (target["title"] if kind == "ep" else target["name"])
        return f'<a href="{target["url"]}">{html.escape(label)}</a>'

    guides = []
    for path in sorted((CONTENT / "guias").glob("*.json")):
        g = json.loads(path.read_text(encoding="utf-8"))
        g["slug"] = path.stem
        g["url"] = f"/guias/{path.stem}/"
        g["sections"] = [{**sec, "id": slugify(sec["title"], 60), "html": Markup(MARKER_RE.sub(link, sec["html"]))}
                         for sec in g["sections"]]
        g["episodes"] = [by_id[i] for i in g.get("episodes", []) if i in by_id]
        words = len(g["intro"].split()) + sum(len(re.sub(r"<[^>]+>", " ", sec["html"]).split()) for sec in g["sections"])
        g["minutes"] = max(1, round(words / 220))
        g["published"] = g.get("published") or datetime.now().date().isoformat()
        g["updated"] = g.get("updated") or g["published"]
        g["updated_human"] = fmt_date(g["updated"] + "T00:00:00")
        for ep in g["episodes"]:
            ep.setdefault("guides", []).append(g)
        guides.append(g)
    return guides


def faq(config, episodes, topics, guests):
    names = [g["name"] for g in sorted(guests, key=lambda g: -len(g["episodes"]))][:5]
    values = {
        "episodios": len(episodes),
        "invitados": len(guests),
        "ejemplos": ", ".join(names[:-1]) + " y " + names[-1] if len(names) > 1 else "".join(names),
        "temas": ", ".join(t["name"].lower() if t["name"] != "ChatGPT" else t["name"] for t in topics[:6]),
        "ultimo": episodes[0]["date_human"] if episodes else "",
        "email": config["contact_email"],
    }
    items = json.loads(read_optional(CONTENT / "faq.json") or "[]")
    return [{"q": i["q"], "a": i["a"].format(**values)} for i in items]


def person(g):
    return {"@type": "Person", "@id": f"{g['base']}{g['url']}#persona", "name": g["name"], "jobTitle": g["role"] or None,
            "url": g["base"] + g["url"]}


def episode_schema(ep, base, config):
    """PodcastEpisode + VideoObject con capítulos (Clip) para los "momentos clave" de Google."""
    url = base + ep["url"]
    chapters = ep["chapters"]
    clips = [{"@type": "Clip", "name": c["title"], "startOffset": c["seconds"],
              "endOffset": chapters[i + 1]["seconds"] if i + 1 < len(chapters) else ep["duration_seconds"],
              "url": f"{url}?t={c['seconds']}"} for i, c in enumerate(chapters)]
    video = {"@type": "VideoObject", "@id": url + "#video", "name": ep["title"], "description": ep["summary"],
             "thumbnailUrl": [ep["thumbnail"]], "uploadDate": ep["published"], "duration": ep["duration_iso"],
             "embedUrl": f"https://www.youtube.com/embed/{ep['id']}",
             "contentUrl": f"https://www.youtube.com/watch?v={ep['id']}", "inLanguage": config["language"],
             "interactionStatistic": {"@type": "InteractionCounter", "interactionType": {"@type": "WatchAction"},
                                      "userInteractionCount": int(ep.get("view_count") or 0)}}
    if clips:
        video["hasPart"] = clips
    guests = [person({**g, "base": base}) for g in ep["guests"]]
    episode = {"@type": "PodcastEpisode", "@id": url + "#episodio", "name": ep["title"], "url": url,
               "datePublished": ep["date_iso"], "description": ep["summary"], "timeRequired": ep["duration_iso"],
               "inLanguage": config["language"], "image": ep["thumbnail"],
               "partOfSeries": {"@id": base + "/#podcast"},
               "author": {"@id": base + "/#conductor"}, "publisher": {"@id": base + "/#organizacion"},
               "about": [{"@type": "Thing", "name": t["name"]} for t in ep["topics"]] or None,
               "keywords": ", ".join(t["name"] for t in ep["topics"]) or None,
               "actor": guests or None, "associatedMedia": video}
    graph = []
    if ep["editorial"]:
        episode["abstract"] = ep["editorial"]["resumen"][0]
        graph.append({"@type": "FAQPage", "@id": url + "#preguntas", "isPartOf": {"@id": url + "#episodio"},
                      "mainEntity": [{"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
                                     for q in ep["editorial"]["preguntas"]]})
    if ep["number"] is not None:
        episode["episodeNumber"] = ep["number"]
        episode["partOfSeason"] = {"@type": "PodcastSeason", "seasonNumber": ep["season"], "partOfSeries": {"@id": base + "/#podcast"}}
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Episodios", "item": base + "/"},
        {"@type": "ListItem", "position": 2, "name": ep["title"], "item": url}]}
    return [prune(episode), crumbs] + graph


def prune(value):
    if isinstance(value, dict):
        return {k: prune(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [prune(v) for v in value]
    return value


AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
           "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot", "CCBot"]


def write(rel, content):
    path = DIST / rel.lstrip("/")
    if rel.endswith("/"):
        path = path / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    config = load_config()
    base = config["base_url"].rstrip("/")
    episodes, topics, guests = prepare(config)
    guides = load_guides(episodes, guests)

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
    env.filters["faq_item"] = lambda i: {"@type": "Question", "name": i["q"], "acceptedAnswer": {"@type": "Answer", "text": i["a"]}}
    env.filters["prune"] = prune
    env.filters["ep_ref"] = lambda e: {"@id": base + e["url"] + "#episodio"}
    env.filters["guest_ref"] = lambda g: {"@type": "Person", "name": g["name"], "url": base + g["url"]}
    env.filters["org"] = lambda name: {"@type": "CollegeOrUniversity", "name": name}
    env.filters["list_items"] = lambda xs: [{"@type": "ListItem", "position": i, "url": base + x["url"], "name": x.get("name") or x["title"]}
                                            for i, x in enumerate(xs, 1)]
    env.filters["tojson_safe"] = lambda v: Markup(json.dumps(v, ensure_ascii=False).replace("</", "<\\/"))
    env.globals.update(site=config, base=base, year=datetime.now().year, top_topics=topics[:12], guides=guides,
                       host=config["hosts"][0] if config.get("hosts") else None)

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "static", DIST / "static")

    sitemap = []

    def render(rel, template, priority="0.5", lastmod=None, index=True, **ctx):
        write(rel, env.get_template(template).render(canonical=base + rel, path=rel, **ctx))
        if index:
            sitemap.append((rel, lastmod, priority))

    # En la portada, la temporada destacada va primero (del último episodio al primero);
    # el resto sigue por fecha de publicación.
    featured = config.get("home_featured_season")
    home = sorted(episodes, key=lambda e: (0, -e["number"]) if featured and e["season"] == featured else (1, 0))
    per_page = config["episodes_per_page"]
    pages = max(1, math.ceil(len(episodes) / per_page))
    latest = episodes[0]["date_iso"] if episodes else None
    for n in range(1, pages + 1):
        rel = "/" if n == 1 else f"/episodios/pagina/{n}/"
        render(rel, "list.html", "1.0" if n == 1 else "0.4", latest,
               episodes=home[(n - 1) * per_page:n * per_page], page=n, pages=pages, topics=topics,
               faq=faq(config, episodes, topics, guests) if n == 1 else [],
               prev_url=None if n == 1 else ("/" if n == 2 else f"/episodios/pagina/{n - 1}/"),
               next_url=f"/episodios/pagina/{n + 1}/" if n < pages else None)

    for ep in episodes:
        render(ep["url"], "episode.html", "0.8", ep["date_iso"], ep=ep, schema=episode_schema(ep, base, config))
        if ep["old_slug"] != ep["slug"]:
            write(f"/episodios/{ep['old_slug']}/", redirect_page(base + ep["url"]))

    for g in guides:
        render(g["url"], "guide.html", "0.9", g["updated"], guide=g)
    if guides:
        render("/guias/", "guides.html", "0.7", max(g["updated"] for g in guides))

    for g in guests:
        render(g["url"], "guest.html", "0.6", g["episodes"][0]["date_iso"], guest=g,
               schema=[prune({**person({**g, "base": base}), "description": f"{g['name']}, {g['role']}. Conversó en {config['site_name']}.",
                              "subjectOf": [{"@id": base + e["url"] + "#episodio"} for e in g["episodes"]]})])
    render("/invitados/", "guests.html", "0.5", latest, guests=guests)

    for t in topics:
        eps = [e for e in episodes if t in e["topics"]]
        render(t["url"], "topic.html", "0.6", eps[0]["date_iso"], topic=t, episodes=eps)
    render("/temas/", "topics.html", "0.5", latest, topics=topics)

    for page in sorted((CONTENT / "pages").glob("*.html")):
        title, _, body = page.read_text(encoding="utf-8").partition("\n")
        body = body.replace("{{ email }}", config["contact_email"]).replace("{{ site }}", config["site_name"])
        render(f"/{page.stem}/", "page.html", "0.3", title=title.strip(), body=Markup(body))

    host = (config.get("hosts") or [None])[0]
    if host and host.get("slug"):
        bio = Markup(read_optional(CONTENT / "autor" / f"{host['slug']}.html"))
        render(f"/{host['slug']}/", "author.html", "0.6", latest, bio=bio, episodes=episodes)

    render("/buscar/", "search.html", index=False)
    write("/404.html", env.get_template("404.html").render(canonical=base + "/404.html", path="/404"))

    write("/search.json", json.dumps([
        {"t": e["title"], "u": e["url"], "d": e["date_human"], "s": e["summary"],
         "k": " ".join([t["name"] for t in e["topics"]] + [g["name"] for g in e["guests"]])} for e in episodes]
        + [{"t": g["title"], "u": g["url"], "d": "Guía", "s": g["description"], "k": "guía"} for g in guides],
        ensure_ascii=False))

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

    # Los buscadores con IA (ChatGPT, Claude, Perplexity, Gemini) pueden leer y citar el sitio.
    bots = "".join(f"User-agent: {b}\nAllow: /\n\n" for b in AI_BOTS)
    write("/robots.txt", f"{bots}User-agent: *\nAllow: /\nDisallow: /buscar/\n\nSitemap: {base}/sitemap.xml\n")
    for full, name in ((False, "/llms.txt"), (True, "/llms-full.txt")):
        write(name, env.get_template("llms.txt").render(episodes=episodes, topics=topics, guests=guests, full=full))
    if config.get("indexnow_key"):
        write(f"/{config['indexnow_key']}.txt", config["indexnow_key"])
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

    print(f"Sitio generado en dist/: {len(episodes)} episodios, {len(topics)} temas, {len(guests)} invitados, "
          f"{len(sitemap)} URLs en sitemap")


if __name__ == "__main__":
    main()
