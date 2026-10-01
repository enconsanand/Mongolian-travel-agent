#!/usr/bin/env python3
"""Generates Mongolia travel mock data (one JSON array per MongoDB collection).

Run:  python3 generate.py   -> writes *.json next to this file.
Commerce data is MOCK: names, phones, prices and event dates are plausible, not real.
Curated destinations in ../landmarks/catalog.json are real, with coordinate provenance.
Coordinates are GeoJSON order: [lng, lat].
"""
import json, math, random, os
from datetime import date, timedelta

OUT = os.path.dirname(os.path.abspath(__file__))
random.seed(42)


def pt(lat, lng):
    return {"type": "Point", "coordinates": [lng, lat]}


# ---------------------------------------------------------------- places
# id, name_en, name_mn, aimag, kind, lat, lng, fuel, note
PLACES = [
    ("place_ub", "Ulaanbaatar", "Улаанбаатар", "Ulaanbaatar", "city", 47.9186, 106.9177, True, "Capital. Dragon bus terminal (west) serves north, west and south routes."),
    ("place_darkhan", "Darkhan", "Дархан", "Darkhan-Uul", "aimag_center", 49.4867, 105.9228, True, "Second largest city, on the paved UB to Russia highway."),
    ("place_amarbayasgalant", "Amarbayasgalant Monastery", "Амарбаясгалант хийд", "Selenge", "attraction", 49.4781, 105.0853, False, "18th-century monastery; last stretch is dirt."),
    ("place_erdenet", "Erdenet", "Эрдэнэт", "Orkhon", "aimag_center", 49.0275, 104.0442, True, "Copper mining city, good hotels and fuel."),
    ("place_bulgan", "Bulgan", "Булган", "Bulgan", "aimag_center", 48.8125, 103.5347, True, "Small green aimag center, gateway to Uran Togoo."),
    ("place_lun", "Lün", "Лүн", "Töv", "soum_center", 47.8667, 105.2500, True, "Tuul river crossing, roadside guanz (canteens)."),
    ("place_uran_togoo", "Uran Togoo Volcano", "Уран Тогоо", "Bulgan", "attraction", 48.9981, 102.7406, False, "Extinct volcano, easy 1h hike to the crater."),
    ("place_khutag_undur", "Khutag-Öndör", "Хутаг-Өндөр", "Bulgan", "soum_center", 49.3833, 102.6833, True, "Last reliable fuel between Bulgan and Mörön."),
    ("place_murun", "Mörön", "Мөрөн", "Khövsgöl", "aimag_center", 49.6342, 100.1625, True, "Khövsgöl aimag center, airport, bus station."),
    ("place_khatgal", "Khatgal", "Хатгал", "Khövsgöl", "soum_center", 50.4425, 100.1600, True, "Village at the south tip of Khövsgöl Lake."),
    ("place_toilogt", "Toilogt", "Тойлогт", "Khövsgöl", "attraction", 50.5167, 100.2167, False, "Peninsula on the west shore, many ger camps."),
    ("place_jankhai", "Jankhai", "Жанхай", "Khövsgöl", "attraction", 50.6380, 100.2950, False, "West shore camps; road is rocky and slow."),
    ("place_kharkhorin", "Kharkhorin", "Хархорин", "Övörkhangai", "soum_center", 47.1972, 102.8436, True, "Ancient capital, Erdene Zuu monastery."),
    ("place_elsen_tasarkhai", "Elsen Tasarkhai (Mini Gobi)", "Элсэн Тасархай", "Bulgan", "attraction", 47.3700, 103.6800, False, "Sand dunes right next to the paved road."),
    ("place_tsetserleg", "Tsetserleg", "Цэцэрлэг", "Arkhangai", "aimag_center", 47.4747, 101.4542, True, "Arkhangai aimag center."),
    ("place_tariat", "Tariat", "Тариат", "Arkhangai", "soum_center", 48.1567, 99.8828, True, "Next to Khorgo volcano and Terkhiin Tsagaan Lake."),
    ("place_terkhiin_tsagaan", "Terkhiin Tsagaan Lake", "Тэрхийн Цагаан нуур", "Arkhangai", "attraction", 48.1700, 99.7200, False, "Freshwater lake with ger camps."),
    ("place_shine_ider", "Shine-Ider", "Шинэ-Идэр", "Khövsgöl", "soum_center", 48.9500, 99.5300, True, "Small soum on the dirt road Tariat to Mörön."),
    ("place_mandalgovi", "Mandalgovi", "Мандалговь", "Dundgovi", "aimag_center", 45.7625, 106.2708, True, "Dundgovi aimag center, halfway to the south Gobi."),
    ("place_tsagaan_suvarga", "Tsagaan Suvarga", "Цагаан Суварга", "Dundgovi", "attraction", 44.5990, 105.7560, False, "Colourful eroded cliffs, 'White Stupa'."),
    ("place_dalanzadgad", "Dalanzadgad", "Даланзадгад", "Ömnögovi", "aimag_center", 43.5708, 104.4250, True, "Ömnögovi aimag center, airport."),
    ("place_yolyn_am", "Yolyn Am", "Ёлын Ам", "Ömnögovi", "attraction", 43.4900, 104.0700, False, "Ice canyon in Gurvan Saikhan National Park."),
    ("place_bayanzag", "Bayanzag (Flaming Cliffs)", "Баянзаг", "Ömnögovi", "attraction", 44.1380, 103.7270, False, "Dinosaur fossil site, red cliffs at sunset."),
    ("place_khongoryn_els", "Khongoryn Els", "Хонгорын Элс", "Ömnögovi", "attraction", 43.7725, 102.2800, False, "Singing sand dunes, up to 300 m high."),
    ("place_bulgan_soum_gobi", "Bulgan soum (Ömnögovi)", "Булган сум (Өмнөговь)", "Ömnögovi", "soum_center", 44.0930, 103.5400, True, "Host of the Thousand Camel Festival."),
]

places = [{
    "_id": p[0], "name": p[1], "name_mn": p[2], "aimag": p[3], "kind": p[4],
    "location": pt(p[5], p[6]), "fuel_available": p[7], "note": p[8],
} for p in PLACES]
PLACE = {p["_id"]: p for p in places}


def ll(pid):
    return PLACE[pid]["location"]["coordinates"]


# ---------------------------------------------------------------- routes
SPEED = {"paved": 70, "mixed": 45, "gravel": 40, "dirt": 30}  # km/h average incl. slowdowns


def hav(a, b):
    lng1, lat1, lng2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def seg(frm, to, surface, mid, condition="good", notes="", hazards=None):
    coords = [ll(frm)] + mid + [ll(to)]
    km = round(sum(hav(coords[i], coords[i + 1]) for i in range(len(coords) - 1)) * 1.12)
    return {
        "from_place_id": frm, "to_place_id": to, "surface": surface, "road_condition": condition,
        "distance_km": km, "drive_time_min": int(round(km / SPEED[surface] * 60 / 5) * 5),
        "fuel_at_end": PLACE[to]["fuel_available"], "hazards": hazards or [], "notes": notes,
        "geometry": {"type": "LineString", "coordinates": coords},
    }


# Reusable road legs
L = {
    "ub_darkhan": lambda: seg("place_ub", "place_darkhan", "paved", [[106.80, 48.20], [106.73, 48.39], [106.45, 48.86], [106.20, 49.20]], notes="Main north highway, police checkpoints at city exits."),
    "darkhan_erdenet": lambda: seg("place_darkhan", "place_erdenet", "paved", [[105.40, 49.40], [104.95, 49.25], [104.50, 49.10]]),
    "erdenet_bulgan": lambda: seg("place_erdenet", "place_bulgan", "paved", [[103.80, 48.93]]),
    "ub_lun": lambda: seg("place_ub", "place_lun", "paved", [[106.40, 47.88], [105.60, 47.85]], notes="Heavy truck traffic leaving UB before 10:00."),
    "lun_bulgan": lambda: seg("place_lun", "place_bulgan", "paved", [[104.60, 47.95], [104.00, 47.85], [103.80, 48.30]], condition="fair", notes="Potholes near Dashinchilen."),
    "bulgan_murun": lambda: seg("place_bulgan", "place_murun", "paved", [[103.10, 49.05], [102.6833, 49.3833], [101.90, 49.55], [101.20, 49.60], [100.60, 49.62]], condition="fair", notes="Refuel at Khutag-Öndör; long stretch without services.", hazards=["livestock_on_road", "long_no_fuel"]),
    "murun_khatgal": lambda: seg("place_murun", "place_khatgal", "paved", [[100.12, 49.90], [100.14, 50.20]]),
    "khatgal_jankhai": lambda: seg("place_khatgal", "place_jankhai", "dirt", [[100.2167, 50.5167]], condition="poor", notes="Rocky shore road via Toilogt, 4x4 recommended after rain.", hazards=["mud_after_rain", "rocky"]),
    "darkhan_amarbayasgalant": lambda: seg("place_darkhan", "place_amarbayasgalant", "mixed", [[105.50, 49.40], [105.25, 49.45]], condition="fair", notes="Paved to the turnoff, then ~35 km dirt track.", hazards=["mud_after_rain"]),
    "bulgan_uran_togoo": lambda: seg("place_bulgan", "place_uran_togoo", "mixed", [[103.10, 48.90]], notes="Last 20 km is a grassy track."),
    "ub_kharkhorin": lambda: seg("place_ub", "place_kharkhorin", "paved", [[106.40, 47.88], [105.25, 47.8667], [104.10, 47.60], [103.68, 47.37], [103.20, 47.25]], notes="Passes Elsen Tasarkhai dunes."),
    "kharkhorin_tsetserleg": lambda: seg("place_kharkhorin", "place_tsetserleg", "paved", [[102.30, 47.30], [101.80, 47.40]]),
    "tsetserleg_tariat": lambda: seg("place_tsetserleg", "place_tariat", "paved", [[101.00, 47.70], [100.50, 47.95]], condition="fair"),
    "tariat_terkhiin": lambda: seg("place_tariat", "place_terkhiin_tsagaan", "dirt", [], notes="Short track along the lava field."),
    "tariat_murun": lambda: seg("place_tariat", "place_murun", "dirt", [[99.70, 48.50], [99.53, 48.95], [99.80, 49.30]], condition="poor", notes="Unpaved, several stream crossings; not for sedans.", hazards=["river_crossing", "mud_after_rain", "no_signal"]),
    "ub_mandalgovi": lambda: seg("place_ub", "place_mandalgovi", "paved", [[106.95, 47.60], [106.80, 47.10], [106.50, 46.50]]),
    "mandalgovi_dalanzadgad": lambda: seg("place_mandalgovi", "place_dalanzadgad", "paved", [[105.90, 45.10], [105.30, 44.50], [104.80, 44.00]], notes="Straight desert highway, strong crosswinds.", hazards=["sandstorm_spring"]),
    "mandalgovi_tsagaan_suvarga": lambda: seg("place_mandalgovi", "place_tsagaan_suvarga", "mixed", [[105.95, 45.20], [105.85, 44.90]], condition="fair", notes="Paved ~70 km, then desert track. Needs a local driver or GPS."),
    "dalanzadgad_yolyn_am": lambda: seg("place_dalanzadgad", "place_yolyn_am", "mixed", [[104.25, 43.53]], notes="Park entrance fee 5,000 MNT/person."),
    "dalanzadgad_bayanzag": lambda: seg("place_dalanzadgad", "place_bayanzag", "mixed", [[104.10, 43.80]]),
    "dalanzadgad_khongor": lambda: seg("place_dalanzadgad", "place_khongoryn_els", "mixed", [[103.80, 43.62], [103.20, 43.68], [102.70, 43.73]], notes="New paved road toward Gurvantes, last ~60 km sand track.", hazards=["sand_stuck_risk"]),
    "bayanzag_khongor": lambda: seg("place_bayanzag", "place_khongoryn_els", "dirt", [[103.00, 43.95]], condition="poor", notes="Classic Gobi track, 4x4 only.", hazards=["sand_stuck_risk", "no_signal"]),
}

ROUTES = [
    ("route_ub_darkhan", "Ulaanbaatar to Darkhan", "north", ["ub_darkhan"], "Fastest trip out of UB; good weekend option."),
    ("route_ub_amarbayasgalant", "Ulaanbaatar to Amarbayasgalant Monastery", "north", ["ub_darkhan", "darkhan_amarbayasgalant"], "Usually overnight at the monastery ger camp."),
    ("route_ub_bulgan_via_lun", "Ulaanbaatar to Bulgan via Lün", "north", ["ub_lun", "lun_bulgan"], "Shortest paved road to Bulgan."),
    ("route_ub_bulgan_via_erdenet", "Ulaanbaatar to Bulgan via Darkhan and Erdenet", "north", ["ub_darkhan", "darkhan_erdenet", "erdenet_bulgan"], "Longer but better road and more services."),
    ("route_bulgan_uran_togoo", "Bulgan to Uran Togoo Volcano", "north", ["bulgan_uran_togoo"], "Day trip from Bulgan."),
    ("route_ub_khatgal_via_erdenet", "Ulaanbaatar to Khövsgöl Lake (Khatgal) via Erdenet", "khuvsgul", ["ub_darkhan", "darkhan_erdenet", "erdenet_bulgan", "bulgan_murun", "murun_khatgal"], "Fully paved; most drivers split it with a night in Bulgan or Mörön."),
    ("route_ub_khatgal_via_lun", "Ulaanbaatar to Khövsgöl Lake (Khatgal) via Lün", "khuvsgul", ["ub_lun", "lun_bulgan", "bulgan_murun", "murun_khatgal"], "Shorter paved option; fewer services."),
    ("route_khatgal_jankhai", "Khatgal to Jankhai (west shore)", "khuvsgul", ["khatgal_jankhai"], "Slow lake-shore track to the quieter camps."),
    ("route_ub_murun_central", "Ulaanbaatar to Mörön via Kharkhorin, Tsetserleg and Tariat", "khuvsgul", ["ub_kharkhorin", "kharkhorin_tsetserleg", "tsetserleg_tariat", "tariat_murun"], "Scenic central loop; the Tariat to Mörön part is dirt and weather sensitive."),
    ("route_tariat_terkhiin", "Tariat to Terkhiin Tsagaan Lake", "khuvsgul", ["tariat_terkhiin"], "Short hop to the lake camps."),
    ("route_ub_dalanzadgad", "Ulaanbaatar to Dalanzadgad (South Gobi)", "gobi", ["ub_mandalgovi", "mandalgovi_dalanzadgad"], "Fully paved; flights also available."),
    ("route_mandalgovi_tsagaan_suvarga", "Mandalgovi to Tsagaan Suvarga", "gobi", ["mandalgovi_tsagaan_suvarga"], "Common first stop on a Gobi loop."),
    ("route_dalanzadgad_yolyn_am", "Dalanzadgad to Yolyn Am", "gobi", ["dalanzadgad_yolyn_am"], "Half-day trip."),
    ("route_dalanzadgad_bayanzag", "Dalanzadgad to Bayanzag", "gobi", ["dalanzadgad_bayanzag"], "Go late afternoon for the sunset."),
    ("route_dalanzadgad_khongoryn_els", "Dalanzadgad to Khongoryn Els", "gobi", ["dalanzadgad_khongor"], "Mostly paved now, last part sand."),
    ("route_bayanzag_khongoryn_els", "Bayanzag to Khongoryn Els", "gobi", ["bayanzag_khongor"], "Off-road Gobi track, only with experienced driver."),
]

routes = []
for rid, name, region, legs, summary in ROUTES:
    segs = [L[k]() for k in legs]
    for i, s in enumerate(segs):
        s["seq"] = i + 1
    km = sum(s["distance_km"] for s in segs)
    by_surface = {}
    for s in segs:
        by_surface[s["surface"]] = by_surface.get(s["surface"], 0) + s["distance_km"]
    mins = sum(s["drive_time_min"] for s in segs)
    coords = []
    for s in segs:
        coords += s["geometry"]["coordinates"] if not coords else s["geometry"]["coordinates"][1:]
    routes.append({
        "_id": rid, "name": name, "region": region,
        "from_place_id": segs[0]["from_place_id"], "to_place_id": segs[-1]["to_place_id"],
        "waypoint_place_ids": [segs[0]["from_place_id"]] + [s["to_place_id"] for s in segs],
        "total_distance_km": km, "total_drive_time_min": mins,
        "recommended_days": max(1, math.ceil(mins / 60 / 8)),
        "surface_km": by_surface,
        "vehicle_min": "suv_4x4" if any(s["surface"] in ("dirt",) or "sand_stuck_risk" in s["hazards"] for s in segs) else "sedan",
        "summary": summary, "segments": segs,
        "geometry": {"type": "LineString", "coordinates": coords},
    })

