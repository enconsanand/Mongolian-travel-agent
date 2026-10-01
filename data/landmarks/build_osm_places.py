#!/usr/bin/env python3
"""Pull named visitor places for Terelj, Khövsgöl and Uvs from OpenStreetMap.

Writes ../landmarks/osm_places.json (max 200). Coordinates and tags are ODbL
(OpenStreetMap contributors). Notes are short originals, not copied reviews.
Optionally attaches freely licensed Wikimedia Commons photos into
../mock/images.json. Google photos and review text are not collected.

Run from the repo:  python3 data/landmarks/build_osm_places.py
"""

import json
import math
import os
import re
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "landmarks", "osm_places.json")
PLACES = os.path.join(ROOT, "data", "mock", "places.json")
IMAGES = os.path.join(ROOT, "data", "mock", "images.json")
MAX_PLACES = 200
RETRIEVED = "2026-10-01"

QUERY = r"""
[out:json][timeout:90];
(
  nwr["name"]["tourism"](47.75,107.15,48.35,107.95);
  nwr["name"]["historic"~"monastery|ruins|archaeological_site|memorial"](47.75,107.15,48.35,107.95);
  nwr["name"]["natural"~"cliff|waterfall|hot_spring|beach"](47.75,107.15,48.35,107.95);
  nwr["name"]["tourism"](49.35,99.50,51.75,101.55);
  nwr["name"]["historic"~"monastery|ruins|archaeological_site|memorial"](49.35,99.50,51.75,101.55);
  nwr["name"]["natural"~"cliff|waterfall|hot_spring|beach"](49.35,99.50,51.75,101.55);
  nwr["name"]["tourism"](49.05,91.15,50.80,95.40);
  nwr["name"]["historic"~"monastery|ruins|archaeological_site|memorial"](49.05,91.15,50.80,95.40);
  nwr["name"]["natural"~"cliff|waterfall|hot_spring|beach"](49.05,91.15,50.80,95.40);
);
out center tags;
"""

KEEP_TOURISM = {
    "camp_site", "hotel", "guest_house", "chalet", "motel", "attraction", "viewpoint",
    "museum", "wilderness_hut", "alpine_hut", "hostel", "apartment", "resort", "caravan_site",
}
LODGING = {
    "camp_site", "hotel", "guest_house", "chalet", "motel", "hostel", "resort",
    "caravan_site", "alpine_hut", "wilderness_hut",
}
GENERIC = {
    "gercamp", "touristcamp", "hotel", "guesthouse", "camp", "stonecliff", "cliff",
    "viewpoint", "museum", "attraction", "resort", "ger", "campsite", "hut",
}
TYPE_NOTE = {
    "camp_site": ("Жуулчны бааз.", "Tourist camp."),
    "hotel": ("Зочид буудал.", "Hotel."),
    "guest_house": ("Зочны байр.", "Guest house."),
    "chalet": ("Амралтын байшин.", "Holiday cabin."),
    "motel": ("Замын буудал.", "Motel."),
    "apartment": ("Амралтын байр.", "Holiday apartment."),
    "resort": ("Амралтын цогцолбор.", "Resort."),
    "attraction": ("Аялалын үзвэр.", "Visitor stop."),
    "viewpoint": ("Үзэсгэлэнт цэг.", "Viewpoint."),
    "museum": ("Музей.", "Museum."),
    "wilderness_hut": ("Аялагчийн овоохой.", "Wilderness hut."),
    "alpine_hut": ("Уулын овоохой.", "Mountain hut."),
    "hostel": ("Хямд буудал.", "Hostel."),
    "caravan_site": ("Машины зогсоолтой бааз.", "Camp with vehicle parking."),
    "cliff": ("Хад цохио.", "Rock formation."),
    "waterfall": ("Хүрхрээ.", "Waterfall."),
    "hot_spring": ("Халуун рашаан.", "Hot spring."),
    "beach": ("Нуурын эрэг.", "Shore."),
    "monastery": ("Хийд.", "Monastery."),
    "memorial": ("Дурсгалын газар.", "Memorial."),
    "ruins": ("Түүхэн туурь.", "Historic ruins."),
    "archaeological_site": ("Эртний дурсгал.", "Archaeological site."),
}
AREA_NOTE = {
    "terelj": ("Горхи-Тэрэлжийн орчим.", "Near Gorkhi-Terelj."),
    "khuvsgul": ("Хөвсгөлийн чиглэл.", "On the Khövsgöl side."),
    "uvs": ("Увсын чиглэл.", "On the Uvs side."),
}
AREA_AIMAG = {"terelj": "Töv", "khuvsgul": "Khövsgöl", "uvs": "Uvs"}
RESORT_WORD = re.compile(r"амралт|resort|camp|бааз|lodge|жуулч|cabin|ger", re.I)
NUMBERED = re.compile(r"^(terelj|тэрэлж)\s*\d+$", re.I)
CYR = re.compile(r"[А-Яа-яӨөҮүЁё]")
# Russian spellings and map junk that are not a Mongolian holiday stay.
JUNK = re.compile(
    r"[ыёщъ]|посёлок|зимовье|трансформатор|столик|гараж|garage|confluence|телескоп|"
    r"telescope|павильон|pavilion|участнику|[\uac00-\ud7af]|50\s*°|^\s*50\s*100|"
    r"наш дом|ger camping|viewpoint lake",
    re.I,
)
BARE = {
    "lake", "ovoo", "ovaa", "museum", "buudal", "yurt", "yurta", "grand", "vot", "car",
    "english", "hut", "camp", "hotel", "ancient", "russkyi", "gorykak",
    "овоо", "оваа", "буудал", "музей", "нуур", "гэр", "юрта",
    "сэлэнгэ", "дэлгэрмөрөн", "selenge", "delgermoron",
}

