"""Importa todos los videos del canal de YouTube a data/episodes.json.

Usa la YouTube Data API v3 (gratis, requiere una API key en YOUTUBE_API_KEY).
Los slugs ya asignados nunca cambian, para no romper URLs ya indexadas en Google.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from common import load_config, load_episodes, save_episodes, slugify

API = "https://www.googleapis.com/youtube/v3/"


def api(endpoint, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def parse_duration(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def uploads_playlist(config):
    if config.get("youtube_channel_id"):
        res = api("channels", part="contentDetails", id=config["youtube_channel_id"])
    else:
        res = api("channels", part="contentDetails", forHandle=config["youtube_handle"])
    if not res.get("items"):
        sys.exit("No se encontró el canal. Revisa youtube_channel_id / youtube_handle en site.config.json")
    return res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def all_video_ids(playlist_id):
    ids, token = [], None
    while True:
        params = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50}
        if token:
            params["pageToken"] = token
        res = api("playlistItems", **params)
        ids += [it["contentDetails"]["videoId"] for it in res["items"]]
        token = res.get("nextPageToken")
        if not token:
            return ids


def best_thumbnail(thumbs):
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbs:
            return thumbs[key]["url"]
    return ""


def main():
    config = load_config()
    existing = {ep["id"]: ep for ep in load_episodes()}
    used_slugs = {ep["slug"] for ep in existing.values()}

    ids = all_video_ids(uploads_playlist(config))
    print(f"{len(ids)} videos en el canal")

    episodes = []
    for i in range(0, len(ids), 50):
        res = api("videos", part="snippet,contentDetails,statistics,status", id=",".join(ids[i:i + 50]))
        for v in res["items"]:
            if v["status"].get("privacyStatus") != "public":
                continue
            sn = v["snippet"]
            ep = existing.get(v["id"], {})
            slug = ep.get("slug")
            if not slug:
                base = slug = slugify(sn["title"])
                n = 2
                while slug in used_slugs:
                    slug = f"{base}-{n}"
                    n += 1
                used_slugs.add(slug)
            episodes.append({
                "id": v["id"],
                "slug": slug,
                "title": sn["title"],
                "description": sn.get("description", ""),
                "published": sn["publishedAt"],
                "duration_seconds": parse_duration(v["contentDetails"].get("duration")),
                "thumbnail": best_thumbnail(sn.get("thumbnails", {})),
                "tags": sn.get("tags", []),
                "view_count": int(v.get("statistics", {}).get("viewCount", 0)),
            })

    episodes.sort(key=lambda e: e["published"], reverse=True)
    save_episodes(episodes)
    new = len([e for e in episodes if e["id"] not in existing])
    print(f"Guardados {len(episodes)} episodios ({new} nuevos)")


if __name__ == "__main__":
    main()