# ---------------------------------------------------------------- events
EVENTS = [
    ("event_darkhan_autumn_fair", "Darkhan Autumn Harvest & Airag Fair", "Дархан намрын ургацын яармаг", "place_darkhan", "festival", "2026-10-03", "2026-10-04", 0, 8000, 1.3, "Local vegetables, dairy, airag, crafts in the central square."),
    ("event_khatgal_season_close_race", "Khövsgöl Season-Closing Horse Race", "Хөвсгөлийн улирал хаалтын морины уралдаан", "place_khatgal", "sport", "2026-10-03", "2026-10-03", 0, 1500, 1.5, "Small local horse race and bonfire as camps close for winter."),
    ("event_uran_togoo_hike_day", "Uran Togoo Autumn Hike Day", "Уран Тогоо намрын аялал", "place_uran_togoo", "outdoor", "2026-10-04", "2026-10-04", 10000, 400, 1.2, "Guided group hike to the crater with Bulgan youth volunteers."),
    ("event_gobi_autumn_camel_race", "Gobi Autumn Camel Race", "Говийн намрын тэмээн уралдаан", "place_dalanzadgad", "sport", "2026-10-10", "2026-10-11", 0, 3000, 1.6, "Camel races, camel polo, herder craft stalls."),
    ("event_ub_tsagaan_sar_2027", "Tsagaan Sar (Lunar New Year)", "Цагаан сар", "place_ub", "national_holiday", "2027-02-07", "2027-02-09", 0, 1500000, 0.8, "Families visit elders; many shops and services close for 3 days."),
    ("event_khuvsgul_ice_festival_2027", "Khövsgöl Ice Festival", "Хөвсгөлийн мөсний баяр", "place_khatgal", "festival", "2027-03-02", "2027-03-03", 20000, 6000, 2.5, "Ice sculptures, horse sledding, ice skating marathon, reindeer herders."),
    ("event_thousand_camel_festival_2027", "Thousand Camel Festival", "Мянган тэмээний баяр", "place_bulgan_soum_gobi", "festival", "2027-03-06", "2027-03-07", 15000, 4000, 2.2, "Camel races and camel polo with a thousand Bactrian camels."),
    ("event_dundgovi_naadam_2027", "Dundgovi Aimag Naadam", "Дундговь аймгийн наадам", "place_mandalgovi", "naadam", "2027-07-05", "2027-07-06", 5000, 10000, 1.8, "Wrestling, horse racing, archery at the aimag stadium."),
    ("event_bulgan_naadam_2027", "Bulgan Aimag Naadam", "Булган аймгийн наадам", "place_bulgan", "naadam", "2027-07-06", "2027-07-07", 5000, 9000, 1.8, "Aimag-level naadam; horse races held on the steppe 15 km out of town."),
    ("event_umnugovi_naadam_2027", "Ömnögovi Aimag Naadam", "Өмнөговь аймгийн наадам", "place_dalanzadgad", "naadam", "2027-07-07", "2027-07-08", 5000, 12000, 2.0, "Gobi naadam with camel racing alongside the three manly games."),
    ("event_darkhan_naadam_2027", "Darkhan-Uul Aimag Naadam", "Дархан-Уул аймгийн наадам", "place_darkhan", "naadam", "2027-07-08", "2027-07-09", 5000, 15000, 1.7, "Central stadium, archery and ankle-bone shooting."),
    ("event_khuvsgul_naadam_2027", "Khövsgöl Aimag Naadam", "Хөвсгөл аймгийн наадам", "place_murun", "naadam", "2027-07-08", "2027-07-10", 5000, 14000, 2.0, "Held in Mörön; hotels in Mörön fill up weeks ahead."),
    ("event_national_naadam_2027", "National Naadam Festival", "Үндэсний их баяр наадам", "place_ub", "naadam", "2027-07-11", "2027-07-15", 60000, 300000, 3.0, "Opening ceremony at the National Stadium, horse races at Khui Doloon Khudag."),
    ("event_khatgal_naadam_2027", "Khatgal Soum Naadam", "Хатгал сумын наадам", "place_khatgal", "naadam", "2027-07-18", "2027-07-19", 0, 2500, 1.6, "Small lakeside naadam, very photogenic, tourists welcome."),
    ("event_tariat_naadam_2027", "Tariat Soum Naadam", "Тариат сумын наадам", "place_tariat", "naadam", "2027-07-20", "2027-07-20", 0, 1500, 1.4, "Soum naadam by Terkhiin Tsagaan Lake."),
    ("event_amarbayasgalant_tsam_2027", "Amarbayasgalant Tsam Dance", "Амарбаясгалант хийдийн цам", "place_amarbayasgalant", "religious", "2027-08-21", "2027-08-22", 10000, 3000, 2.0, "Masked religious dance during the monastery's summer ceremony."),
    ("event_kharkhorin_danshig_2027", "Danshig Naadam at Kharkhorin", "Хархорин Даншиг наадам", "place_kharkhorin", "naadam", "2027-08-06", "2027-08-08", 10000, 8000, 1.8, "Religious-themed naadam near Erdene Zuu monastery."),
]
events = [{
    "_id": e[0], "name": e[1], "name_mn": e[2], "place_id": e[3], "aimag": PLACE[e[3]]["aimag"],
    "location": PLACE[e[3]]["location"], "category": e[4], "start_date": e[5], "end_date": e[6],
    "ticket_price_mnt": e[7], "expected_attendance": e[8], "stay_demand_multiplier": e[9],
    "description": e[10], "date_confidence": "approximate", "is_mock": True,
} for e in EVENTS]

# ---------------------------------------------------------------- cancellation policies
policies = [
    {"_id": "policy_flexible", "name": "Flexible", "free_cancel_hours_before": 24, "refund_pct_after_deadline": 50, "no_show_refund_pct": 0, "reschedule_allowed": True, "reschedule_fee_mnt": 0, "notes": "Free cancellation up to 24h before check-in."},
    {"_id": "policy_moderate", "name": "Moderate", "free_cancel_hours_before": 72, "refund_pct_after_deadline": 30, "no_show_refund_pct": 0, "reschedule_allowed": True, "reschedule_fee_mnt": 20000, "notes": "Typical ger camp policy; deposit kept if late."},
    {"_id": "policy_strict", "name": "Strict", "free_cancel_hours_before": 168, "refund_pct_after_deadline": 0, "no_show_refund_pct": 0, "reschedule_allowed": True, "reschedule_fee_mnt": 50000, "notes": "Peak season (Naadam, Ice Festival)."},
    {"_id": "policy_deposit_only", "name": "Deposit only", "free_cancel_hours_before": 48, "refund_pct_after_deadline": 70, "no_show_refund_pct": 0, "reschedule_allowed": True, "reschedule_fee_mnt": 0, "deposit_pct": 30, "deposit_refundable": False, "notes": "30% non-refundable deposit via QPay, rest paid on arrival."},
]

# ---------------------------------------------------------------- stays
OWNERS = ["Bat-Erdene", "Oyunchimeg", "Ganbold", "Sarangerel", "Tömörbaatar", "Enkhjargal", "Batbayar", "Nomin", "Davaasüren", "Altantsetseg", "Munkhbat", "Uyanga", "Tsogtbayar", "Khulan", "Erdenebileg", "Solongo", "Byambadorj", "Gerelmaa", "Naranbaatar", "Zolzaya", "Otgonbayar", "Ariunaa", "Chinbat", "Delgermaa", "Purevdorj", "Bolormaa"]

# id, name, name_mn, type, place, dlat, dlng, units[(unit_type,count,beds,price,basis,meals)], amenities, season, policy, rating
YEAR = None
STAYS = [
    ("stay_ub_hotel_blue_sky", "Steppe View Hotel", "Тал нутаг зочид буудал", "hotel", "place_ub", 0.001, 0.003, [("double_room", 40, 2, 280000, "per_unit", False), ("family_room", 10, 4, 420000, "per_unit", False)], ["wifi", "restaurant", "parking", "airport_transfer"], YEAR, "policy_flexible", 4.4),
    ("stay_ub_guesthouse_nomad", "Nomad Backpackers Guesthouse", "Нүүдэлчин гэр буудал", "guesthouse", "place_ub", -0.004, -0.010, [("dorm_bed", 16, 1, 35000, "per_person", False), ("double_room", 6, 2, 90000, "per_unit", False)], ["wifi", "kitchen", "tour_desk"], YEAR, "policy_flexible", 4.5),
    ("stay_darkhan_hotel_selenge", "Selenge River Hotel", "Сэлэнгэ голын зочид буудал", "hotel", "place_darkhan", 0.002, -0.004, [("double_room", 24, 2, 160000, "per_unit", False), ("suite", 4, 2, 260000, "per_unit", False)], ["wifi", "restaurant", "parking"], YEAR, "policy_flexible", 4.1),
    ("stay_darkhan_house_khongor", "Khongor Family House", "Хонгор гэр бүлийн байшин", "house", "place_darkhan", 0.030, 0.050, [("whole_house", 1, 6, 250000, "per_unit", False)], ["kitchen", "sauna", "bbq", "parking"], YEAR, "policy_moderate", 4.6),
    ("stay_amarbayasgalant_camp", "Amarbayasgalant Ger Camp", "Амарбаясгалант жуулчны бааз", "ger_camp", "place_amarbayasgalant", 0.006, 0.010, [("ger", 15, 3, 95000, "per_person", True)], ["meals", "hot_shower", "horse_riding"], ("06-01", "09-30"), "policy_moderate", 4.3),
    ("stay_erdenet_hotel_copper", "Copper City Hotel", "Зэс хотын зочид буудал", "hotel", "place_erdenet", 0.001, 0.002, [("double_room", 30, 2, 180000, "per_unit", False)], ["wifi", "restaurant", "gym", "parking"], YEAR, "policy_flexible", 4.2),
    ("stay_bulgan_hotel_khan", "Bulgan Khan Hotel", "Булган хан зочид буудал", "hotel", "place_bulgan", 0.001, -0.002, [("double_room", 18, 2, 130000, "per_unit", False), ("family_room", 4, 4, 200000, "per_unit", False)], ["wifi", "restaurant", "parking"], YEAR, "policy_flexible", 3.9),
    ("stay_bulgan_house_bayan", "Bayan Airag Country House", "Баян айраг хөдөөний байшин", "house", "place_bulgan", 0.050, 0.080, [("whole_house", 1, 8, 320000, "per_unit", False)], ["kitchen", "horse_riding", "airag", "fireplace"], YEAR, "policy_moderate", 4.7),
    ("stay_uran_togoo_camp", "Volcano Ger Camp", "Галт уулын бааз", "ger_camp", "place_uran_togoo", -0.010, 0.020, [("ger", 12, 4, 85000, "per_person", True)], ["meals", "hot_shower", "guided_hike"], ("05-20", "10-10"), "policy_moderate", 4.2),
    ("stay_murun_hotel_delger", "Delger Mörön Hotel", "Дэлгэр Мөрөн зочид буудал", "hotel", "place_murun", 0.001, 0.001, [("double_room", 26, 2, 150000, "per_unit", False), ("family_room", 6, 4, 230000, "per_unit", False)], ["wifi", "restaurant", "parking", "airport_transfer"], YEAR, "policy_flexible", 4.0),
    ("stay_khatgal_guesthouse_lake", "Lakeside Guesthouse Khatgal", "Нуурын эрэг гэр буудал", "guesthouse", "place_khatgal", 0.003, 0.004, [("ger", 6, 3, 50000, "per_person", False), ("double_room", 5, 2, 110000, "per_unit", False)], ["wifi", "kitchen", "kayak_rental", "horse_riding"], YEAR, "policy_flexible", 4.6),
    ("stay_khatgal_camp_blue_pearl", "Blue Pearl Ger Camp", "Хөх сувд бааз", "ger_camp", "place_khatgal", 0.020, 0.030, [("ger", 25, 3, 120000, "per_person", True), ("wooden_cabin", 6, 4, 150000, "per_person", True)], ["meals", "hot_shower", "sauna", "boat_trips"], ("06-01", "10-15"), "policy_moderate", 4.5),
    ("stay_toilogt_camp", "Toilogt Lakeshore Camp", "Тойлогт бааз", "ger_camp", "place_toilogt", 0.002, 0.004, [("ger", 30, 3, 140000, "per_person", True), ("wooden_cabin", 10, 4, 180000, "per_person", True)], ["meals", "hot_shower", "sauna", "boat_trips", "horse_riding"], ("06-10", "09-20"), "policy_strict", 4.4),
    ("stay_jankhai_house_taiga", "Taiga Log House", "Тайгын модон байшин", "house", "place_jankhai", 0.004, -0.003, [("whole_house", 1, 10, 450000, "per_unit", False)], ["kitchen", "sauna", "fireplace", "boat"], YEAR, "policy_deposit_only", 4.8),
    ("stay_jankhai_camp_nature", "Jankhai Nature Camp", "Жанхай байгалийн бааз", "ger_camp", "place_jankhai", -0.004, 0.002, [("ger", 14, 3, 110000, "per_person", True)], ["meals", "hot_shower", "horse_riding"], ("06-15", "09-15"), "policy_moderate", 4.1),
    ("stay_kharkhorin_camp_erdene", "Erdene Zuu Ger Camp", "Эрдэнэ Зуу бааз", "ger_camp", "place_kharkhorin", 0.010, 0.012, [("ger", 20, 3, 100000, "per_person", True)], ["meals", "hot_shower", "wifi"], ("05-15", "10-15"), "policy_moderate", 4.3),
    ("stay_elsen_tasarkhai_camp", "Mini Gobi Dune Camp", "Бага говь бааз", "ger_camp", "place_elsen_tasarkhai", 0.005, -0.006, [("ger", 18, 3, 90000, "per_person", True)], ["meals", "camel_riding", "hot_shower"], ("05-15", "10-05"), "policy_moderate", 4.0),
    ("stay_tsetserleg_hotel_bulgan", "Bulgan Mountain Hotel Tsetserleg", "Булган уулын зочид буудал", "hotel", "place_tsetserleg", 0.001, 0.001, [("double_room", 16, 2, 120000, "per_unit", False)], ["wifi", "restaurant"], YEAR, "policy_flexible", 4.0),
    ("stay_terkhiin_camp_white_lake", "White Lake Ger Camp", "Цагаан нуур бааз", "ger_camp", "place_terkhiin_tsagaan", 0.008, 0.015, [("ger", 22, 3, 95000, "per_person", True)], ["meals", "hot_shower", "fishing", "horse_riding"], ("06-01", "09-30"), "policy_moderate", 4.2),
    ("stay_tariat_family_ger", "Tariat Herder Family Gers", "Тариатын малчин айлын гэр", "house", "place_tariat", 0.040, -0.030, [("ger", 3, 4, 45000, "per_person", True)], ["meals", "herding_experience", "horse_riding"], YEAR, "policy_flexible", 4.9),
    ("stay_mandalgovi_hotel_gobi", "Middle Gobi Hotel", "Дундговь зочид буудал", "hotel", "place_mandalgovi", 0.001, -0.001, [("double_room", 14, 2, 110000, "per_unit", False)], ["wifi", "restaurant", "parking"], YEAR, "policy_flexible", 3.8),
    ("stay_tsagaan_suvarga_camp", "White Stupa Ger Camp", "Цагаан суварга бааз", "ger_camp", "place_tsagaan_suvarga", 0.010, 0.010, [("ger", 16, 3, 90000, "per_person", True)], ["meals", "solar_power", "stargazing"], ("05-01", "10-15"), "policy_moderate", 4.1),
    ("stay_dalanzadgad_hotel_south", "South Gobi Hotel", "Өмнийн говь зочид буудал", "hotel", "place_dalanzadgad", 0.001, 0.002, [("double_room", 30, 2, 170000, "per_unit", False), ("family_room", 6, 4, 260000, "per_unit", False)], ["wifi", "restaurant", "parking", "airport_transfer"], YEAR, "policy_flexible", 4.1),
    ("stay_yolyn_am_camp", "Gurvan Saikhan Ger Camp", "Гурван сайхан бааз", "ger_camp", "place_yolyn_am", 0.030, 0.050, [("ger", 30, 3, 130000, "per_person", True)], ["meals", "hot_shower", "wifi", "horse_riding"], ("05-01", "10-20"), "policy_moderate", 4.4),
    ("stay_bayanzag_camp", "Flaming Cliffs Camp", "Улаан эрэг бааз", "ger_camp", "place_bayanzag", 0.015, -0.010, [("ger", 20, 3, 115000, "per_person", True)], ["meals", "hot_shower", "stargazing"], ("05-01", "10-15"), "policy_moderate", 4.3),
    ("stay_khongor_camp_dunes", "Singing Dunes Camp", "Дуут манхан бааз", "ger_camp", "place_khongoryn_els", 0.030, 0.020, [("ger", 25, 3, 125000, "per_person", True)], ["meals", "camel_riding", "hot_shower", "sandboarding"], ("05-01", "10-20"), "policy_strict", 4.5),
    ("stay_khongor_herder_family", "Khongor Camel Herder Family", "Хонгорын тэмээчин айл", "house", "place_khongoryn_els", 0.050, -0.040, [("ger", 2, 4, 50000, "per_person", True)], ["meals", "camel_riding", "herding_experience"], YEAR, "policy_flexible", 4.8),
]