def norm(value: str) -> str:
    return re.sub(r"[^0-9a-zа-яөүё]", "", value.lower())


def to_latin(value: str) -> str:
    out = []
    for ch in value:
        low = ch.lower()
        if low in _TO_LATIN:
            piece = _TO_LATIN[low]
            out.append(piece[:1].upper() + piece[1:] if ch.isupper() else piece)
        else:
            out.append(ch)
    return "".join(out)


_TO_LATIN = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "ye", "ё": "yo", "ж": "j",
    "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "ө": "ö", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ү": "ü", "ф": "f",
    "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}


def pair(raw: str, tags: dict) -> tuple[str, str]:
    mn = tags.get("name:mn") or ""
    en = tags.get("name:en") or ""
    if CYR.search(raw):
        mn = mn or raw
        en = en or to_latin(mn)
    else:
        en = en or raw
        # Keep a Latin business name as written. Galig would turn "Riverside" into nonsense.
        mn = mn or en
    mn, en = mn.strip(), en.strip()
    if norm(mn) == norm(en) and CYR.search(mn):
        en = to_latin(mn)
    return mn, en


def kind_of(tags: dict) -> str | None:
    if tags.get("tourism") in KEEP_TOURISM:
        return tags["tourism"]
    for key in ("natural", "historic"):
        if tags.get(key) in TYPE_NOTE:
            return tags[key]
    return None


def area_of(lat: float, lng: float) -> str | None:
    if 47.75 <= lat <= 48.35 and 107.15 <= lng <= 107.95:
        return "terelj"
    if 49.35 <= lat <= 51.75 and 99.50 <= lng <= 101.55:
        return "khuvsgul"
    if 49.05 <= lat <= 50.80 and 91.15 <= lng <= 95.40:
        return "uvs"
    return None


def hav(a: tuple[float, float], b: tuple[float, float]) -> float:
    lng1, lat1 = map(math.radians, a)
    lng2, lat2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def clip(text: str) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
    return text[:240]


