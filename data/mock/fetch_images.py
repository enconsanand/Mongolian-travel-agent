#!/usr/bin/env python3
"""Find freely licensed photos of the real places behind the mock data, from Wikimedia Commons.

- Places and stays: photos geotagged near the coordinates (Commons geosearch), ranked by title words.
- Events: photos of the real event (Naadam, Golden Eagle Festival, Ice Festival, ...) by text search.
Only CC BY / CC BY-SA / CC0 / public domain JPEGs are kept, with author, license and source.

Run once (needs internet):  python3 fetch_images.py  -> writes images.json, which generate.py reads.
Photos come from Commons only, never from resort or booking websites (those are copyrighted).
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = os.path.dirname(os.path.abspath(__file__))
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "mn-travel-mockdata/0.2 (hackathon demo; images with attribution)"}
LICENSE_OK = re.compile(r"^(cc[ -]?by|cc0|public domain|pd)", re.I)
SKIP_WORDS = re.compile(
    r"\b(iss\d*|earth|map|flag|coat of arms|emblem|logo|stamp|diagram|chart|portrait|signature|banknote|"
    r"coin|document|poster|screenshot|seal|insect|beetle|moth|butterfly|flower|plant|thymus|mushroom|"
    r"specimen|herbarium|fossil skull|parliament|bank|university|ministry|embassy|railway station)\b",
    re.I,
)
STAY_WORDS = re.compile(r"\b(camp|ger|gers|yurt|yurts|lodge|hotel|resort|guest ?house|tourist|cabin|house|bungalow)", re.I)
# Text-search results must be about Mongolia (title, description or categories)
MONGOLIA = re.compile(r"mongol|монгол|ulaanbaatar|ulan bator|gobi|khövsgöl|khuvsgul|hovsgol|ölgii|olgii|altai", re.I)
VIEW_WORDS = re.compile(r"\b(view|landscape|panorama|panoramio|lake|dunes?|valley|river|mountain|steppe|shore)", re.I)

# Checked by hand after a run: off-topic photos (food, accidents, Russia, Japan, unrelated buildings)
MANUAL_EXCLUDE = ["Mongol husúr", "Accident in Mongolian steppe", "Kosh-Agachsky District", "Darkhan District Office", "Darkhan Bus Station", "in Tsukuba", "MODIS", "Musical Instrument Museum", "Ruins of Lenin statue in Choibalsan", "Choibalsan Airport"]

EVENT_QUERIES = {
    "naadam": ["Naadam {city}", "Naadam horse racing Mongolia", "Naadam wrestling Mongolia", "Naadam archery Mongolia"],
    "event_national_naadam_2027": ["Naadam opening ceremony Ulaanbaatar", "Naadam National Sports Stadium"],
    "event_golden_eagle_festival_2026": ["Golden Eagle Festival Mongolia", "eagle hunter Bayan-Ölgii festival"],
    "event_khuvsgul_ice_festival_2027": ["Khuvsgul ice festival", "Khövsgöl lake winter ice"],
    "event_thousand_camel_festival_2027": ["Thousand Camel Festival", "camel race Gobi Mongolia"],
    "event_gobi_autumn_camel_race": ["camel race Gobi Mongolia", "Bactrian camels Gobi"],
    "event_ub_tsagaan_sar_2027": ["Tsagaan Sar Mongolia", "Mongolian lunar new year"],
    "event_amarbayasgalant_tsam_2027": ["Tsam dance Mongolia", "Amarbayasgalant monastery"],
    "event_kharkhorin_danshig_2027": ["Danshig Naadam", "Erdene Zuu monastery"],
    "event_olgii_nauryz_2027": ["Nauryz Mongolia", "Kazakh Bayan-Ölgii"],
    "event_darkhan_autumn_fair": ["Mongolian market dairy", "Darkhan Mongolia"],
    "event_choibalsan_autumn_fair": ["Mongolian market meat", "Choibalsan"],
    "event_khatgal_season_close_race": ["horse race Khövsgöl", "Mongolian horse race"],
    "event_uran_togoo_hike_day": ["Uran Togoo"],
    "event_dadal_chinggis_day_2026": ["Dadal Chinggis Khaan", "Dadal Khentii"],
    "event_playtime_festival_2027": ["Playtime Festival Mongolia", "rock concert Ulaanbaatar"],
    "event_sukhbaatar_horse_festival_2027": ["Mongolian horse race steppe", "Dariganga horses"],
}


def api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    for attempt in range(6):
        try:
            time.sleep(1.0)
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(15 * (attempt + 1))
    raise SystemExit("Commons keeps rate-limiting; try again later")


def image_info(titles: list[str]) -> dict[str, dict]:
    info = {}
    for i in range(0, len(titles), 40):
        pages = api({
            "action": "query", "titles": "|".join(titles[i:i + 40]), "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1024,
        }).get("query", {}).get("pages", {})
        for p in pages.values():
            if "imageinfo" not in p:
                continue
            ii = p["imageinfo"][0]
            meta = ii.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "")
            if ii.get("mime") != "image/jpeg" or not LICENSE_OK.match(lic) or ii.get("width", 0) < 800:
                continue
            about = " ".join(
                meta.get(k, {}).get("value", "") for k in ("Categories", "ImageDescription", "ObjectName")
            ) + " " + p["title"]
            info[p["title"]] = {
                "_in_mongolia": bool(MONGOLIA.search(about)),
                "url": ii["thumburl"].split("?")[0], "original_url": ii["url"].split("?")[0], "title": p["title"].removeprefix("File:"),
                "license": lic, "license_url": meta.get("LicenseUrl", {}).get("value"),
                "author": re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()[:120] or "unknown",
                "source": ii["descriptionurl"],
            }
    return info


def geosearch(lng: float, lat: float, radius_m: int = 10000, limit: int = 50) -> list[tuple[str, float]]:
    rows = api({"action": "query", "list": "geosearch", "gscoord": f"{lat}|{lng}", "gsradius": radius_m,
                "gsnamespace": 6, "gslimit": limit}).get("query", {}).get("geosearch", [])
    return [(r["title"], r["dist"]) for r in rows if r["title"].lower().endswith((".jpg", ".jpeg"))]


def textsearch(query: str, limit: int = 15) -> list[str]:
    rows = api({"action": "query", "list": "search", "srsearch": f"{query} filetype:bitmap", "srnamespace": 6,
                "srlimit": limit}).get("query", {}).get("search", [])
    return [r["title"] for r in rows]


def rank_geo(hits: list[tuple[str, float]], words: re.Pattern, name_words: list[str]) -> list[tuple[str, float]]:
    scored = []
    for title, dist in hits:
        if SKIP_WORDS.search(title):
            continue
        score = 3 * bool(words.search(title)) + 2 * bool(VIEW_WORDS.search(title))
        score += 2 * any(w.lower() in title.lower() for w in name_words)
        if score:
            scored.append((score, dist, title))
    scored.sort(key=lambda s: (-s[0], s[1]))
    return [(t, d) for _, d, t in scored]


def main() -> None:
    load = lambda name: json.load(open(os.path.join(OUT, f"{name}.json"), encoding="utf-8"))  # noqa: E731
    places, stays, events = load("places"), load("stays"), load("events")
    place_by_id = {p["_id"]: p for p in places}
    wanted: dict[str, list[dict]] = {}  # doc id -> candidates {title, match, distance_m}

    for p in places:
        lng, lat = p["location"]["coordinates"]
        name_words = [w for w in re.split(r"[\s(),]+", p["name"]["en"]) if len(w) > 3]
        hits = rank_geo(geosearch(lng, lat, 10000), VIEW_WORDS, name_words)[:4]  # 10 km is the API maximum
        wanted[p["_id"]] = [{"title": t, "match": "location", "distance_m": round(d)} for t, d in hits]
        print(f"place {p['_id']:28s} {len(hits)}")

    for s in stays:
        lng, lat = s["location"]["coordinates"]
        place = place_by_id[s["place_id"]]
        name_words = [w for w in re.split(r"[\s(),]+", place["name"]["en"]) if len(w) > 3]
        hits = rank_geo(geosearch(lng, lat, 5000), STAY_WORDS, name_words)
        lodging = [(t, d) for t, d in hits if STAY_WORDS.search(t)][:3]
        wanted[s["_id"]] = [{"title": t, "match": "near_stay", "distance_m": round(d)} for t, d in lodging]
        print(f"stay  {s['_id']:28s} {len(lodging)}")

    for e in events:
        city = place_by_id[e["place_id"]]["name"]["en"].split(" (")[0]
        queries = EVENT_QUERIES.get(e["_id"]) or [q.format(city=city) for q in EVENT_QUERIES.get(e["category"], [])]
        titles: list[str] = []
        for q in queries:
            titles += [t for t in textsearch(q) if t not in titles and not SKIP_WORDS.search(t)]
        wanted[e["_id"]] = [{"title": t, "match": "event_topic", "distance_m": None} for t in titles[:24]]
        print(f"event {e['_id']:28s} {len(titles)}")

    info = image_info(sorted({c["title"] for cands in wanted.values() for c in cands}))
    result = {}
    for n, (doc_id, cands) in enumerate(wanted.items()):
        imgs = [
            {**info[c["title"]], "match": c["match"], "distance_m": c["distance_m"]}
            for c in cands
            if c["title"] in info
            and (c["match"] != "event_topic" or info[c["title"]]["_in_mongolia"])
            and not any(x in c["title"] for x in MANUAL_EXCLUDE)
        ]
        if doc_id.startswith("event_") and len(imgs) > 4:
            # Many events share the same search results (e.g. aimag naadams): rotate so they differ
            start = (n * 3) % len(imgs)
            imgs = imgs[start:] + imgs[:start]
        for img in imgs:
            img.pop("_in_mongolia", None)
        if imgs:
            result[doc_id] = imgs[:4]
    with open(os.path.join(OUT, "images.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"images.json: {len(result)} docs, {sum(len(v) for v in result.values())} images")


if __name__ == "__main__":
    main()