stays = []
for i, s in enumerate(STAYS):
    sid, name, name_mn, typ, pid, dlat, dlng, units, amen, season, pol, rating = s
    lng, lat = ll(pid)
    stays.append({
        "_id": sid, "name": name, "name_mn": name_mn, "type": typ, "place_id": pid,
        "aimag": PLACE[pid]["aimag"], "location": pt(round(lat + dlat, 5), round(lng + dlng, 5)),
        "owner": {"name": OWNERS[i % len(OWNERS)], "phone": f"+976 9900 {1001 + i:04d}",
                  "preferred_channel": random.choice(["messenger", "phone", "phone", "messenger", "whatsapp"]),
                  "languages": ["mn"] + (["en"] if typ in ("hotel", "guesthouse") or random.random() < 0.4 else [])},
        "units": [{"unit_type": u[0], "count": u[1], "beds_per_unit": u[2], "price_mnt": u[3],
                   "price_basis": u[4], "meals_included": u[5]} for u in units],
        "total_beds": sum(u[1] * u[2] for u in units),
        "amenities": amen,
        "season": {"year_round": season is None, "open_from": season[0] if season else None,
                   "open_to": season[1] if season else None},
        "cancellation_policy_id": pol, "check_in": "14:00", "check_out": "11:00",
        "payment_methods": ["qpay", "cash"] + (["card"] if typ == "hotel" else []),
        "rating": rating, "reviews_count": random.randint(12, 480), "is_mock": True,
    })
STAY = {s["_id"]: s for s in stays}

# ---------------------------------------------------------------- availability (demo window around build day)
DEMO_START, DEMO_DAYS = date(2026, 10, 1), 14


def open_on(stay, d):
    if stay["season"]["year_round"]:
        return True
    md = d.strftime("%m-%d")
    return stay["season"]["open_from"] <= md <= stay["season"]["open_to"]