def note_for(tags: dict, kind: str, area: str) -> dict:
    mn_d = clip(tags.get("description:mn") or "")
    en_d = clip(tags.get("description:en") or "")
    plain = clip(tags.get("description") or "")
    if plain and not mn_d and not en_d:
        if CYR.search(plain):
            mn_d = plain
        else:
            en_d = plain
    mn_t, en_t = TYPE_NOTE[kind]
    mn_a, en_a = AREA_NOTE[area]
    mn = mn_d or f"{mn_a} {mn_t}"
    en = en_d or f"{en_a} {en_t}"
    phone = tags.get("phone") or tags.get("contact:phone")
    if phone:
        phone = clip(phone)
        mn = f"{mn} Утас: {phone}"
        en = f"{en} Phone: {phone}"
    stars = tags.get("stars")
    if stars and re.fullmatch(r"[0-5](\.0)?", stars):
        mn = f"{mn} Газрын зураг дээр {stars} од."
        en = f"{en} OpenStreetMap lists {stars} stars."
    return {"mn": mn, "en": en}


def fetch_osm() -> list[dict]:
    req = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=QUERY.encode(),
        headers={"User-Agent": "mn-travel-catalog/0.1 (hackathon; OSM ODbL)"},
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)["elements"]


def existing_index() -> list[tuple[str, tuple[float, float]]]:
    rows = []
    for place in json.load(open(PLACES, encoding="utf-8")):
        lng, lat = place["location"]["coordinates"]
        names = [place["name"]["mn"], place["name"]["en"], *place.get("aliases", [])]
        for name in names:
            key = norm(name)
            if key:
                rows.append((key, (lng, lat)))
    return rows


def build() -> list[dict]:
    known = existing_index()
    seen: list[tuple[str, tuple[float, float]]] = []
    picked = []
    for el in fetch_osm():
        tags = el.get("tags") or {}
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lng = el.get("lon") or (el.get("center") or {}).get("lon")
        kind = kind_of(tags)
        if lat is None or lng is None or not kind or el.get("type") == "relation":
            continue
        area = area_of(lat, lng)
        raw = (tags.get("name") or "").strip()
        if lat > 51.58:
            continue
        if not area or not raw or NUMBERED.match(raw) or norm(raw) in GENERIC or JUNK.search(raw):
            continue
        if kind == "apartment" and not RESORT_WORD.search(raw):
            continue
        mn, en = pair(raw, tags)
        if JUNK.search(mn) or JUNK.search(en) or norm(en) in BARE or norm(mn) in BARE:
            continue
        if len(mn) < 2 or len(en) < 2:
            continue
        point = (round(lng, 6), round(lat, 6))
        keys = {norm(mn), norm(en), norm(raw)}
        known_names = {key for key, _ in known}
        if keys & known_names:
            continue
        if any(hav(point, prev) < 0.4 and key == pkey for key in keys for pkey, prev in seen):
            continue
        if any(hav(point, prev) < 0.3 for _, prev in known):
            continue
        seen.append((norm(mn), point))
        aliases = []
        for value in (raw, tags.get("name:en"), tags.get("name:mn"), tags.get("alt_name"), mn, en):
            if value and value.strip() and value.strip() not in aliases:
                aliases.append(value.strip())
        osm_type = {"node": "node", "way": "way", "relation": "relation"}[el["type"]]
        picked.append({
            "_id": f"place_osm_{osm_type[0]}_{el['id']}",
            "name": {"mn": mn, "en": en},
            "aimag": AREA_AIMAG[area],
            "kind": "attraction",
            "location": {"type": "Point", "coordinates": [point[0], point[1]]},
            "fuel_available": False,
            "aliases": aliases,
            "coordinate_source": {
                "url": f"https://www.openstreetmap.org/{osm_type}/{el['id']}",
                "source_id": f"{osm_type} {el['id']}",
                "retrieved_on": RETRIEVED,
                "coordinate_role": "landmark",
            },
            "note": note_for(tags, kind, area),
            "_area": area,
            "_lodging": kind in LODGING,
        })
    if len(picked) > MAX_PLACES:
        lodging = [p for p in picked if p["_lodging"]]
        other = [p for p in picked if not p["_lodging"]]
        room = max(0, MAX_PLACES - len(lodging))
        picked = lodging[:MAX_PLACES] + other[:room]
    for doc in picked:
        doc.pop("_area")
        doc.pop("_lodging")
    picked.sort(key=lambda d: d["_id"])
    return picked[:MAX_PLACES]


