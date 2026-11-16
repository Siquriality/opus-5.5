import math

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
