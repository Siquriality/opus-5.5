import json
import urllib.parse
import urllib.request
import pandas as pd

BBOX = (50.38, 30.58, 50.48, 30.68)

OVERPASS_QUERY = f"""[out:json][timeout:60];
(
  way["bridge"="yes"]{BBOX};
  node["railway"="tram_stop"]{BBOX};
  nwr["amenity"="place_of_worship"]["religion"="christian"]{BBOX};
  nwr["leisure"="park"]{BBOX};
  nwr["historic"="monument"]{BBOX};
  nwr["historic"="memorial"]{BBOX};
  way(23705293);
  way(149714824);
  way(1282234657);
);
out center;"""

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

raw_data = None
used_mirror = None

for url in MIRRORS:
    try:
        print(f"Пробую завантажити з {url} ...")
        data = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"User-Agent": "KyivLeftBankHackathon/1.0"},
        )
        with urllib.request.urlopen(req, timeout=70) as resp:
            text = resp.read().decode("utf-8")
            parsed = json.loads(text)
            if parsed.get("elements"):
                raw_data = parsed
                used_mirror = url
                print(f"Успішно! Отримано елементів: {len(parsed['elements'])}")
                break
    except Exception as e:
        print(f"Не вдалося з {url}: {e}")

if raw_data is None:
    raise RuntimeError("Не вдалося завантажити дані з жодного дзеркала Overpass API.")

with open("data/raw_osm.json", "w", encoding="utf-8") as f:
    json.dump(raw_data, f, ensure_ascii=False, indent=2)

elements = raw_data.get("elements", [])
read_count = len(elements)
skipped_count = 0
rows = []

for el in elements:
    osm_type = el.get("type")
    osm_id = str(el.get("id", ""))
    tags = el.get("tags", {})

    category = None
    if tags.get("railway") == "tram_stop":
        category = "tram_stop"
    elif tags.get("bridge") == "yes":
        category = "bridge"
    elif tags.get("amenity") == "place_of_worship" and tags.get("religion") == "christian":
        category = "church"
    elif tags.get("leisure") == "park":
        category = "park"
    elif tags.get("historic") in ("monument", "memorial"):
        category = "monument"

    if not category or osm_type not in ("node", "way", "relation"):
        skipped_count += 1
        continue

    if osm_type == "node":
        latitude = el.get("lat")
        longitude = el.get("lon")
    else:
        center = el.get("center") or {}
        latitude = center.get("lat")
        longitude = center.get("lon")

    if latitude is None or longitude is None:
        skipped_count += 1
        continue
    if not (50.36 <= latitude <= 50.56 and 30.56 <= longitude <= 30.83):
        skipped_count += 1
        continue

    raw_name = tags.get("name:uk") or tags.get("name") or tags.get("name:ru")
    name = raw_name.strip() if raw_name else f"{category}_{osm_id}"
    url = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

    rows.append({
        "osm_type": osm_type,
        "osm_id": osm_id,
        "name": name,
        "category": category,
        "lat": float(latitude),
        "lon": float(longitude),
        "url": url,
    })

df = pd.DataFrame(rows, columns=["osm_type", "osm_id", "name", "category", "lat", "lon", "url"])

before_dedup = len(df)
df = df.drop_duplicates(subset=["osm_type", "osm_id", "category"]).reset_index(drop=True)
duplicates_removed = before_dedup - len(df)

df.to_csv("data/places.csv", index=False, encoding="utf-8")

category_counts = df["category"].value_counts().to_dict()
source_meta = {
    "source": "OpenStreetMap (Overpass API)",
    "endpoint": used_mirror,
    "attribution": "© OpenStreetMap contributors",
    "license_url": "https://www.openstreetmap.org/copyright",
    "date": "2026-11-16",
    "area": "Kyiv (Left Bank)",
    "bbox": list(BBOX),
    "overpass_query": OVERPASS_QUERY,
    "filters": {
        "bridge": "way[bridge=yes]",
        "tram_stop": "node[railway=tram_stop]",
        "church": "nwr[amenity=place_of_worship][religion=christian]",
        "park": "nwr[leisure=park]",
        "monument": "nwr[historic=monument|memorial]"
    },
    "counts_by_category": category_counts,
    "total_records": len(df)
}

with open("data/source.json", "w", encoding="utf-8") as f:
    json.dump(source_meta, f, ensure_ascii=False, indent=2)

print("Прочитано елементів:", read_count)
print("Пропущено:", skipped_count)
print("Видалено дублікатів:", duplicates_removed)
print("Збережено в data/places.csv:", len(df))
print("Розподіл за категоріями:", category_counts)