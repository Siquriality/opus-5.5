import pandas as pd
from search import find_places, haversine_m


def build_mock_dataset() -> pd.DataFrame:
    rows = [
        {
            "osm_type": "way",
            "osm_id": "101",
            "name": "Тестовий міст А",
            "category": "bridge",
            "lat": 50.4500,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/101",
        },
        {
            "osm_type": "way",
            "osm_id": "102",
            "name": "Тестовий міст Б",
            "category": "bridge",
            "lat": 50.4600,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/102",
        },
        {
            "osm_type": "way",
            "osm_id": "103",
            "name": "Самотній міст В",
            "category": "bridge",
            "lat": 50.4900,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/103",
        },
        {
            "osm_type": "way",
            "osm_id": "104",
            "name": "Тестовий міст Г",
            "category": "bridge",
            "lat": 50.4700,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/104",
        },
        {
            "osm_type": "node",
            "osm_id": "201",
            "name": "Зупинка біля А",
            "category": "tram_stop",
            "lat": 50.4505,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/node/201",
        },
        {
            "osm_type": "node",
            "osm_id": "202",
            "name": "Зупинка біля Б",
            "category": "tram_stop",
            "lat": 50.4620,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/node/202",
        },
        {
            "osm_type": "node",
            "osm_id": "204",
            "name": "Зупинка біля Г",
            "category": "tram_stop",
            "lat": 50.4710,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/node/204",
        },
        {
            "osm_type": "way",
            "osm_id": "301",
            "name": "Церква біля А",
            "category": "church",
            "lat": 50.4510,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/301",
        },
        {
            "osm_type": "way",
            "osm_id": "302",
            "name": "Церква далеко від Б",
            "category": "church",
            "lat": 50.4680,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/302",
        },
        {
            "osm_type": "way",
            "osm_id": "304",
            "name": "Церква біля Г",
            "category": "church",
            "lat": 50.4715,
            "lon": 30.5200,
            "url": "https://www.openstreetmap.org/way/304",
        },
    ]
    return pd.DataFrame(rows)


def run_all_checks() -> None:
    df = build_mock_dataset()

    # Перевірка нуля для однакових точок та симетрії функції відстані
    assert haversine_m(50.45, 30.52, 50.45, 30.52) == 0.0, "Очікувалась нульова відстань"
    dist_ab = haversine_m(50.45, 30.52, 50.46, 30.53)
    dist_ba = haversine_m(50.46, 30.53, 50.45, 30.52)
    assert abs(dist_ab - dist_ba) < 1e-6, "Функція відстані має бути симетричною"

    # Сортування за сумою відстаней при рівній кількості збігів (2/2)
    res_two = find_places(df, ["bridge", "tram_stop"], radius_m=300, limit=3)
    keys_two = [item["candidate_key"] for item in res_two]
    assert keys_two == ["way/101", "way/104", "way/102"], f"Невірний порядок: {keys_two}"

    # Повний збіг (3/3) має стояти вище часткового (2/3)
    res_three = find_places(df, ["bridge", "tram_stop", "church"], radius_m=300, limit=3)
    assert len(res_three) == 3, f"Очікувалось 3 кандидати, отримано {len(res_three)}"
    assert [item["matched_count"] for item in res_three] == [3, 3, 2], "Невірний пріоритет збігів"
    assert res_three[0]["candidate_key"] == "way/101", "Міст А має бути першим"

    missing_church = [m for m in res_three[2]["matches"] if m["category"] == "church"][0]
    assert missing_church["found"] is False, "Для не знайденого об'єкта found має бути False"
    assert (
        missing_church["name"] is None
        and missing_church["lat"] is None
        and missing_church["lon"] is None
        and missing_church["distance_m"] is None
        and missing_church["url"] is None
    ), "Поля не знайденого об'єкта мають бути None"

    # Перевірка межі радіуса (на межі входить, за межею — виключається)
    exact_radius = haversine_m(50.4500, 30.5200, 50.4510, 30.5200)
    res_on_border = find_places(df, ["bridge", "church"], radius_m=exact_radius, limit=3)
    assert len(res_on_border) == 1 and res_on_border[0]["candidate_key"] == "way/101", "Об'єкт на межі має входити"

    res_outside_border = find_places(df, ["bridge", "church"], radius_m=exact_radius - 0.01, limit=3)
    assert len(res_outside_border) == 0, "Об'єкт за межею має виключатися"

    # Обмеження максимальної кількості результатів (limit=3)
    res_limited = find_places(df, ["bridge", "tram_stop"], radius_m=1500, limit=3)
    assert len(res_limited) == 3, f"Очікувалось 3 результати, отримано {len(res_limited)}"

    # Порожній список за відсутності збігів >= 2
    res_empty = find_places(df, ["bridge", "church"], radius_m=100, limit=3)
    assert res_empty == [], f"Очікувався порожній список, отримано {res_empty}"

    # Валідація некоректних вхідних даних (ValueError)
    invalid_cases = [
        (["bridge"], 400),
        (["bridge", "bridge"], 400),
        (["bridge", "non_existent"], 400),
        (["bridge", "church"], 99),
        (["bridge", "church"], 1501),
    ]
    for categories, radius in invalid_cases:
        try:
            find_places(df, categories, radius_m=radius)
            raise AssertionError(f"Очікувався ValueError для {categories}, {radius}")
        except ValueError:
            pass

    print("OK: Усі перевірки checks.py успішно пройдені!")


if __name__ == "__main__":
    run_all_checks()