availability = []
for s in stays:
    for k in range(DEMO_DAYS):
        d = DEMO_START + timedelta(days=k)
        for u in s["units"]:
            is_open = open_on(s, d)
            booked = random.randint(0, u["count"]) if is_open else u["count"]
            if d.weekday() >= 4 and is_open:  # Fri/Sat busier
                booked = min(u["count"], booked + max(1, u["count"] // 4))
            availability.append({
                "_id": f"avail_{s['_id'][5:]}_{u['unit_type']}_{d.isoformat()}",
                "stay_id": s["_id"], "date": d.isoformat(), "unit_type": u["unit_type"],
                "total": u["count"], "available": u["count"] - booked if is_open else 0,
                "status": "open" if is_open else "closed_for_season",
                "price_mnt": u["price_mnt"],
            })

# ---------------------------------------------------------------- drivers & vehicles
DRIVERS = [
    ("driver_01", "Batjargal", "Батжаргал", ["mn", "ru"], 18, 4.8, ["Khövsgöl", "Bulgan", "Arkhangai"], "place_ub"),
    ("driver_02", "Ganzorig", "Ганзориг", ["mn", "en"], 9, 4.7, ["Ömnögovi", "Dundgovi"], "place_ub"),
    ("driver_03", "Tsogoo", "Цогоо", ["mn"], 25, 4.9, ["Ömnögovi", "Dundgovi", "Övörkhangai"], "place_dalanzadgad"),
    ("driver_04", "Erdene", "Эрдэнэ", ["mn", "en"], 6, 4.5, ["Khövsgöl"], "place_murun"),
    ("driver_05", "Dorj", "Дорж", ["mn"], 14, 4.6, ["Darkhan-Uul", "Selenge", "Orkhon", "Bulgan"], "place_darkhan"),
    ("driver_06", "Munkh-Ochir", "Мөнх-Очир", ["mn", "en", "ko"], 11, 4.7, ["Arkhangai", "Övörkhangai", "Khövsgöl"], "place_ub"),
    ("driver_07", "Bold", "Болд", ["mn"], 20, 4.4, ["Töv", "Bulgan", "Orkhon"], "place_ub"),
    ("driver_08", "Saruul", "Саруул", ["mn", "en"], 5, 4.8, ["Khövsgöl"], "place_khatgal"),
    ("driver_09", "Tuvshin", "Түвшин", ["mn", "zh"], 12, 4.5, ["Ömnögovi"], "place_dalanzadgad"),
    ("driver_10", "Enkhbayar", "Энхбаяр", ["mn"], 16, 4.3, ["Ulaanbaatar", "Darkhan-Uul"], "place_ub"),
    ("driver_11", "Amgalan", "Амгалан", ["mn", "ru"], 22, 4.6, ["Bulgan", "Khövsgöl"], "place_bulgan"),
    ("driver_12", "Nyamaa", "Нямаа", ["mn"], 8, 4.4, ["Dundgovi", "Ömnögovi"], "place_mandalgovi"),
]
drivers = [{
    "_id": d[0], "name": d[1], "name_mn": d[2], "phone": f"+976 8800 {2001 + i:04d}",
    "languages": d[3], "years_experience": d[4], "rating": d[5], "regions_known": d[6],
    "base_place_id": d[7], "vehicle_id": None, "is_mock": True,
} for i, d in enumerate(DRIVERS)]

# id, type, model, seats, offroad, per_day, per_km, driver, base, features
VEHICLES = [
    ("veh_bus_01", "bus", "Hyundai Universe", 45, False, None, None, None, "place_ub", ["ac", "luggage_hold"], "Tsetsens Transport"),
    ("veh_bus_02", "bus", "Hyundai Universe", 45, False, None, None, None, "place_ub", ["ac", "luggage_hold"], "Tsetsens Transport"),
    ("veh_bus_03", "bus", "Yutong ZK6122", 49, False, None, None, None, "place_ub", ["ac", "luggage_hold", "usb_charging"], "Govi Express"),
    ("veh_bus_04", "bus", "Hyundai County", 25, False, None, None, None, "place_ub", ["luggage_hold"], "Khangai Line"),
    ("veh_van_01", "minivan", "UAZ-452 'Furgon'", 8, True, 250000, 1500, "driver_01", "place_ub", ["roof_rack", "offroad"], None),
    ("veh_van_02", "minivan", "UAZ-452 'Furgon'", 8, True, 230000, 1400, "driver_03", "place_dalanzadgad", ["roof_rack", "offroad"], None),
    ("veh_van_03", "minivan", "Toyota Hiace", 12, False, 300000, 1600, "driver_10", "place_ub", ["ac"], None),
    ("veh_van_04", "minivan", "Mitsubishi Delica", 7, True, 260000, 1500, "driver_04", "place_murun", ["4x4"], None),
    ("veh_suv_01", "suv", "Toyota Land Cruiser 70", 5, True, 380000, 2000, "driver_02", "place_ub", ["4x4", "ac", "fridge", "sat_phone"], None),
    ("veh_suv_02", "suv", "Toyota Land Cruiser 200", 5, True, 450000, 2300, "driver_06", "place_ub", ["4x4", "ac", "wifi_hotspot"], None),
    ("veh_suv_03", "suv", "Toyota Land Cruiser 105", 5, True, 350000, 1900, "driver_09", "place_dalanzadgad", ["4x4", "ac"], None),
    ("veh_suv_04", "suv", "Nissan Patrol", 5, True, 340000, 1800, "driver_11", "place_bulgan", ["4x4"], None),
    ("veh_suv_05", "suv", "Toyota Land Cruiser Prado", 5, True, 320000, 1800, "driver_08", "place_khatgal", ["4x4", "ac"], None),
    ("veh_sedan_01", "sedan", "Toyota Prius 30", 4, False, 120000, 800, "driver_05", "place_darkhan", ["ac"], None),
    ("veh_sedan_02", "sedan", "Toyota Prius 41", 4, False, 130000, 800, "driver_07", "place_ub", ["ac"], None),
    ("veh_van_05", "minivan", "Hyundai Starex", 9, False, 220000, 1300, "driver_12", "place_mandalgovi", ["ac"], None),
]
vehicles = []
for i, v in enumerate(VEHICLES):
    lng, lat = ll(v[8])
    vehicles.append({
        "_id": v[0], "type": v[1], "model": v[2], "seats": v[3], "offroad_capable": v[4],
        "rental": None if v[5] is None else {"price_per_day_mnt": v[5], "price_per_km_mnt": v[6], "includes_driver": True, "fuel_included": False},
        "driver_id": v[7], "operator": v[10], "base_place_id": v[8],
        "plate": f"{1000 + i * 37 % 9000:04d} УБ{'АБВГДЕЖ'[i % 7]}",
        "features": v[9], "current_location": pt(round(lat + random.uniform(-0.01, 0.01), 5), round(lng + random.uniform(-0.01, 0.01), 5)),
        "status": random.choice(["available", "available", "available", "on_trip"]) if v[7] else "scheduled",
        "is_mock": True,
    })
for v in vehicles:
    if v["driver_id"]:
        next(d for d in drivers if d["_id"] == v["driver_id"])["vehicle_id"] = v["_id"]

# ---------------------------------------------------------------- transport schedules (bus, shared van, flights)
DAILY = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SCHED = [
    # id, mode, operator, route, from, to, terminal, days, times, duration_min, price, seats, vehicle
    ("sched_bus_ub_darkhan", "bus", "Tsetsens Transport", "route_ub_darkhan", "place_ub", "place_darkhan", "Dragon bus terminal", DAILY, ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"], 210, 17000, 45, "veh_bus_01"),
    ("sched_bus_ub_erdenet", "bus", "Tsetsens Transport", "route_ub_bulgan_via_erdenet", "place_ub", "place_erdenet", "Dragon bus terminal", DAILY, ["09:00", "13:00", "17:00"], 360, 26000, 45, "veh_bus_02"),
    ("sched_bus_ub_bulgan", "bus", "Khangai Line", "route_ub_bulgan_via_lun", "place_ub", "place_bulgan", "Dragon bus terminal", DAILY, ["08:00", "14:00"], 330, 32000, 25, "veh_bus_04"),
    ("sched_bus_ub_murun", "bus", "Khangai Line", "route_ub_khatgal_via_lun", "place_ub", "place_murun", "Dragon bus terminal", DAILY, ["08:00", "17:00"], 720, 58000, 45, "veh_bus_02"),
    ("sched_van_murun_khatgal", "shared_van", "Mörön market van stand", "route_ub_khatgal_via_lun", "place_murun", "place_khatgal", "Mörön market", DAILY, ["10:00", "15:00"], 100, 20000, 8, "veh_van_04"),
    ("sched_bus_ub_tsetserleg", "bus", "Khangai Line", "route_ub_murun_central", "place_ub", "place_tsetserleg", "Dragon bus terminal", DAILY, ["08:00", "14:00"], 480, 38000, 25, "veh_bus_04"),
    ("sched_bus_ub_kharkhorin", "bus", "Khangai Line", "route_ub_murun_central", "place_ub", "place_kharkhorin", "Dragon bus terminal", DAILY, ["11:00"], 330, 30000, 25, "veh_bus_04"),
    ("sched_bus_ub_mandalgovi", "bus", "Govi Express", "route_ub_dalanzadgad", "place_ub", "place_mandalgovi", "Dragon bus terminal", DAILY, ["09:00", "15:00"], 240, 25000, 49, "veh_bus_03"),
    ("sched_bus_ub_dalanzadgad", "bus", "Govi Express", "route_ub_dalanzadgad", "place_ub", "place_dalanzadgad", "Dragon bus terminal", DAILY, ["08:00", "16:00"], 540, 45000, 49, "veh_bus_03"),
    ("sched_flight_ub_murun", "flight", "Hunnu Air (mock)", None, "place_ub", "place_murun", "Chinggis Khaan Intl Airport", ["tue", "fri", "sun"], ["09:30"], 90, 360000, 70, None),
    ("sched_flight_ub_dalanzadgad", "flight", "Aero Mongolia (mock)", None, "place_ub", "place_dalanzadgad", "Chinggis Khaan Intl Airport", DAILY, ["07:40", "15:20"], 80, 295000, 70, None),
]
schedules = [{
    "_id": s[0], "mode": s[1], "operator": s[2], "route_id": s[3], "from_place_id": s[4], "to_place_id": s[5],
    "departure_point": s[6], "days_of_week": s[7], "departure_times": s[8], "duration_min": s[9],
    "price_mnt": s[10], "seats": s[11], "vehicle_id": s[12],
    "booking_channel": {"bus": "ticket office or eticket app", "shared_van": "pay the driver, leaves when full", "flight": "airline website"}[s[1]],
    "is_mock": True,
} for s in SCHED]

# ---------------------------------------------------------------- demo trips, itinerary versions, bookings
trips = [
    {"_id": "trip_demo_khuvsgul", "title": "Family trip to Khövsgöl Lake", "user": {"name": "Oyuka", "lang": "mn", "phone": "+976 9911 0001"},
     "party": {"adults": 2, "children": 2}, "start_date": "2026-10-02", "end_date": "2026-10-06",
     "route_id": "route_ub_khatgal_via_erdenet", "vehicle_id": "veh_suv_02", "driver_id": "driver_06",
     "current_version": 2, "status": "in_progress", "created_at": "2026-09-25T09:12:00Z"},
    {"_id": "trip_demo_gobi", "title": "Gobi highlights for two", "user": {"name": "Lea", "lang": "en", "phone": "+49 151 0000 0000"},
     "party": {"adults": 2, "children": 0}, "start_date": "2026-10-08", "end_date": "2026-10-12",
     "route_id": "route_ub_dalanzadgad", "vehicle_id": "veh_suv_01", "driver_id": "driver_02",
     "current_version": 1, "status": "planned", "created_at": "2026-09-27T14:40:00Z"},
]

itinerary_versions = [
    {"_id": "itin_khuvsgul_v1", "trip_id": "trip_demo_khuvsgul", "version": 1, "created_at": "2026-09-25T09:15:00Z",
     "reason": "initial_plan", "days": [
        {"day": 1, "date": "2026-10-02", "from_place_id": "place_ub", "to_place_id": "place_bulgan", "route_id": "route_ub_bulgan_via_erdenet", "stay_id": "stay_bulgan_hotel_khan"},
        {"day": 2, "date": "2026-10-03", "from_place_id": "place_bulgan", "to_place_id": "place_khatgal", "route_id": "route_ub_khatgal_via_erdenet", "stay_id": "stay_khatgal_camp_blue_pearl", "event_ids": ["event_khatgal_season_close_race"]},
        {"day": 3, "date": "2026-10-04", "from_place_id": "place_khatgal", "to_place_id": "place_khatgal", "stay_id": "stay_khatgal_camp_blue_pearl"},
        {"day": 4, "date": "2026-10-05", "from_place_id": "place_khatgal", "to_place_id": "place_murun", "stay_id": "stay_murun_hotel_delger"},
        {"day": 5, "date": "2026-10-06", "from_place_id": "place_murun", "to_place_id": "place_ub", "route_id": "route_ub_khatgal_via_lun"}]},
    {"_id": "itin_khuvsgul_v2", "trip_id": "trip_demo_khuvsgul", "version": 2, "created_at": "2026-10-02T15:05:00Z",
     "reason": "delay", "change_request": "Хүүхэд өвдөөд 4 цаг хоцорлоо, өнөөдөр Булган хүрэхгүй нь. Эрдэнэтэд хонох уу?",
     "agent_summary": "Stop in Erdenet tonight instead of Bulgan, cancel the Bulgan hotel (flexible policy, under 24h so 50% refund), day 2 becomes a longer drive to Khatgal, rest of the plan unchanged.",
     "days": [
        {"day": 1, "date": "2026-10-02", "from_place_id": "place_ub", "to_place_id": "place_erdenet", "route_id": "route_ub_bulgan_via_erdenet", "stay_id": "stay_erdenet_hotel_copper"},
        {"day": 2, "date": "2026-10-03", "from_place_id": "place_erdenet", "to_place_id": "place_khatgal", "route_id": "route_ub_khatgal_via_erdenet", "stay_id": "stay_khatgal_camp_blue_pearl", "event_ids": ["event_khatgal_season_close_race"], "note": "Long day, ~9h driving"},
        {"day": 3, "date": "2026-10-04", "from_place_id": "place_khatgal", "to_place_id": "place_khatgal", "stay_id": "stay_khatgal_camp_blue_pearl"},
        {"day": 4, "date": "2026-10-05", "from_place_id": "place_khatgal", "to_place_id": "place_murun", "stay_id": "stay_murun_hotel_delger"},
        {"day": 5, "date": "2026-10-06", "from_place_id": "place_murun", "to_place_id": "place_ub", "route_id": "route_ub_khatgal_via_lun"}]},
    {"_id": "itin_gobi_v1", "trip_id": "trip_demo_gobi", "version": 1, "created_at": "2026-09-27T14:45:00Z",
     "reason": "initial_plan", "days": [
        {"day": 1, "date": "2026-10-08", "from_place_id": "place_ub", "to_place_id": "place_tsagaan_suvarga", "route_id": "route_mandalgovi_tsagaan_suvarga", "stay_id": "stay_tsagaan_suvarga_camp"},
        {"day": 2, "date": "2026-10-09", "from_place_id": "place_tsagaan_suvarga", "to_place_id": "place_yolyn_am", "route_id": "route_dalanzadgad_yolyn_am", "stay_id": "stay_yolyn_am_camp"},
        {"day": 3, "date": "2026-10-10", "from_place_id": "place_yolyn_am", "to_place_id": "place_khongoryn_els", "route_id": "route_dalanzadgad_khongoryn_els", "stay_id": "stay_khongor_camp_dunes", "event_ids": ["event_gobi_autumn_camel_race"]},
        {"day": 4, "date": "2026-10-11", "from_place_id": "place_khongoryn_els", "to_place_id": "place_bayanzag", "route_id": "route_bayanzag_khongoryn_els", "stay_id": "stay_bayanzag_camp"},
        {"day": 5, "date": "2026-10-12", "from_place_id": "place_bayanzag", "to_place_id": "place_ub", "route_id": "route_ub_dalanzadgad"}]},
]


def stay_price(stay_id, unit_type, guests, nights):
    u = next(x for x in STAY[stay_id]["units"] if x["unit_type"] == unit_type)
    return u["price_mnt"] * nights * (guests if u["price_basis"] == "per_person" else 1)


BOOK = [
    ("booking_001", "trip_demo_khuvsgul", "stay", "stay_bulgan_hotel_khan", "family_room", "2026-10-02", 1, 4, "cancelled", "Cancelled by agent in itinerary v2"),
    ("booking_002", "trip_demo_khuvsgul", "stay", "stay_erdenet_hotel_copper", "double_room", "2026-10-02", 1, 4, "confirmed", "Created by agent in itinerary v2 (2 rooms)"),
    ("booking_003", "trip_demo_khuvsgul", "stay", "stay_khatgal_camp_blue_pearl", "ger", "2026-10-03", 2, 4, "confirmed", ""),
    ("booking_004", "trip_demo_khuvsgul", "stay", "stay_murun_hotel_delger", "family_room", "2026-10-05", 1, 4, "confirmed", ""),
    ("booking_005", "trip_demo_gobi", "stay", "stay_tsagaan_suvarga_camp", "ger", "2026-10-08", 1, 2, "confirmed", ""),
    ("booking_006", "trip_demo_gobi", "stay", "stay_yolyn_am_camp", "ger", "2026-10-09", 1, 2, "pending_owner", "Owner replies on Messenger"),
    ("booking_007", "trip_demo_gobi", "stay", "stay_khongor_camp_dunes", "ger", "2026-10-10", 1, 2, "confirmed", ""),
    ("booking_008", "trip_demo_gobi", "stay", "stay_bayanzag_camp", "ger", "2026-10-11", 1, 2, "confirmed", ""),
]
bookings = []
for b in BOOK:
    bid, tid, kind, sid, unit, start, nights, guests, status, note = b
    total = stay_price(sid, unit, guests, nights) * (2 if unit == "double_room" and guests > 2 else 1)
    end = (date.fromisoformat(start) + timedelta(days=nights)).isoformat()
    bookings.append({
        "_id": bid, "trip_id": tid, "kind": kind, "stay_id": sid, "unit_type": unit,
        "check_in": start, "check_out": end, "nights": nights, "guests": guests,
        "total_price_mnt": total, "deposit_paid_mnt": int(total * 0.3) if status != "pending_owner" else 0,
        "cancellation_policy_id": STAY[sid]["cancellation_policy_id"], "status": status,
        "payment_method": "qpay", "note": note, "is_mock": True,
    })
bookings += [
    {"_id": "booking_009", "trip_id": "trip_demo_khuvsgul", "kind": "vehicle", "vehicle_id": "veh_suv_02", "driver_id": "driver_06",
     "start_date": "2026-10-02", "end_date": "2026-10-06", "days": 5, "total_price_mnt": 5 * 450000,
     "deposit_paid_mnt": 675000, "status": "confirmed", "payment_method": "qpay", "note": "Driver with car, fuel extra", "is_mock": True},
    {"_id": "booking_010", "trip_id": "trip_demo_gobi", "kind": "vehicle", "vehicle_id": "veh_suv_01", "driver_id": "driver_02",
     "start_date": "2026-10-08", "end_date": "2026-10-12", "days": 5, "total_price_mnt": 5 * 380000,
     "deposit_paid_mnt": 570000, "status": "confirmed", "payment_method": "qpay", "note": "English-speaking driver", "is_mock": True},
]

# ---------------------------------------------------------------- west & east expansion
# Appended after everything above and with its own RNG, so the original north/south data stays identical.
rnd = random.Random(2026)

for p in [
    ("place_olgii", "Ölgii", "Өлгий", "Bayan-Ölgii", "aimag_center", 48.9683, 89.9650, True, "Kazakh-majority town, gateway to the Altai; Golden Eagle Festival."),
    ("place_tavan_bogd", "Altai Tavan Bogd (Tsagaan Gol)", "Алтай Таван Богд", "Bayan-Ölgii", "attraction", 49.1500, 87.9000, False, "Potanin glacier base camp area; permits needed near the border."),
    ("place_khovd", "Khovd", "Ховд", "Khovd", "aimag_center", 48.0056, 91.6419, True, "Western hub city, airport, bus to UB."),
    ("place_khar_us", "Khar Us Lake", "Хар ус нуур", "Khovd", "attraction", 48.0500, 92.3000, False, "Reed-lined lake, birdwatching."),
    ("place_ulaangom", "Ulaangom", "Улаангом", "Uvs", "aimag_center", 49.9811, 92.0667, True, "Uvs aimag center, near Uvs Lake."),
    ("place_uvs_lake", "Uvs Lake", "Увс нуур", "Uvs", "attraction", 50.3000, 92.7000, False, "Largest lake in Mongolia, salty, UNESCO basin."),
    ("place_uliastai", "Uliastai", "Улиастай", "Zavkhan", "aimag_center", 47.7417, 96.8444, True, "Zavkhan aimag center in a mountain valley."),
    ("place_altai_city", "Altai", "Алтай", "Govi-Altai", "aimag_center", 46.3722, 96.2583, True, "Govi-Altai aimag center."),
    ("place_chinggis_city", "Chinggis city (Öndörkhaan)", "Чингис хот", "Khentii", "aimag_center", 47.3194, 110.6556, True, "Khentii aimag center, first stop going east."),
    ("place_dadal", "Dadal", "Дадал", "Khentii", "soum_center", 49.0236, 111.6264, True, "Forested soum, said to be Chinggis Khaan's birthplace."),
    ("place_choibalsan", "Choibalsan", "Чойбалсан", "Dornod", "aimag_center", 48.0706, 114.5228, True, "Largest eastern city, airport, rail to Russia."),
    ("place_baruun_urt", "Baruun-Urt", "Баруун-Урт", "Sükhbaatar", "aimag_center", 46.6806, 113.2792, True, "Sükhbaatar aimag center, open eastern steppe."),
    ("place_shiliin_bogd", "Shiliin Bogd Mountain", "Шилийн Богд уул", "Sükhbaatar", "attraction", 45.4700, 114.5900, False, "Sacred extinct volcano, sunrise pilgrimage; border permit."),
]:
    places.append({"_id": p[0], "name": p[1], "name_mn": p[2], "aimag": p[3], "kind": p[4],
                   "location": pt(p[5], p[6]), "fuel_available": p[7], "note": p[8]})
    PLACE[p[0]] = places[-1]

L.update({
    "tsetserleg_uliastai": lambda: seg("place_tsetserleg", "place_uliastai", "mixed", [[100.40, 47.60], [99.00, 47.70], [97.80, 47.75]], condition="fair", notes="Long mountain road, paved in parts, passes Tosontsengel.", hazards=["long_no_fuel", "livestock_on_road"]),
    "uliastai_khovd": lambda: seg("place_uliastai", "place_khovd", "mixed", [[95.50, 47.90], [94.00, 48.00], [92.80, 48.00]], condition="fair", notes="Mixed paved and gravel, very few services.", hazards=["long_no_fuel", "no_signal"]),
    "khovd_olgii": lambda: seg("place_khovd", "place_olgii", "paved", [[91.20, 48.40], [90.50, 48.70]], notes="Paved mountain road with passes."),
    "olgii_tavan_bogd": lambda: seg("place_olgii", "place_tavan_bogd", "dirt", [[89.40, 49.00], [88.60, 49.10]], condition="poor", notes="Rough track, river crossings; border-zone permit checked on the way.", hazards=["river_crossing", "no_signal", "snow_early_autumn"]),
    "khovd_khar_us": lambda: seg("place_khovd", "place_khar_us", "mixed", []),
    "khovd_ulaangom": lambda: seg("place_khovd", "place_ulaangom", "paved", [[91.80, 48.70], [92.00, 49.40]]),
    "ulaangom_uvs_lake": lambda: seg("place_ulaangom", "place_uvs_lake", "dirt", [[92.40, 50.15]], condition="fair", notes="Flat steppe track to the lake shore."),
    "ub_chinggis": lambda: seg("place_ub", "place_chinggis_city", "paved", [[107.50, 47.80], [108.50, 47.60], [109.60, 47.40]], notes="Paved east highway, passes the Chinggis Khaan statue turnoff."),
    "chinggis_choibalsan": lambda: seg("place_chinggis_city", "place_choibalsan", "paved", [[111.80, 47.50], [113.20, 47.80]], notes="Long straight steppe road, watch for gazelles.", hazards=["wildlife_on_road", "long_no_fuel"]),
    "chinggis_dadal": lambda: seg("place_chinggis_city", "place_dadal", "mixed", [[110.90, 48.00], [111.20, 48.50]], condition="fair", notes="Paved to Binder, then gravel through forest.", hazards=["mud_after_rain"]),
    "chinggis_baruun_urt": lambda: seg("place_chinggis_city", "place_baruun_urt", "paved", [[111.60, 47.00], [112.50, 46.80]]),
    "baruun_urt_shiliin_bogd": lambda: seg("place_baruun_urt", "place_shiliin_bogd", "dirt", [[113.60, 46.20], [114.10, 45.80]], condition="fair", notes="Open steppe tracks, navigate by GPS.", hazards=["no_signal", "long_no_fuel"]),
})

for rid, name, area, legs, summary in [
    ("route_ub_khovd_central", "Ulaanbaatar to Khovd via Tsetserleg and Uliastai", "west", ["ub_kharkhorin", "kharkhorin_tsetserleg", "tsetserleg_uliastai", "uliastai_khovd"], "3 to 4 days of driving; most people fly to Khovd or Ölgii instead."),
    ("route_khovd_olgii", "Khovd to Ölgii", "west", ["khovd_olgii"], "Paved half-day drive through the Altai foothills."),
    ("route_olgii_tavan_bogd", "Ölgii to Altai Tavan Bogd", "west", ["olgii_tavan_bogd"], "Expedition road to the glaciers, 4x4 only, June to September."),
    ("route_khovd_khar_us", "Khovd to Khar Us Lake", "west", ["khovd_khar_us"], "Short trip for birdwatching."),
    ("route_khovd_uvs_lake", "Khovd to Uvs Lake via Ulaangom", "west", ["khovd_ulaangom", "ulaangom_uvs_lake"], "Paved to Ulaangom, then steppe track."),
    ("route_ub_chinggis", "Ulaanbaatar to Chinggis city", "east", ["ub_chinggis"], "Easy paved drive east, one day."),
    ("route_ub_choibalsan", "Ulaanbaatar to Choibalsan", "east", ["ub_chinggis", "chinggis_choibalsan"], "Fully paved but long; usually split in Chinggis city."),
    ("route_chinggis_dadal", "Chinggis city to Dadal", "east", ["chinggis_dadal"], "Forest and rivers, Chinggis Khaan birthplace sites."),
    ("route_ub_shiliin_bogd", "Ulaanbaatar to Shiliin Bogd via Baruun-Urt", "east", ["ub_chinggis", "chinggis_baruun_urt", "baruun_urt_shiliin_bogd"], "Remote steppe trip; last part is off-road."),
]:
    segs = [L[k]() for k in legs]
    for i, s in enumerate(segs):
        s["seq"] = i + 1
    by_surface = {}
    for s in segs:
        by_surface[s["surface"]] = by_surface.get(s["surface"], 0) + s["distance_km"]
    coords = []
    for s in segs:
        coords += s["geometry"]["coordinates"] if not coords else s["geometry"]["coordinates"][1:]
    mins = sum(s["drive_time_min"] for s in segs)
    routes.append({
        "_id": rid, "name": name, "region": area,
        "from_place_id": segs[0]["from_place_id"], "to_place_id": segs[-1]["to_place_id"],
        "waypoint_place_ids": [segs[0]["from_place_id"]] + [s["to_place_id"] for s in segs],
        "total_distance_km": sum(s["distance_km"] for s in segs), "total_drive_time_min": mins,
        "recommended_days": max(1, math.ceil(mins / 60 / 8)), "surface_km": by_surface,
        "vehicle_min": "suv_4x4" if any(s["surface"] == "dirt" or "sand_stuck_risk" in s["hazards"] for s in segs) else "sedan",
        "summary": summary, "segments": segs, "geometry": {"type": "LineString", "coordinates": coords},
    })

for e in [
    ("event_golden_eagle_festival_2026", "Golden Eagle Festival", "Бүргэдийн баяр", "place_olgii", "festival", "2026-10-03", "2026-10-04", 60000, 5000, 2.8, "Kazakh eagle hunters compete; hotels in Ölgii sell out."),
    ("event_olgii_nauryz_2027", "Nauryz (Kazakh New Year)", "Наурыз", "place_olgii", "festival", "2027-03-22", "2027-03-22", 0, 6000, 1.5, "Kazakh spring new year, music, food and horse games."),
    ("event_khovd_naadam_2027", "Khovd Aimag Naadam", "Ховд аймгийн наадам", "place_khovd", "naadam", "2027-07-07", "2027-07-08", 5000, 11000, 1.8, "Western naadam with many ethnic groups taking part."),
    ("event_uvs_naadam_2027", "Uvs Aimag Naadam", "Увс аймгийн наадам", "place_ulaangom", "naadam", "2027-07-08", "2027-07-09", 5000, 8000, 1.7, "Aimag naadam in Ulaangom."),
    ("event_zavkhan_naadam_2027", "Zavkhan Aimag Naadam", "Завхан аймгийн наадам", "place_uliastai", "naadam", "2027-07-06", "2027-07-07", 5000, 7000, 1.6, "Mountain-valley naadam in Uliastai."),
    ("event_khentii_naadam_2027", "Khentii Aimag Naadam", "Хэнтий аймгийн наадам", "place_chinggis_city", "naadam", "2027-07-07", "2027-07-08", 5000, 9000, 1.7, "Held in Chinggis city."),
    ("event_dornod_naadam_2027", "Dornod Aimag Naadam", "Дорнод аймгийн наадам", "place_choibalsan", "naadam", "2027-07-08", "2027-07-09", 5000, 10000, 1.7, "Largest naadam in the east."),
    ("event_sukhbaatar_horse_festival_2027", "Sükhbaatar Horse Festival", "Сүхбаатар аймгийн морин наадам", "place_baruun_urt", "sport", "2027-08-14", "2027-08-15", 5000, 4000, 1.5, "Famous eastern steppe horses, long-distance races."),
    ("event_dadal_chinggis_day_2026", "Chinggis Khaan Day in Dadal", "Их Эзэн Чингис хааны өдөр (Дадал)", "place_dadal", "national_holiday", "2026-11-11", "2026-11-11", 0, 2000, 1.4, "Ceremonies at the birthplace monuments on the lunar-calendar holiday."),
    ("event_playtime_festival_2027", "Playtime Festival", "Playtime наадам", "place_ub", "music_festival", "2027-07-02", "2027-07-04", 250000, 20000, 1.6, "Biggest rock and pop music festival, open-air stage on the outskirts of Ulaanbaatar with camping."),
]:
    events.append({
        "_id": e[0], "name": e[1], "name_mn": e[2], "place_id": e[3], "aimag": PLACE[e[3]]["aimag"],
        "location": PLACE[e[3]]["location"], "category": e[4], "start_date": e[5], "end_date": e[6],
        "ticket_price_mnt": e[7], "expected_attendance": e[8], "stay_demand_multiplier": e[9],
        "description": e[10], "date_confidence": "approximate", "is_mock": True,
    })

NEW_STAYS = [
    ("stay_olgii_guesthouse_kazakh", "Altai Kazakh Guesthouse", "Алтай казах гэр буудал", "guesthouse", "place_olgii", 0.002, 0.003, [("double_room", 8, 2, 90000, "per_unit", True), ("ger", 4, 4, 45000, "per_person", True)], ["wifi", "meals", "tour_desk", "eagle_hunter_visit"], YEAR, "policy_flexible", 4.6),
    ("stay_olgii_hotel_eagle", "Golden Eagle Hotel Ölgii", "Алтан бүргэд зочид буудал", "hotel", "place_olgii", 0.001, -0.002, [("double_room", 20, 2, 150000, "per_unit", False)], ["wifi", "restaurant", "parking"], YEAR, "policy_strict", 4.0),
    ("stay_tavan_bogd_camp", "Tavan Bogd Base Camp", "Таван Богд бааз", "ger_camp", "place_tavan_bogd", 0.010, 0.020, [("ger", 10, 3, 100000, "per_person", True)], ["meals", "guided_hike", "horse_riding"], ("06-15", "09-15"), "policy_moderate", 4.4),
    ("stay_olgii_eagle_hunter_family", "Eagle Hunter Family Ger", "Бүргэдчин айлын гэр", "house", "place_olgii", 0.080, -0.060, [("ger", 2, 4, 55000, "per_person", True)], ["meals", "eagle_hunter_visit", "horse_riding"], YEAR, "policy_flexible", 4.9),
    ("stay_khovd_hotel_buyant", "Buyant River Hotel", "Буянт голын зочид буудал", "hotel", "place_khovd", 0.001, 0.002, [("double_room", 24, 2, 140000, "per_unit", False), ("family_room", 4, 4, 220000, "per_unit", False)], ["wifi", "restaurant", "parking", "airport_transfer"], YEAR, "policy_flexible", 4.1),
    ("stay_khar_us_camp", "Khar Us Reed Camp", "Хар ус бааз", "ger_camp", "place_khar_us", 0.006, 0.008, [("ger", 10, 3, 80000, "per_person", True)], ["meals", "birdwatching", "boat_trips"], ("05-20", "09-30"), "policy_moderate", 4.0),
    ("stay_uliastai_hotel", "Zavkhan Hotel Uliastai", "Завхан зочид буудал", "hotel", "place_uliastai", 0.001, 0.001, [("double_room", 14, 2, 110000, "per_unit", False)], ["wifi", "restaurant"], YEAR, "policy_flexible", 3.8),
    ("stay_uvs_lake_camp", "Uvs Lake Ger Camp", "Увс нуур бааз", "ger_camp", "place_uvs_lake", -0.010, 0.020, [("ger", 12, 3, 85000, "per_person", True)], ["meals", "hot_shower", "fishing"], ("06-01", "09-20"), "policy_moderate", 4.1),
    ("stay_chinggis_hotel_kherlen", "Kherlen Hotel", "Хэрлэн зочид буудал", "hotel", "place_chinggis_city", 0.001, 0.002, [("double_room", 18, 2, 120000, "per_unit", False)], ["wifi", "restaurant", "parking"], YEAR, "policy_flexible", 3.9),
    ("stay_dadal_camp_gurvan_nuur", "Gurvan Nuur Camp Dadal", "Гурван нуур бааз", "ger_camp", "place_dadal", 0.010, -0.010, [("ger", 15, 3, 90000, "per_person", True), ("wooden_cabin", 6, 4, 120000, "per_person", True)], ["meals", "sauna", "fishing", "horse_riding"], ("05-25", "10-10"), "policy_moderate", 4.3),
    ("stay_dadal_log_house", "Onon River Log House", "Онон голын модон байшин", "house", "place_dadal", 0.030, 0.040, [("whole_house", 1, 8, 300000, "per_unit", False)], ["kitchen", "sauna", "fireplace", "fishing"], YEAR, "policy_deposit_only", 4.7),
    ("stay_choibalsan_hotel_kherlen", "Eastern Steppe Hotel", "Дорнод тал зочид буудал", "hotel", "place_choibalsan", 0.001, -0.001, [("double_room", 28, 2, 150000, "per_unit", False), ("family_room", 6, 4, 230000, "per_unit", False)], ["wifi", "restaurant", "parking", "airport_transfer"], YEAR, "policy_flexible", 4.0),
    ("stay_baruun_urt_herder_family", "Dariganga Horse Herder Family", "Дарьгангын адуучин айл", "house", "place_baruun_urt", -0.060, 0.070, [("ger", 2, 4, 45000, "per_person", True)], ["meals", "herding_experience", "horse_riding"], YEAR, "policy_flexible", 4.8),
]
for s in NEW_STAYS:
    sid, name, name_mn, typ, pid, dlat, dlng, units, amen, season, pol, rating = s
    lng, lat = ll(pid)
    i = len(stays)
    stays.append({
        "_id": sid, "name": name, "name_mn": name_mn, "type": typ, "place_id": pid,
        "aimag": PLACE[pid]["aimag"], "location": pt(round(lat + dlat, 5), round(lng + dlng, 5)),
        "owner": {"name": OWNERS[i % len(OWNERS)], "phone": f"+976 9900 {1001 + i:04d}",
                  "preferred_channel": rnd.choice(["messenger", "phone", "phone", "messenger", "whatsapp"]),
                  "languages": ["mn"] + (["kk"] if PLACE[pid]["aimag"] == "Bayan-Ölgii" else []) + (["en"] if typ in ("hotel", "guesthouse") else [])},
        "units": [{"unit_type": u[0], "count": u[1], "beds_per_unit": u[2], "price_mnt": u[3],
                   "price_basis": u[4], "meals_included": u[5]} for u in units],
        "total_beds": sum(u[1] * u[2] for u in units), "amenities": amen,
        "season": {"year_round": season is None, "open_from": season[0] if season else None,
                   "open_to": season[1] if season else None},
        "cancellation_policy_id": pol, "check_in": "14:00", "check_out": "11:00",
        "payment_methods": ["qpay", "cash"] + (["card"] if typ == "hotel" else []),
        "rating": rating, "reviews_count": rnd.randint(8, 300), "is_mock": True,
    })
    st = stays[-1]
    STAY[sid] = st
    for k in range(DEMO_DAYS):
        d = DEMO_START + timedelta(days=k)
        for u in st["units"]:
            is_open = open_on(st, d)
            booked = rnd.randint(0, u["count"]) if is_open else u["count"]
            if sid == "stay_olgii_hotel_eagle" and d.isoformat() in ("2026-10-02", "2026-10-03", "2026-10-04"):
                booked = u["count"]  # Golden Eagle Festival sell-out
            availability.append({
                "_id": f"avail_{sid[5:]}_{u['unit_type']}_{d.isoformat()}", "stay_id": sid, "date": d.isoformat(),
                "unit_type": u["unit_type"], "total": u["count"], "available": u["count"] - booked if is_open else 0,
                "status": "open" if is_open else "closed_for_season", "price_mnt": u["price_mnt"],
            })

for i, d in enumerate([
    ("driver_13", "Serik", "Серик", ["kk", "mn", "en"], 15, 4.9, ["Bayan-Ölgii", "Khovd", "Uvs"], "place_olgii"),
    ("driver_14", "Otgonbaatar", "Отгонбаатар", ["mn", "ru"], 19, 4.6, ["Khovd", "Zavkhan", "Govi-Altai", "Uvs"], "place_khovd"),
    ("driver_15", "Gantulga", "Гантулга", ["mn", "en"], 10, 4.7, ["Khentii", "Dornod", "Sükhbaatar"], "place_ub"),
    ("driver_16", "Byambaa", "Бямбаа", ["mn"], 24, 4.5, ["Dornod", "Sükhbaatar"], "place_choibalsan"),
], start=len(drivers)):
    drivers.append({"_id": d[0], "name": d[1], "name_mn": d[2], "phone": f"+976 8800 {2001 + i:04d}",
                    "languages": d[3], "years_experience": d[4], "rating": d[5], "regions_known": d[6],
                    "base_place_id": d[7], "vehicle_id": None, "is_mock": True})
for i, v in enumerate([
    ("veh_suv_06", "suv", "Toyota Land Cruiser 76", 5, True, 400000, 2100, "driver_13", "place_olgii", ["4x4", "roof_rack", "sat_phone"], None),
    ("veh_van_06", "minivan", "UAZ-452 'Furgon'", 8, True, 260000, 1500, "driver_14", "place_khovd", ["roof_rack", "offroad"], None),
    ("veh_suv_07", "suv", "Toyota Land Cruiser 200", 5, True, 420000, 2200, "driver_15", "place_ub", ["4x4", "ac"], None),
    ("veh_van_07", "minivan", "Toyota Hiace 4WD", 10, True, 280000, 1600, "driver_16", "place_choibalsan", ["4x4", "ac"], None),
    ("veh_bus_05", "bus", "Yutong ZK6122", 49, False, None, None, None, "place_ub", ["ac", "luggage_hold"], "Baruun Zam Transport"),
    ("veh_bus_06", "bus", "Hyundai Universe", 45, False, None, None, None, "place_ub", ["ac", "luggage_hold"], "Zuun Zam Transport"),
], start=len(vehicles)):
    lng, lat = ll(v[8])
    vehicles.append({
        "_id": v[0], "type": v[1], "model": v[2], "seats": v[3], "offroad_capable": v[4],
        "rental": None if v[5] is None else {"price_per_day_mnt": v[5], "price_per_km_mnt": v[6], "includes_driver": True, "fuel_included": False},
        "driver_id": v[7], "operator": v[10], "base_place_id": v[8],
        "plate": f"{1000 + i * 37 % 9000:04d} УБ{'АБВГДЕЖ'[i % 7]}", "features": v[9],
        "current_location": pt(round(lat + rnd.uniform(-0.01, 0.01), 5), round(lng + rnd.uniform(-0.01, 0.01), 5)),
        "status": "available" if v[7] else "scheduled", "is_mock": True,
    })
    if v[7]:
        next(d for d in drivers if d["_id"] == v[7])["vehicle_id"] = v[0]

for s in [
    ("sched_bus_ub_khovd", "bus", "Baruun Zam Transport", "route_ub_khovd_central", "place_ub", "place_khovd", "Dragon bus terminal", ["mon", "wed", "fri"], ["16:00"], 1680, 110000, 49, "veh_bus_05"),
    ("sched_bus_ub_chinggis", "bus", "Zuun Zam Transport", "route_ub_chinggis", "place_ub", "place_chinggis_city", "Bayanzürkh east terminal", DAILY, ["09:00", "15:00"], 330, 28000, 45, "veh_bus_06"),
    ("sched_bus_ub_choibalsan", "bus", "Zuun Zam Transport", "route_ub_choibalsan", "place_ub", "place_choibalsan", "Bayanzürkh east terminal", DAILY, ["08:00"], 720, 55000, 45, "veh_bus_06"),
    ("sched_flight_ub_olgii", "flight", "Aero Mongolia (mock)", None, "place_ub", "place_olgii", "Chinggis Khaan Intl Airport", ["mon", "thu", "sat"], ["08:30"], 210, 520000, 70, None),
    ("sched_flight_ub_khovd", "flight", "Hunnu Air (mock)", None, "place_ub", "place_khovd", "Chinggis Khaan Intl Airport", ["tue", "fri"], ["10:00"], 180, 480000, 70, None),
    ("sched_flight_ub_choibalsan", "flight", "Hunnu Air (mock)", None, "place_ub", "place_choibalsan", "Chinggis Khaan Intl Airport", ["wed", "sun"], ["11:20"], 100, 330000, 70, None),
]:
    schedules.append({
        "_id": s[0], "mode": s[1], "operator": s[2], "route_id": s[3], "from_place_id": s[4], "to_place_id": s[5],
        "departure_point": s[6], "days_of_week": s[7], "departure_times": s[8], "duration_min": s[9],
        "price_mnt": s[10], "seats": s[11], "vehicle_id": s[12],
        "booking_channel": {"bus": "ticket office or eticket app", "shared_van": "pay the driver, leaves when full", "flight": "airline website"}[s[1]],
        "is_mock": True,
    })

# ---------------------------------------------------------------- more transport: trains, self-drive rental, shared rides
for p in [
    ("place_sukhbaatar_city", "Sükhbaatar (Selenge)", "Сүхбаатар хот", "Selenge", "aimag_center", 50.2314, 106.2078, True, "Railway border town to Russia."),
    ("place_choir", "Choir", "Чойр", "Govisümber", "aimag_center", 46.3597, 108.3622, True, "Rail stop on the way to the Gobi."),
    ("place_sainshand", "Sainshand", "Сайншанд", "Dornogovi", "aimag_center", 44.8925, 110.1397, True, "Dornogovi center, Khamariin Khiid energy center nearby."),
    ("place_zamyn_uud", "Zamyn-Üüd", "Замын-Үүд", "Dornogovi", "soum_center", 43.7167, 111.9000, True, "Border town with China (Erenhot)."),
]:
    places.append({"_id": p[0], "name": p[1], "name_mn": p[2], "aimag": p[3], "kind": p[4],
                   "location": pt(p[5], p[6]), "fuel_available": p[7], "note": p[8]})
    PLACE[p[0]] = places[-1]

# Trains (mock timetable in the style of the Ulaanbaatar Railway). Fares are from the origin, per seat class.
TRAINS = [
    ("sched_train_ub_sukhbaatar", "UB to Sükhbaatar (via Darkhan)", "place_ub", DAILY, "10:30",
     [("place_ub", 0, {}), ("place_darkhan", 330, {"hard_seat": 18000, "platzkart": 26000, "kupe": 38000}),
      ("place_sukhbaatar_city", 540, {"hard_seat": 25000, "platzkart": 36000, "kupe": 52000})]),
    ("sched_train_ub_erdenet", "UB to Erdenet overnight (via Darkhan)", "place_ub", DAILY, "20:40",
     [("place_ub", 0, {}), ("place_darkhan", 330, {"hard_seat": 18000, "platzkart": 26000, "kupe": 38000}),
      ("place_erdenet", 660, {"hard_seat": 26000, "platzkart": 38000, "kupe": 56000})]),
    ("sched_train_ub_zamyn_uud", "UB to Zamyn-Üüd overnight (via Choir, Sainshand)", "place_ub", DAILY, "17:20",
     [("place_ub", 0, {}), ("place_choir", 300, {"hard_seat": 16000, "platzkart": 24000, "kupe": 35000}),
      ("place_sainshand", 600, {"hard_seat": 27000, "platzkart": 39000, "kupe": 58000}),
      ("place_zamyn_uud", 840, {"hard_seat": 36000, "platzkart": 52000, "kupe": 76000})]),
]
TRAIN_SEATS = {"hard_seat": 180, "platzkart": 216, "kupe": 72}
for sid, name, frm, days, dep, stops in TRAINS:
    h, m = map(int, dep.split(":"))
    stop_docs = []
    for pid, offset, fares in stops:
        t = h * 60 + m + offset
        stop_docs.append({"place_id": pid, "arrive_offset_min": offset, "time": f"{t // 60 % 24:02d}:{t % 60:02d}",
                          "day_offset": t // 1440, "fare_from_origin_mnt": fares})
    schedules.append({
        "_id": sid, "mode": "train", "operator": "Ulaanbaatar Railway (mock)", "name": name, "route_id": None,
        "from_place_id": frm, "to_place_id": stops[-1][0], "departure_point": "Ulaanbaatar railway station",
        "days_of_week": days, "departure_times": [dep], "duration_min": stops[-1][1],
        "price_mnt": stops[-1][2]["hard_seat"], "seats": sum(TRAIN_SEATS.values()), "vehicle_id": None,
        "stops": stop_docs, "seat_classes": [{"class": c, "seats": n} for c, n in TRAIN_SEATS.items()],
        "booking_channel": "eticket.ubtz.mn style (mock) or station ticket office", "is_mock": True,
    })

# Self-drive rental cars (no driver). Existing vehicles with a driver get rental.mode = "with_driver".
for v in vehicles:
    if v["rental"]:
        v["rental"]["mode"] = "with_driver"
for i, v in enumerate([
    ("veh_rent_01", "sedan", "Toyota Prius 41", 4, False, "place_ub", 90000, 250, 300, 500000, 15000, ["ac", "hybrid"], "Steppe Rent (mock)"),
    ("veh_rent_02", "suv", "Hyundai Tucson", 5, False, "place_ub", 150000, 300, 400, 800000, 20000, ["ac", "awd"], "Steppe Rent (mock)"),
    ("veh_rent_03", "suv", "Toyota Land Cruiser Prado", 5, True, "place_ub", 280000, 350, 600, 1500000, 30000, ["4x4", "ac", "roof_rack"], "Nomad Wheels (mock)"),
    ("veh_rent_04", "sedan", "Toyota Prius 30", 4, False, "place_darkhan", 80000, 250, 300, 400000, 15000, ["ac", "hybrid"], "Darkhan Car Rent (mock)"),
    ("veh_rent_05", "suv", "Toyota Land Cruiser Prado", 5, True, "place_dalanzadgad", 300000, 300, 600, 1500000, 30000, ["4x4", "ac", "sand_ladders"], "Gobi Rent (mock)"),
    ("veh_rent_06", "minivan", "Mitsubishi Delica", 7, True, "place_khovd", 220000, 300, 500, 1000000, 25000, ["4x4"], "Altai Rent (mock)"),
    ("veh_rent_07", "suv", "Toyota RAV4", 5, False, "place_choibalsan", 160000, 300, 400, 800000, 20000, ["ac", "awd"], "Dornod Rent (mock)"),
], start=len(vehicles)):
    lng, lat = ll(v[5])
    vehicles.append({
        "_id": v[0], "type": v[1], "model": v[2], "seats": v[3], "offroad_capable": v[4],
        "rental": {"mode": "self_drive", "includes_driver": False, "price_per_day_mnt": v[6], "km_included_per_day": v[7],
                   "price_per_extra_km_mnt": v[8], "deposit_mnt": v[9], "insurance_per_day_mnt": v[10], "fuel_included": False,
                   "fuel_policy": "full_to_full", "min_driver_age": 21, "license_required": "B",
                   "international_license_ok": True, "pickup_place_id": v[5], "one_way_drop_fee_mnt": 250000},
        "driver_id": None, "operator": v[12], "base_place_id": v[5],
        "plate": f"{1000 + i * 37 % 9000:04d} УБ{'АБВГДЕЖ'[i % 7]}", "features": v[11],
        "current_location": pt(round(lat + rnd.uniform(-0.01, 0.01), 5), round(lng + rnd.uniform(-0.01, 0.01), 5)),
        "status": "available", "is_mock": True,
    })

# Shared rides: local drivers selling seats, or individual travellers splitting a car.
shared_rides = []
for rid, kind, frm, to, day, dep, seats, left, price, veh, drv, poster, note in [
    ("ride_001", "driver_offer", "place_ub", "place_darkhan", "2026-10-03", "09:00", 7, 3, 25000, "veh_van_03", "driver_10", None, "Leaves from Dragon terminal parking."),
    ("ride_002", "driver_offer", "place_murun", "place_khatgal", "2026-10-03", "11:00", 7, 5, 22000, "veh_van_04", "driver_04", None, "Leaves when full, around 11:00."),
    ("ride_003", "traveler_post", "place_ub", "place_khatgal", "2026-10-02", "07:00", 3, 2, 110000, None, None, {"name": "Tömöröö", "phone": "+976 9911 3301", "note": "Own Prado, splitting fuel"}, "Two free seats, small luggage only."),
    ("ride_004", "driver_offer", "place_ub", "place_dalanzadgad", "2026-10-08", "08:00", 7, 4, 70000, "veh_van_02", "driver_03", None, "UAZ furgon, stops in Mandalgovi."),
    ("ride_005", "traveler_post", "place_dalanzadgad", "place_khongoryn_els", "2026-10-10", "09:30", 4, 2, 60000, None, None, {"name": "Marta", "phone": "+34 600 000 000", "note": "Backpacker with hired jeep"}, "Sharing jeep cost to the dunes."),
    ("ride_006", "driver_offer", "place_khovd", "place_olgii", "2026-10-02", "10:00", 7, 1, 45000, "veh_van_06", "driver_14", None, "Festival day, almost full."),
    ("ride_007", "driver_offer", "place_olgii", "place_tavan_bogd", "2026-10-06", "08:00", 4, 4, 150000, "veh_suv_06", "driver_13", None, "Season is ending; confirm permit first."),
    ("ride_008", "traveler_post", "place_ub", "place_olgii", "2026-10-01", "06:00", 3, 3, 250000, None, None, {"name": "Aibek", "phone": "+976 9911 3302", "note": "Driving home for the festival"}, "2 days on the road via Khovd."),
    ("ride_009", "driver_offer", "place_ub", "place_chinggis_city", "2026-10-09", "09:00", 4, 2, 35000, "veh_suv_07", "driver_15", None, "Continues to Dadal on request."),
    ("ride_010", "driver_offer", "place_choibalsan", "place_ub", "2026-10-12", "07:00", 9, 6, 60000, "veh_van_07", "driver_16", None, "Weekly Choibalsan to UB run."),
    ("ride_011", "traveler_post", "place_ub", "place_bulgan", "2026-10-04", "10:00", 3, 1, 40000, None, None, {"name": "Saraa", "phone": "+976 9911 3303", "note": "Visiting parents"}, "One seat left."),
    ("ride_012", "driver_offer", "place_darkhan", "place_ub", "2026-10-05", "15:00", 3, 3, 25000, "veh_sedan_01", "driver_05", None, "Prius, back to UB."),
]:
    shared_rides.append({
        "_id": rid, "type": kind, "from_place_id": frm, "to_place_id": to, "date": day, "depart_time": dep,
        "seats_total": seats, "seats_left": left, "price_per_seat_mnt": price, "vehicle_id": veh, "driver_id": drv,
        "posted_by": poster, "luggage": "1 bag + 1 small per seat", "notes": note,
        "status": "open" if left else "full", "bookable": left > 0, "is_mock": True,
    })

# Seats left per departure (bus, train, flight, shared van) for the demo window.
transport_availability = []
DOW = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
for s in schedules:
    classes = [c["class"] for c in s.get("seat_classes", [])] or [{"flight": "economy"}.get(s["mode"], "standard")]
    for k in range(DEMO_DAYS):
        d = DEMO_START + timedelta(days=k)
        if DOW[d.weekday()] not in s["days_of_week"]:
            continue
        for t in s["departure_times"]:
            for c in classes:
                total = TRAIN_SEATS[c] if s["mode"] == "train" else s["seats"]
                left = rnd.randint(0, total // 2) if d.weekday() >= 4 else rnd.randint(total // 3, total)
                transport_availability.append({
                    "_id": f"tavail_{s['_id'][6:]}_{d.isoformat()}_{t.replace(':', '')}_{c}", "schedule_id": s["_id"],
                    "mode": s["mode"], "date": d.isoformat(), "departure_time": t, "seat_class": c,
                    "seats_total": total, "seats_left": left, "status": "open" if left else "sold_out",
                })

# Which days each rentable vehicle is free (with driver or self-drive).
vehicle_availability = []
for v in vehicles:
    if not v["rental"]:
        continue
    for k in range(DEMO_DAYS):
        d = DEMO_START + timedelta(days=k)
        vehicle_availability.append({
            "_id": f"vavail_{v['_id'][4:]}_{d.isoformat()}", "vehicle_id": v["_id"], "date": d.isoformat(),
            "status": rnd.choice(["available"] * 5 + ["booked", "maintenance"]), "booking_id": None,
        })

# ---------------------------------------------------------------- regions (4 travel regions: north, west, east, south)
# Ulaanbaatar is the start hub, not a region (region "hub"). Töv, Arkhangai, Övörkhangai count as north.
# Membership is decided by aimag. The boundary polygons are rough, non-overlapping boxes for maps and
# $geoIntersects lookups, not official borders.
REGIONS = [
    ("north", "North", "Хойд бүс", [[97.5, 46.4], [102.0, 46.4], [102.0, 46.0], [107.8, 46.0], [107.8, 46.6], [108.5, 46.6], [108.5, 52.2], [97.5, 52.2], [97.5, 46.4]],
     [("Töv", "Төв"), ("Selenge", "Сэлэнгэ"), ("Darkhan-Uul", "Дархан-Уул"), ("Orkhon", "Орхон"), ("Bulgan", "Булган"),
      ("Khövsgöl", "Хөвсгөл"), ("Arkhangai", "Архангай"), ("Övörkhangai", "Өвөрхангай")],
     ["Khövsgöl Lake", "Amarbayasgalant", "Kharkhorin, Erdene Zuu", "Terkhiin Tsagaan Lake", "Uran Togoo"], [6, 7, 8, 9], 5,
     "Forests, lakes, monasteries. Mostly paved roads; train to Darkhan and Erdenet."),
    ("west", "West", "Баруун бүс", [[87.7, 41.5], [97.5, 41.5], [97.5, 52.2], [87.7, 52.2], [87.7, 41.5]],
     [("Bayan-Ölgii", "Баян-Өлгий"), ("Uvs", "Увс"), ("Khovd", "Ховд"), ("Zavkhan", "Завхан"), ("Govi-Altai", "Говь-Алтай")],
     ["Golden Eagle Festival", "Altai Tavan Bogd", "Uvs Lake", "Khar Us Lake", "Kazakh culture"], [6, 7, 8, 9, 10], 7,
     "Very far from UB (1,400+ km); fly to Ölgii or Khovd and hire a local driver."),
    ("east", "East", "Зүүн бүс", [[108.5, 46.6], [109.0, 46.6], [109.0, 46.0], [112.0, 46.0], [112.0, 44.5], [119.95, 44.5], [119.95, 50.4], [108.5, 50.4], [108.5, 46.6]],
     [("Khentii", "Хэнтий"), ("Dornod", "Дорнод"), ("Sükhbaatar", "Сүхбаатар")],
     ["Dadal (Chinggis Khaan birthplace)", "Eastern steppe gazelles", "Shiliin Bogd", "Dariganga"], [6, 7, 8, 9], 4,
     "Open steppe and history; long paved road to Choibalsan."),
    ("south", "South", "Өмнөд бүс", [[97.5, 41.5], [112.0, 41.5], [112.0, 46.0], [109.0, 46.0], [109.0, 46.6], [107.8, 46.6], [107.8, 46.0], [102.0, 46.0], [102.0, 46.4], [97.5, 46.4], [97.5, 41.5]],
     [("Ömnögovi", "Өмнөговь"), ("Dundgovi", "Дундговь"), ("Dornogovi", "Дорноговь"), ("Govisümber", "Говьсүмбэр"), ("Bayankhongor", "Баянхонгор")],
     ["Khongoryn Els dunes", "Yolyn Am", "Bayanzag Flaming Cliffs", "Tsagaan Suvarga", "Thousand Camel Festival"], [5, 6, 7, 8, 9], 5,
     "Gobi desert; most ger camps close mid-October. Flights to Dalanzadgad, train to Sainshand."),
]
AIMAG_REGION = {a: r[0] for r in REGIONS for a, _ in r[4]}
AIMAG_REGION["Ulaanbaatar"] = "hub"
regions = [{
    "_id": rid, "code": rid, "name": name, "name_mn": name_mn,
    "boundary": {"type": "Polygon", "coordinates": [poly]}, "boundary_is_approximate": True,
    "aimags": [{"name": a, "name_mn": amn} for a, amn in aimags], "highlights": hl, "best_months": months,
    "min_days": min_days, "notes": notes, "is_mock": True,
} for rid, name, name_mn, poly, aimags, hl, months, min_days, notes in REGIONS]


def region_of_place(pid):
    return AIMAG_REGION[PLACE[pid]["aimag"]]


def trip_region(frm, to):
    # UB-start trips take the destination's region
    r = region_of_place(to)
    return r if r != "hub" else region_of_place(frm)


for doc in places + stays + events:
    doc["region"] = AIMAG_REGION[doc["aimag"]]
for r in routes:
    r["area"] = r["region"]  # old sub-area label (north / khuvsgul / gobi / west / east)
    r["region"] = trip_region(r["from_place_id"], r["to_place_id"])
for s in schedules:
    s["region"] = trip_region(s["from_place_id"], s["to_place_id"])
SCHED_REGION = {s["_id"]: s["region"] for s in schedules}
for a in transport_availability:
    a["region"] = SCHED_REGION[a["schedule_id"]]
for r in shared_rides:
    r["region"] = trip_region(r["from_place_id"], r["to_place_id"])
for v in vehicles:
    v["region"] = region_of_place(v["base_place_id"])
VEH_REGION = {v["_id"]: v["region"] for v in vehicles}
for a in vehicle_availability:
    a["region"] = VEH_REGION[a["vehicle_id"]]
for d in drivers:
    d["region"] = region_of_place(d["base_place_id"])
    d["regions_served"] = sorted({AIMAG_REGION[a] for a in d["regions_known"]} - {"hub"})
ROUTE = {r["_id"]: r for r in routes}
for t in trips:
    t["region"] = ROUTE[t["route_id"]]["region"]


def _in_poly(x, y, poly):
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


for p in places:  # sanity check: every place's point falls in its region's polygon
    x, y = p["location"]["coordinates"]
    want = p["region"] if p["region"] != "hub" else "north"
    got = [r["_id"] for r in regions if _in_poly(x, y, r["boundary"]["coordinates"][0])]
    assert got == [want], (p["_id"], want, got)

# ---------------------------------------------------------------- sourced landmarks
# Load after the legacy approximate-region polygon check: those display polygons are not
# administrative boundaries. Curated landmarks use their reviewed aimag, not those polygons.
# Also load after random mock inventory generation, keeping all existing commerce data stable.
LANDMARKS = os.path.join(OUT, "..", "landmarks")
with open(os.path.join(LANDMARKS, "catalog.json"), encoding="utf-8") as f:
    for landmark in json.load(f):
        assert landmark["_id"] not in PLACE, f"Duplicate place: {landmark['_id']}"
        landmark["region"] = AIMAG_REGION[landmark["aimag"]]
        landmark["is_mock"] = False
        places.append(landmark)
        PLACE[landmark["_id"]] = landmark
with open(os.path.join(LANDMARKS, "aliases.json"), encoding="utf-8") as f:
    for pid, aliases in json.load(f).items():
        PLACE[pid]["aliases"] = aliases
# OpenStreetMap lodging and sights for Terelj, Khövsgöl and Uvs. Facts and coordinates are ODbL;
# notes are short originals. Photos, when present, come from Wikimedia Commons via images.json.
_osm_path = os.path.join(LANDMARKS, "osm_places.json")
if os.path.exists(_osm_path):
    with open(_osm_path, encoding="utf-8") as f:
        for landmark in json.load(f):
            assert landmark["_id"] not in PLACE, f"Duplicate place: {landmark['_id']}"
            landmark["region"] = AIMAG_REGION[landmark["aimag"]]
            landmark["is_mock"] = False
            places.append(landmark)
            PLACE[landmark["_id"]] = landmark

# ---------------------------------------------------------------- images
# Freely licensed photos from Wikimedia Commons, each with author, license and source link.
# images.json (from fetch_images.py): real photos geotagged near a place or stay, or of the real event.
# image_pool.json: generic photos per stay type, used to fill up stays with fewer than 3 nearby photos.
# `match` says how a photo relates: near_stay / location / event_topic / type. Stays are fake, so
# no photo shows that exact property (is_illustrative stays true).
with open(os.path.join(OUT, "image_pool.json"), encoding="utf-8") as f:
    IMAGE_POOL = json.load(f)
_images_path = os.path.join(OUT, "images.json")
FOUND = json.load(open(_images_path, encoding="utf-8")) if os.path.exists(_images_path) else {}


def _spread_photos(photos: list[dict]) -> list[dict]:
    """Take turns by photographer, so one stay is not three shots of the same camp."""
    buckets: dict[str, list[dict]] = {}
    order: list[str] = []
    for photo in photos:
        author = photo.get("author") or ""
        if author not in buckets:
            buckets[author] = []
            order.append(author)
        buckets[author].append(photo)
    spread: list[dict] = []
    while any(buckets.values()):
        for author in order:
            if buckets[author]:
                spread.append(buckets[author].pop(0))
    return spread


def _pool_photo(img: dict) -> dict:
    return dict(img, is_illustrative=True, match="type", distance_m=None)


def _least_used(photos: list[dict], used: dict[str, int], skip: set[str]):
    ranked = sorted(
        (img for img in photos if img["url"] not in skip),
        key=lambda img: (used.get(img["url"], 0), photos.index(img)),
    )
    return ranked[0] if ranked else None


_pools = {kind: _spread_photos(photos) for kind, photos in IMAGE_POOL.items()}
_used: dict[str, int] = {}
# Covers first, so two stays do not open on the same photo while unused photos remain.
_near: dict[str, list[dict]] = {}
for s in stays:
    near = [dict(img, is_illustrative=True) for img in FOUND.get(s["_id"], [])][:3]
    _near[s["_id"]] = near
    cover = near[0] if near and _used.get(near[0]["url"], 0) == 0 else None
    if cover is None:
        picked = _least_used(_pools[s["type"]], _used, set())
        if picked and _used.get(picked["url"], 0) == 0:
            cover = _pool_photo(picked)
        elif near:
            cover = near[0]
        elif picked:
            cover = _pool_photo(picked)
    assert cover is not None
    s["images"] = [cover]
    _used[cover["url"]] = _used.get(cover["url"], 0) + 1
for s in stays:
    urls = {img["url"] for img in s["images"]}
    for img in _near[s["_id"]]:
        if len(s["images"]) >= 3:
            break
        if img["url"] not in urls:
            s["images"].append(img)
            urls.add(img["url"])
            _used[img["url"]] = _used.get(img["url"], 0) + 1
    while len(s["images"]) < 3:
        picked = _least_used(_pools[s["type"]], _used, urls)
        if picked is None:
            break
        s["images"].append(_pool_photo(picked))
        urls.add(picked["url"])
        _used[picked["url"]] = _used.get(picked["url"], 0) + 1
    s["cover_image_url"] = s["images"][0]["url"]
for doc in places + events:
    doc["images"] = [
        dict(img, is_illustrative=img["is_illustrative"] if "is_illustrative" in img else doc in events)
        for img in FOUND.get(doc["_id"], [])
    ]
    doc["cover_image_url"] = doc["images"][0]["url"] if doc["images"] else None

# ---------------------------------------------------------------- app users (login demo accounts)
# Passwords are NOT stored here: the backend seeder (back/app/seeder.py) adds a bcrypt hash from
# SEED_DEV_PASSWORD. Cards are Stripe's published TEST numbers only; they cannot charge anything.
# Only a provider token + last4 is stored, never the card number or CVC (same as a real app would).
# The matching Stripe test numbers for the checkout form are listed in README.md.
STRIPE_TEST_PM = {"4242424242424242": "pm_card_visa", "4012888888881881": "pm_card_visa",
                  "4000056655665556": "pm_card_visa_debit"}


def test_card(number, exp_month, exp_year, holder):
    return {"type": "card", "brand": "visa", "last4": number[-4:], "exp_month": exp_month, "exp_year": exp_year,
            "holder_name": holder, "provider": "stripe_test", "provider_payment_method": STRIPE_TEST_PM[number],
            "is_default": True, "is_test_card": True}


USERS = [
    ("user_anand", "anand@nashatech.com", "Anand", "Demo", "Ананд", "+976 9900 0001", "4242424242424242", 12, 2030),
    ("user_tsende", "tsendayush@nashatech.com", "Tsendayush", "Tserensaikhan", "Цэндаюуш", "+976 9900 0002", "4012888888881881", 6, 2031),
    ("user_jamba", "jambaa@nashatech.com", "Jambaa", "Demo", "Жамбаа", "+976 9900 0003", "4000056655665556", 3, 2029),
]
users = [{
    "_id": uid, "email": email, "first_name": name, "last_name": last, "first_name_mn": name_mn, "phone": phone, "is_active": True,
    "lang": "mn", "role": "traveler", "auth": {"provider": "backend", "password_from_env": "SEED_DEV_PASSWORD"},
    "payment_methods": [test_card(card, m, y, name.upper()), {"type": "qpay", "is_default": False}],
    "created_at": "2026-09-29T00:00:00Z", "is_mock": True,
} for uid, email, name, last, name_mn, phone, card, m, y in USERS]

# ---------------------------------------------------------------- commerce demo: quotes -> user approval -> payment -> refund
# The agent offers options (quotes), the user picks one and approves the amount, then the agent pays.
# Payment lifecycle: quoted -> approved_by_user -> paid -> (cancelled -> refunded). Sandbox only.
CARD = {u["_id"]: u["payment_methods"][0] for u in users}


def card_ref(uid):
    c = CARD[uid]
    return {"type": "card", "brand": c["brand"], "last4": c["last4"], "is_test_card": True}


trips += [
    {"_id": "trip_anand_eagle", "user_id": "user_anand", "title": "Golden Eagle Festival in Ölgii", "user": {"name": "Anand", "lang": "mn", "phone": "+976 9900 0001"},
     "party": {"adults": 1, "children": 0}, "start_date": "2026-10-01", "end_date": "2026-10-05", "route_id": "route_khovd_olgii",
     "vehicle_id": "veh_suv_06", "driver_id": "driver_13", "current_version": 1, "status": "booked", "region": "west",
     "budget": {"limit_mnt": 3000000, "spent_mnt": 0, "currency": "MNT"}, "created_at": "2026-09-26T08:00:00Z"},
    {"_id": "trip_tsende_darkhan", "user_id": "user_tsende", "title": "Weekend in Darkhan by train", "user": {"name": "Tsendayush", "lang": "mn", "phone": "+976 9900 0002"},
     "party": {"adults": 2, "children": 1}, "start_date": "2026-10-03", "end_date": "2026-10-05", "route_id": "route_ub_darkhan",
     "vehicle_id": None, "driver_id": None, "current_version": 1, "status": "booked", "region": "north",
     "budget": {"limit_mnt": 800000, "spent_mnt": 0, "currency": "MNT"}, "created_at": "2026-09-28T10:30:00Z"},
    {"_id": "trip_jamba_east", "user_id": "user_jamba", "title": "Self-drive to Dadal", "user": {"name": "Jambaa", "lang": "mn", "phone": "+976 9900 0003"},
     "party": {"adults": 2, "children": 0}, "start_date": "2026-10-09", "end_date": "2026-10-12", "route_id": "route_chinggis_dadal",
     "vehicle_id": "veh_rent_03", "driver_id": None, "current_version": 1, "status": "awaiting_payment", "region": "east",
     "budget": {"limit_mnt": 2500000, "spent_mnt": 0, "currency": "MNT"}, "created_at": "2026-09-29T09:00:00Z"},
]

itinerary_versions += [
    {"_id": "itin_anand_eagle_v1", "trip_id": "trip_anand_eagle", "version": 1, "created_at": "2026-09-26T08:05:00Z", "reason": "initial_plan", "days": [
        {"day": 1, "date": "2026-10-01", "from_place_id": "place_ub", "to_place_id": "place_olgii", "transport": {"kind": "flight", "schedule_id": "sched_flight_ub_olgii"}, "stay_id": "stay_olgii_guesthouse_kazakh"},
        {"day": 2, "date": "2026-10-02", "from_place_id": "place_olgii", "to_place_id": "place_olgii", "stay_id": "stay_olgii_eagle_hunter_family", "note": "Visit eagle hunter family with driver Serik"},
        {"day": 3, "date": "2026-10-03", "from_place_id": "place_olgii", "to_place_id": "place_olgii", "stay_id": "stay_olgii_guesthouse_kazakh", "event_ids": ["event_golden_eagle_festival_2026"]},
        {"day": 4, "date": "2026-10-04", "from_place_id": "place_olgii", "to_place_id": "place_olgii", "stay_id": "stay_olgii_guesthouse_kazakh", "event_ids": ["event_golden_eagle_festival_2026"]},
        {"day": 5, "date": "2026-10-05", "from_place_id": "place_olgii", "to_place_id": "place_ub", "transport": {"kind": "flight", "schedule_id": "sched_flight_ub_olgii", "note": "return leg"}}]},
    {"_id": "itin_tsende_darkhan_v1", "trip_id": "trip_tsende_darkhan", "version": 1, "created_at": "2026-09-28T10:35:00Z", "reason": "initial_plan", "days": [
        {"day": 1, "date": "2026-10-03", "from_place_id": "place_ub", "to_place_id": "place_darkhan", "transport": {"kind": "train", "schedule_id": "sched_train_ub_sukhbaatar", "seat_class": "kupe"}, "stay_id": "stay_darkhan_house_khongor", "event_ids": ["event_darkhan_autumn_fair"]},
        {"day": 2, "date": "2026-10-04", "from_place_id": "place_darkhan", "to_place_id": "place_darkhan", "stay_id": "stay_darkhan_house_khongor", "event_ids": ["event_darkhan_autumn_fair"]},
        {"day": 3, "date": "2026-10-05", "from_place_id": "place_darkhan", "to_place_id": "place_ub", "transport": {"kind": "shared_ride", "ride_id": "ride_012"}}]},
    {"_id": "itin_jamba_east_v1", "trip_id": "trip_jamba_east", "version": 1, "created_at": "2026-09-29T09:05:00Z", "reason": "initial_plan", "days": [
        {"day": 1, "date": "2026-10-09", "from_place_id": "place_ub", "to_place_id": "place_chinggis_city", "route_id": "route_ub_chinggis", "transport": {"kind": "self_drive", "vehicle_id": "veh_rent_03"}, "stay_id": "stay_chinggis_hotel_kherlen"},
        {"day": 2, "date": "2026-10-10", "from_place_id": "place_chinggis_city", "to_place_id": "place_dadal", "route_id": "route_chinggis_dadal", "stay_id": "stay_dadal_log_house"},
        {"day": 3, "date": "2026-10-11", "from_place_id": "place_dadal", "to_place_id": "place_dadal", "stay_id": "stay_dadal_log_house"},
        {"day": 4, "date": "2026-10-12", "from_place_id": "place_dadal", "to_place_id": "place_ub", "route_id": "route_ub_chinggis"}]},
]

# Options the agent showed; the user picks one.
quotes = []
for qid, tid, uid, label, label_mn, items, status, created in [
    ("quote_anand_a", "trip_anand_eagle", "user_anand", "Fly + local driver", "Онгоц + орон нутгийн жолооч",
     [("flight", "sched_flight_ub_olgii", 2, 520000, "UB ⇄ Ölgii flights"), ("vehicle", "veh_suv_06", 4, 400000, "Land Cruiser with driver Serik, 4 days"),
      ("stay", "stay_olgii_guesthouse_kazakh", 3, 90000, "Guesthouse double room, 3 nights"), ("stay", "stay_olgii_eagle_hunter_family", 1, 55000, "Eagle hunter family ger, 1 night"),
      ("event", "event_golden_eagle_festival_2026", 2, 60000, "Festival tickets, 2 days")], "accepted", "2026-09-26T08:05:00Z"),
    ("quote_anand_b", "trip_anand_eagle", "user_anand", "Shared ride overland", "Хамтын унаагаар газраар",
     [("shared_ride", "ride_008", 1, 250000, "Seat UB → Ölgii with Aibek (2 days)"), ("stay", "stay_olgii_guesthouse_kazakh", 3, 90000, "Guesthouse, 3 nights"),
      ("event", "event_golden_eagle_festival_2026", 2, 60000, "Festival tickets"), ("flight", "sched_flight_ub_olgii", 1, 520000, "Fly back")], "declined", "2026-09-26T08:05:00Z"),
    ("quote_tsende_a", "trip_tsende_darkhan", "user_tsende", "Train + family house", "Галт тэрэг + гэр бүлийн байшин",
     [("train", "sched_train_ub_sukhbaatar", 3, 38000, "Kupe seats UB → Darkhan x3"), ("stay", "stay_darkhan_house_khongor", 2, 250000, "Whole house, 2 nights"),
      ("shared_ride", "ride_012", 3, 25000, "Prius back to UB, 3 seats")], "accepted", "2026-09-28T10:35:00Z"),
    ("quote_tsende_b", "trip_tsende_darkhan", "user_tsende", "Bus + hotel", "Автобус + зочид буудал",
     [("bus", "sched_bus_ub_darkhan", 6, 17000, "Bus both ways x3"), ("stay", "stay_darkhan_hotel_selenge", 2, 160000, "Double room, 2 nights")], "declined", "2026-09-28T10:35:00Z"),
    ("quote_jamba_a", "trip_jamba_east", "user_jamba", "Self-drive Prado", "Өөрөө жолоодох Prado",
     [("vehicle", "veh_rent_03", 4, 280000, "Prado self-drive, 4 days"), ("insurance", "veh_rent_03", 4, 30000, "Insurance, 4 days"),
      ("stay", "stay_chinggis_hotel_kherlen", 1, 120000, "Hotel, 1 night"), ("stay", "stay_dadal_log_house", 2, 300000, "Log house, 2 nights")], "accepted", "2026-09-29T09:05:00Z"),
    ("quote_jamba_b", "trip_jamba_east", "user_jamba", "Driver + camp", "Жолоочтой + бааз",
     [("shared_ride", "ride_009", 2, 35000, "2 seats UB → Chinggis"), ("vehicle", "veh_suv_07", 3, 420000, "Land Cruiser with driver, 3 days"),
      ("stay", "stay_dadal_camp_gurvan_nuur", 2, 180000, "Ger camp, 2 people x 2 nights")], "quoted", "2026-09-29T09:05:00Z"),
]:
    lines = [{"kind": k, "ref_id": ref, "qty": q, "unit_price_mnt": p, "total_mnt": q * p, "label": lab} for k, ref, q, p, lab in items]
    quotes.append({"_id": qid, "trip_id": tid, "user_id": uid, "label": label, "label_mn": label_mn, "lines": lines,
                   "total_mnt": sum(x["total_mnt"] for x in lines), "currency": "MNT", "status": status,
                   "valid_until": "2026-10-01T00:00:00Z", "created_at": created, "is_mock": True})
QUOTE = {q["_id"]: q for q in quotes}

bookings += [
    {"_id": "booking_011", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "transport", "schedule_id": "sched_flight_ub_olgii", "date": "2026-10-01", "seat_class": "economy", "seats": 1, "total_price_mnt": 520000, "status": "confirmed", "payment_id": "pay_anand_001", "is_mock": True},
    {"_id": "booking_012", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "transport", "schedule_id": "sched_flight_ub_olgii", "date": "2026-10-05", "seat_class": "economy", "seats": 1, "total_price_mnt": 520000, "status": "confirmed", "payment_id": "pay_anand_001", "note": "Return leg on the same (mock) schedule", "is_mock": True},
    {"_id": "booking_013", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "vehicle", "vehicle_id": "veh_suv_06", "driver_id": "driver_13", "start_date": "2026-10-01", "end_date": "2026-10-04", "days": 4, "total_price_mnt": 1600000, "status": "confirmed", "payment_id": "pay_anand_001", "is_mock": True},
    {"_id": "booking_014", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "stay", "stay_id": "stay_olgii_guesthouse_kazakh", "unit_type": "double_room", "check_in": "2026-10-01", "check_out": "2026-10-02", "nights": 1, "guests": 1, "total_price_mnt": 90000, "cancellation_policy_id": "policy_flexible", "status": "confirmed", "payment_id": "pay_anand_001", "is_mock": True},
    {"_id": "booking_015", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "stay", "stay_id": "stay_olgii_eagle_hunter_family", "unit_type": "ger", "check_in": "2026-10-02", "check_out": "2026-10-03", "nights": 1, "guests": 1, "total_price_mnt": 55000, "cancellation_policy_id": "policy_flexible", "status": "confirmed", "payment_id": "pay_anand_001", "is_mock": True},
    {"_id": "booking_016", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "stay", "stay_id": "stay_olgii_guesthouse_kazakh", "unit_type": "double_room", "check_in": "2026-10-03", "check_out": "2026-10-05", "nights": 2, "guests": 1, "total_price_mnt": 180000, "cancellation_policy_id": "policy_flexible", "status": "confirmed", "payment_id": "pay_anand_001", "is_mock": True},
    {"_id": "booking_017", "trip_id": "trip_anand_eagle", "user_id": "user_anand", "kind": "event_ticket", "event_id": "event_golden_eagle_festival_2026", "tickets": 2, "total_price_mnt": 120000, "status": "confirmed", "payment_id": "pay_anand_001", "is_mock": True},
    {"_id": "booking_018", "trip_id": "trip_tsende_darkhan", "user_id": "user_tsende", "kind": "transport", "schedule_id": "sched_train_ub_sukhbaatar", "date": "2026-10-03", "from_place_id": "place_ub", "to_place_id": "place_darkhan", "seat_class": "kupe", "seats": 3, "total_price_mnt": 114000, "status": "confirmed", "payment_id": "pay_tsende_001", "is_mock": True},
    {"_id": "booking_019", "trip_id": "trip_tsende_darkhan", "user_id": "user_tsende", "kind": "stay", "stay_id": "stay_darkhan_house_khongor", "unit_type": "whole_house", "check_in": "2026-10-03", "check_out": "2026-10-05", "nights": 2, "guests": 3, "total_price_mnt": 500000, "deposit_paid_mnt": 150000, "balance_due_on_arrival_mnt": 350000, "cancellation_policy_id": "policy_moderate", "status": "confirmed", "payment_id": "pay_tsende_002", "is_mock": True},
    {"_id": "booking_020", "trip_id": "trip_tsende_darkhan", "user_id": "user_tsende", "kind": "shared_ride", "ride_id": "ride_012", "seats": 3, "total_price_mnt": 75000, "status": "cancelled", "payment_id": "pay_tsende_003", "note": "Driver cancelled (car broke down); agent rebooked the bus", "is_mock": True},
    {"_id": "booking_021", "trip_id": "trip_tsende_darkhan", "user_id": "user_tsende", "kind": "transport", "schedule_id": "sched_bus_ub_darkhan", "date": "2026-10-05", "from_place_id": "place_darkhan", "to_place_id": "place_ub", "seat_class": "standard", "seats": 3, "total_price_mnt": 51000, "status": "confirmed", "payment_id": "pay_tsende_004", "note": "Replacement for the cancelled shared ride (bus runs both ways)", "is_mock": True},
    {"_id": "booking_022", "trip_id": "trip_jamba_east", "user_id": "user_jamba", "kind": "vehicle_rental", "vehicle_id": "veh_rent_03", "mode": "self_drive", "start_date": "2026-10-09", "end_date": "2026-10-12", "days": 4, "total_price_mnt": 1240000, "deposit_hold_mnt": 1500000, "status": "pending_payment", "payment_id": "pay_jamba_001", "is_mock": True},
    {"_id": "booking_023", "trip_id": "trip_jamba_east", "user_id": "user_jamba", "kind": "stay", "stay_id": "stay_chinggis_hotel_kherlen", "unit_type": "double_room", "check_in": "2026-10-09", "check_out": "2026-10-10", "nights": 1, "guests": 2, "total_price_mnt": 120000, "cancellation_policy_id": "policy_flexible", "status": "pending_payment", "payment_id": "pay_jamba_001", "is_mock": True},
    {"_id": "booking_024", "trip_id": "trip_jamba_east", "user_id": "user_jamba", "kind": "stay", "stay_id": "stay_dadal_log_house", "unit_type": "whole_house", "check_in": "2026-10-10", "check_out": "2026-10-12", "nights": 2, "guests": 2, "total_price_mnt": 600000, "cancellation_policy_id": "policy_deposit_only", "status": "pending_payment", "payment_id": "pay_jamba_001", "is_mock": True},
]
for v in vehicle_availability:  # block the rental/driver days booked above
    for b in bookings:
        if b.get("vehicle_id") == v["vehicle_id"] and b.get("start_date", "9") <= v["date"] <= b.get("end_date", ""):
            v["status"], v["booking_id"] = "booked", b["_id"]
for r in shared_rides:
    if r["_id"] == "ride_012":
        r["seats_left"], r["status"], r["bookable"] = 0, "cancelled", False


def history(*steps):
    return [{"status": s, "at": at, "actor": actor} for s, at, actor in steps]


payments = []
for pid, uid, tid, qid, amount, method, provider, status, steps, approval in [
    ("pay_anand_001", "user_anand", "trip_anand_eagle", "quote_anand_a", 3085000, card_ref("user_anand"), "stripe_test", "paid",
     [("quoted", "2026-09-26T08:05:00Z", "agent"), ("approved_by_user", "2026-09-26T08:11:00Z", "user"), ("paid", "2026-09-26T08:11:05Z", "agent")], 3100000),
    ("pay_tsende_001", "user_tsende", "trip_tsende_darkhan", "quote_tsende_a", 114000, card_ref("user_tsende"), "stripe_test", "paid",
     [("quoted", "2026-09-28T10:35:00Z", "agent"), ("approved_by_user", "2026-09-28T10:40:00Z", "user"), ("paid", "2026-09-28T10:40:04Z", "agent")], 700000),
    ("pay_tsende_002", "user_tsende", "trip_tsende_darkhan", "quote_tsende_a", 150000, {"type": "qpay", "invoice_id": "qpay_sbx_000102"}, "qpay_sandbox", "paid",
     [("quoted", "2026-09-28T10:35:00Z", "agent"), ("approved_by_user", "2026-09-28T10:40:00Z", "user"), ("paid", "2026-09-28T10:42:30Z", "user")], 700000),
    ("pay_tsende_003", "user_tsende", "trip_tsende_darkhan", "quote_tsende_a", 75000, card_ref("user_tsende"), "stripe_test", "refunded",
     [("quoted", "2026-09-28T10:35:00Z", "agent"), ("approved_by_user", "2026-09-28T10:40:00Z", "user"), ("paid", "2026-09-28T10:40:06Z", "agent"),
      ("cancelled", "2026-10-04T18:20:00Z", "owner"), ("refunded", "2026-10-04T18:21:00Z", "agent")], 700000),
    ("pay_tsende_004", "user_tsende", "trip_tsende_darkhan", None, 51000, card_ref("user_tsende"), "stripe_test", "paid",
     [("quoted", "2026-10-04T18:22:00Z", "agent"), ("approved_by_user", "2026-10-04T18:25:00Z", "user"), ("paid", "2026-10-04T18:25:03Z", "agent")], 100000),
    ("pay_jamba_001", "user_jamba", "trip_jamba_east", "quote_jamba_a", 1960000, card_ref("user_jamba"), "stripe_test", "approved_by_user",
     [("quoted", "2026-09-29T09:05:00Z", "agent"), ("approved_by_user", "2026-09-29T09:12:00Z", "user")], 2000000),
    ("pay_jamba_002", "user_jamba", "trip_jamba_east", "quote_jamba_b", 1690000, card_ref("user_jamba"), "stripe_test", "quoted",
     [("quoted", "2026-09-29T09:05:00Z", "agent")], None),
]:
    payments.append({
        "_id": pid, "user_id": uid, "trip_id": tid, "quote_id": qid,
        "booking_ids": [b["_id"] for b in bookings if b.get("payment_id") == pid],
        "amount_mnt": amount, "currency": "MNT", "method": method, "provider": provider,
        "provider_ref": f"{'pi' if provider == 'stripe_test' else 'qp'}_test_{pid[4:]}", "status": status,
        "status_history": history(*steps),
        "consent": {"approved_by_user": approval is not None, "max_amount_mnt": approval,
                    "approved_at": next((at for s, at, _ in steps if s == "approved_by_user"), None)},
        "idempotency_key": f"idem_{pid}", "is_sandbox": True, "is_mock": True,
    })
for t in trips:
    t_paid = sum(p["amount_mnt"] for p in payments if p["trip_id"] == t["_id"] and p["status"] == "paid")
    if "budget" in t:
        t["budget"]["spent_mnt"] = t_paid

refunds = [
    {"_id": "refund_001", "payment_id": "pay_tsende_003", "user_id": "user_tsende", "trip_id": "trip_tsende_darkhan", "booking_id": "booking_020",
     "amount_mnt": 75000, "reason": "provider_cancelled", "reason_mn": "Жолооч цуцалсан (машин эвдэрсэн)", "policy_applied": "full_refund_provider_cancel",
     "status": "succeeded", "provider_ref": "re_test_tsende_003", "requested_at": "2026-10-04T18:20:30Z", "completed_at": "2026-10-04T18:21:00Z", "is_mock": True},
]

# ---------------------------------------------------------------- fuel (so budgets include fuel)
FUEL = {  # model -> (fuel type, litres per 100 km, mixed roads)
    "Hyundai County": ("diesel", 18), "Hyundai Starex": ("diesel", 10), "Hyundai Tucson": ("ai92", 8.5),
    "Hyundai Universe": ("diesel", 28), "Mitsubishi Delica": ("diesel", 11), "Nissan Patrol": ("ai92", 15),
    "Toyota Hiace": ("diesel", 11), "Toyota Hiace 4WD": ("diesel", 12), "Toyota Land Cruiser 105": ("diesel", 13),
    "Toyota Land Cruiser 200": ("diesel", 12), "Toyota Land Cruiser 70": ("diesel", 13),
    "Toyota Land Cruiser 76": ("diesel", 13), "Toyota Land Cruiser Prado": ("diesel", 10),
    "Toyota Prius 30": ("ai92", 4.5), "Toyota Prius 41": ("ai92", 4.5), "Toyota RAV4": ("ai92", 7.5),
    "UAZ-452 'Furgon'": ("ai92", 16), "Yutong ZK6122": ("diesel", 28),
}
for v in vehicles:
    v["fuel_type"], v["fuel_l_per_100km"] = FUEL[v["model"]]
app_config = [
    {"_id": "fuel_prices", "currency": "MNT", "price_per_liter_mnt": {"ai92": 2350, "ai95": 2950, "diesel": 2700},
     "remote_area_markup_pct": 10, "updated_at": "2026-09-28", "is_mock": True},
]

# ---------------------------------------------------------------- agent collections: audit log, conversations, state
audit_log = []
for p in payments:
    for i, h in enumerate(p["status_history"]):
        audit_log.append({
            "_id": f"audit_{p['_id'][4:]}_{i + 1}", "ts": h["at"], "actor": h["actor"], "user_id": p["user_id"],
            "trip_id": p["trip_id"], "action": f"payment.{h['status']}", "entity": "payments", "entity_id": p["_id"],
            "amount_mnt": p["amount_mnt"], "details": {"provider": p["provider"], "quote_id": p["quote_id"]},
            "is_mock": True,
        })
audit_log.sort(key=lambda a: a["ts"])

conversations = [
    {"_id": "conv_jamba_east", "user_id": "user_jamba", "trip_id": "trip_jamba_east", "lang": "mn",
     "started_at": "2026-09-29T08:58:00Z", "updated_at": "2026-09-29T09:12:00Z", "messages": [
        {"role": "user", "ts": "2026-09-29T08:58:00Z", "text": "10/9-нөөс 4 хоног зүүн тийш, Дадал руу хоёулаа явмаар байна. Өөрсдөө машин барина. Төсөв 2.5 сая."},
        {"role": "agent", "ts": "2026-09-29T09:05:00Z", "text": "Хоёр хувилбар гаргалаа: (1) Prado түрээслээд өөрсдөө жолоодох, Чингис хотод 1, Дадалд 2 хоно, 1,960,000₮. (2) Хамтын унаагаар Чингис хот, тэндээс жолоочтой Land Cruiser, баазад хонох, 1,690,000₮. Алийг нь сонгох вэ?",
         "tool_calls": [{"name": "search_vehicles", "args": {"region": "east", "rental_mode": "self_drive", "date": "2026-10-09"}},
                        {"name": "quote_budget", "args": {"trip_id": "trip_jamba_east"}}]},
        {"role": "user", "ts": "2026-09-29T09:11:00Z", "text": "Эхнийхийг нь авъя."},
        {"role": "agent", "ts": "2026-09-29T09:12:00Z", "text": "1,960,000₮-ийг 5556 төгсгөлтэй Visa картаас төлөхийг зөвшөөрч байна уу? Prado-гийн 1,500,000₮ барьцааг түр түгжинэ.",
         "tool_calls": [{"name": "request_payment_approval", "args": {"payment_id": "pay_jamba_001"}}]},
     ], "is_mock": True},
]

agent_state = [
    {"_id": "state_trip_jamba_east", "trip_id": "trip_jamba_east", "user_id": "user_jamba", "step": "awaiting_payment",
     "slots": {"region": "east", "start_date": "2026-10-09", "days": 4, "party": {"adults": 2, "children": 0},
               "budget_mnt": 2500000, "transport": "self_drive", "stay_preference": "mixed"},
     "missing_slots": [], "pending_approval": {"payment_id": "pay_jamba_001", "amount_mnt": 1960000},
     "updated_at": "2026-09-29T09:12:00Z", "is_mock": True},
]

user_memory = [
    {"_id": "mem_jamba_1", "user_id": "user_jamba", "kind": "preference", "text": "Өөрөө машин барих дуртай, жолооч хөлслөхгүй.",
     "source_conversation_id": "conv_jamba_east", "created_at": "2026-09-29T09:11:00Z", "is_mock": True},
    {"_id": "mem_tsende_1", "user_id": "user_tsende", "kind": "preference", "text": "Хүүхэдтэй, галт тэргээр аялах дуртай.",
     "source_conversation_id": None, "created_at": "2026-09-28T10:40:00Z", "is_mock": True},
]

# ---------------------------------------------------------------- bilingual text {mn, en}
# Every human-readable text field becomes {"mn": ..., "en": ...}. Codes (type, status, amenities,
# hazards, ...) stay as codes; the frontend translates those with its i18n files.
# Mongolian comes from the doc's own *_mn field, else from translations.mn.json.
with open(os.path.join(OUT, "translations.mn.json"), encoding="utf-8") as f:
    MN = json.load(f)
_missing = set()


def loc(en, mn=None):
    if not en:
        return None
    mn = mn or MN.get(en)
    if not mn:
        _missing.add(en)
    return {"mn": mn or en, "en": en}


def loc_fields(docs, *fields):
    for d in docs:
        for fld in fields:
            if fld in d and not isinstance(d[fld], dict):
                d[fld] = loc(d[fld], d.pop(f"{fld}_mn", None))


loc_fields(places, "name", "note")
loc_fields(regions, "name", "notes")
for r in regions:
    r["highlights"] = [loc(h) for h in r["highlights"]]
loc_fields(routes, "name", "summary")
for r in routes:
    loc_fields(r["segments"], "notes")
loc_fields(events, "name", "description")
loc_fields(stays, "name")
loc_fields(policies, "name", "notes")
loc_fields(drivers, "name")
loc_fields(schedules, "name", "departure_point", "booking_channel")
loc_fields(shared_rides, "notes", "luggage")
loc_fields([r["posted_by"] for r in shared_rides if r["posted_by"]], "note")
loc_fields(trips, "title")
loc_fields(itinerary_versions, "agent_summary")
for v in itinerary_versions:
    loc_fields(v["days"], "note")
    loc_fields([d["transport"] for d in v["days"] if d.get("transport")], "note")
loc_fields(quotes, "label")
for q in quotes:
    loc_fields(q["lines"], "label")
loc_fields(bookings, "note")
for r in refunds:
    r["reason_text"] = loc("Driver cancelled (car broke down)", r.pop("reason_mn"))
for u in users:
    u["display_name"] = loc(u["first_name"], u.pop("first_name_mn"))
assert not _missing, f"Add Mongolian for these to translations.mn.json: {sorted(_missing)}"

# ---------------------------------------------------------------- write
COLLECTIONS = {
    "users": users, "regions": regions, "app_config": app_config, "audit_log": audit_log,
    "conversations": conversations, "agent_state": agent_state, "user_memory": user_memory, "quotes": quotes, "payments": payments, "refunds": refunds,
    "shared_rides": shared_rides, "transport_availability": transport_availability, "vehicle_availability": vehicle_availability,
    "places": places, "routes": routes, "events": events, "stays": stays,
    "cancellation_policies": policies, "stay_availability": availability,
    "drivers": drivers, "vehicles": vehicles, "transport_schedules": schedules,
    "trips": trips, "itinerary_versions": itinerary_versions, "bookings": bookings,
}
for name, docs in COLLECTIONS.items():
    with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print(f"{name:22s} {len(docs):4d} docs")
