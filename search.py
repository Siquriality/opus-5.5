import math
import pandas as pd

EARTH_RADIUS_M = 6371000

MIN_RADIUS_M = 100
MAX_RADIUS_M = 1500
DEFAULT_RADIUS_M = 400

ALLOWED_CATEGORIES = ["bridge", "tram_stop", "church", "park", "monument"]

def haversine_m(lat1, lon1, lat2, lon2):
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    central_angle = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * central_angle


def _remove_duplicates(categories):
    unique = []
    for category in categories:
        if category not in unique:
            unique.append(category)
    return unique

def _check_input(data, categories, radius_m, limit):
    if isinstance(categories, str):
        raise ValueError("Категорії треба передати списком, наприклад ['bridge', 'church'].")

    unique_categories = _remove_duplicates(categories)

    if len(unique_categories) < 2:
        raise ValueError("Оберіть щонайменше дві різні категорії орієнтирів.")

    for category in unique_categories:
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(
                f"Невідома категорія '{category}'. "
                f"Дозволені: {', '.join(ALLOWED_CATEGORIES)}."
            )

    if not isinstance(radius_m, (int, float)):
        raise ValueError("Радіус має бути числом (у метрах).")
    if radius_m < MIN_RADIUS_M or radius_m > MAX_RADIUS_M:
        raise ValueError(
            f"Радіус має бути від {MIN_RADIUS_M} до {MAX_RADIUS_M} метрів, "
            f"а отримано {radius_m}."
        )

    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit має бути цілим числом не менше 1.")

    if len(data) > 0:
        categories_in_data = set(data["category"])
        for category in unique_categories:
            if category not in categories_in_data:
                raise ValueError(
                    f"Категорії '{category}' немає в даних. "
                    "Оберіть іншу або оновіть файл places.csv."
                )

    return unique_categories

def _group_objects_by_category(data, categories):
    groups = {}
    for category in categories:
        rows = data[data["category"] == category]
        objects = []
        for row in rows.itertuples(index=False):
            objects.append({
                "osm_type": str(row.osm_type),
                "osm_id": str(row.osm_id),
                "name": str(row.name),
                "lat": float(row.lat),
                "lon": float(row.lon),
                "url": str(row.url),
            })
        groups[category] = objects
    return groups

def _choose_anchor_category(categories, groups):
    return min(categories, key=lambda category: len(groups[category]))

def _find_nearest(lat, lon, objects):
    nearest_object = None
    nearest_distance = None

    for obj in objects:
        distance = haversine_m(lat, lon, obj["lat"], obj["lon"])
        is_closer = nearest_distance is None or distance < nearest_distance
        is_same_but_smaller_key = (
            nearest_distance is not None
            and distance == nearest_distance
            and (obj["osm_type"], obj["osm_id"]) < (nearest_object["osm_type"], nearest_object["osm_id"])
        )
        if is_closer or is_same_but_smaller_key:
            nearest_object = obj
            nearest_distance = distance

    return nearest_object, nearest_distance