def _commons(params: dict) -> dict:
    import time
    import urllib.error
    import urllib.parse

    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    headers = {"User-Agent": "mn-travel-catalog/0.1 (hackathon; Commons CC photos)"}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as res:
                return json.load(res)
        except urllib.error.HTTPError as err:
            err.close()
            if err.code != 429 or attempt == 2:
                return {}
            time.sleep(8)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return {}
    return {}


def attach_images(places: list[dict]) -> None:
    import time

    sys.path.insert(0, os.path.join(ROOT, "data", "mock"))
    import fetch_images as photos

    found = json.load(open(IMAGES, encoding="utf-8")) if os.path.exists(IMAGES) else {}
    used = {img.get("title", "") for rows in found.values() if isinstance(rows, list) for img in rows}
    pending: dict[str, list[dict]] = {}
    for i, place in enumerate(places, 1):
        lng, lat = place["location"]["coordinates"]
        words = [w for w in re.split(r"[\s(),]+", place["name"]["en"]) if len(w) > 3]
        rows = _commons({
            "action": "query", "list": "geosearch", "gscoord": f"{lat}|{lng}",
            "gsradius": 8000, "gsnamespace": 6, "gslimit": 12,
        }).get("query", {}).get("geosearch", [])
        ranked = []
        for row in rows:
            title = row["title"]
            if not title.lower().endswith((".jpg", ".jpeg")) or photos.SKIP_WORDS.search(title):
                continue
            named = any(w.lower() in title.lower() for w in words)
            scenic = bool(photos.VIEW_WORDS.search(title) or photos.STAY_WORDS.search(title))
            if named or (scenic and row["dist"] <= 2500):
                ranked.append((0 if named else 1, row["dist"], title))
        ranked.sort()
        pending[place["_id"]] = [
            {"title": title, "distance_m": round(dist), "named": rank == 0}
            for rank, dist, title in ranked[:4]
        ]
        print(f"photo {i}/{len(places)} {place['_id']} {len(ranked)}", flush=True)
        time.sleep(0.35)
    info = photos.image_info(sorted({c["title"] for rows in pending.values() for c in rows}))
    added = 0
    for pid, cands in pending.items():
        imgs = []
        for cand in cands:
            title = cand["title"]
            if title not in info or info[title]["title"] in used:
                continue
            img = {k: v for k, v in info[title].items() if k != "_in_mongolia"}
            img["match"] = "location"
            img["distance_m"] = cand["distance_m"]
            img["is_illustrative"] = not (cand["named"] and cand["distance_m"] <= 2000)
            imgs.append(img)
            used.add(img["title"])
            if len(imgs) == 2:
                break
        if imgs:
            found[pid] = imgs
            added += 1
    with open(IMAGES, "w", encoding="utf-8") as handle:
        json.dump(found, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print(f"images for {added} new places", flush=True)


def main() -> None:
    images = "--images-only" in sys.argv or "--places-only" not in sys.argv
    if "--images-only" in sys.argv:
        places = json.load(open(OUT, encoding="utf-8"))
    else:
        places = build()
        counts = {}
        for place in places:
            counts[place["aimag"]] = counts.get(place["aimag"], 0) + 1
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(places, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"wrote {len(places)} places {counts}", flush=True)
    if images and "--places-only" not in sys.argv:
        attach_images(places)


if __name__ == "__main__":
    main()
