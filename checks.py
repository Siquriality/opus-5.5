import pandas as pd
from search import find_places, haversine_m


def build_sample_df() -> pd.DataFrame:
    """Штучний набір даних із відомими відстанями для перевірки алгоритмів."""
    rows = [
        # Кластер 1: Повний збіг (bridge + tram_stop + church в межах ~150 м)
        # Примітка: у наборі 4 мости, 3 зупинки та 1 церква.
        # Алгоритм бере найрідкіснішу категорію за опорну (anchor).
        {"osm_type": "way", "osm_id": "101", "category": "bridge", "name": "Міст 1", "lat": 50.4500, "lon": 30.5200, "url": "https://www.openstreetmap.org/way/101"},
        {"osm_type": "node", "osm_id": "201", "category": "tram_stop", "name": "Зупинка 1", "lat": 50.4505, "lon": 30.5205, "url": "https://www.openstreetmap.org/node/201"},
        {"osm_type": "way", "osm_id": "301", "category": "church", "name": "Церква 1", "lat": 50.4510, "lon": 30.5210, "url": "https://www.openstreetmap.org/way/301"},

        # Кластер 2: Повний збіг (bridge + tram_stop), але далі один від одного (~300 м)
        {"osm_type": "way", "osm_id": "104", "category": "bridge", "name": "Міст 4 (далі)", "lat": 50.4700, "lon": 30.5400, "url": "https://www.openstreetmap.org/way/104"},
        {"osm_type": "node", "osm_id": "204", "category": "tram_stop", "name": "Зупинка 4 (далі)", "lat": 50.4720, "lon": 30.5425, "url": "https://www.openstreetmap.org/node/204"},

        # Кластер 3: Частковий збіг (тільки bridge, tram_stop поза радіусом 400 м)
        {"osm_type": "way", "osm_id": "102", "category": "bridge", "name": "Міст 2 (одинокий)", "lat": 50.4600, "lon": 30.5300, "url": "https://www.openstreetmap.org/way/102"},
        {"osm_type": "node", "osm_id": "202", "category": "tram_stop", "name": "Зупинка 2 (далеко)", "lat": 50.4650, "lon": 30.5350, "url": "https://www.openstreetmap.org/node/202"},

        # Кластер 4: Точка на межі радіуса (рівно ~400 м від way/301 по широті)
        {"osm_type": "way", "osm_id": "103", "category": "bridge", "name": "Міст на межі", "lat": 50.454597, "lon": 30.5210, "url": "https://www.openstreetmap.org/way/103"},
    ]
    return pd.DataFrame(rows)


def test_haversine_distance() -> None:
    """1. Перевірка формули розрахунку відстані haversine_m."""
    assert haversine_m(50.45, 30.52, 50.45, 30.52) == 0.0, "Відстань між однаковими точками має бути 0"

    d1 = haversine_m(50.45, 30.52, 50.46, 30.53)
    d2 = haversine_m(50.46, 30.53, 50.45, 30.52)
    assert abs(d1 - d2) < 1e-6, "Функція відстані має бути симетричною"

    dist = haversine_m(50.4500, 30.5200, 50.4510, 30.5200)
    assert 110.0 <= dist <= 112.5, f"Неочікувана відстань: {dist} м"


def test_ranking_and_completeness(df: pd.DataFrame) -> None:
    """2. Перевірка пріоритету повних збігів (2/2 вище за 1/2) та сортування за компактністю."""
    results = find_places(df, categories=["bridge", "tram_stop"], radius_m=400, limit=5)

    assert len(results) == 3, f"Очікувалось 3 кандидати, отримано {len(results)}"

    # Опорна категорія — tram_stop (3 зупинки < 4 мостів)
    assert results[0]["anchor"]["osm_id"] == "201", "Першим має бути найкомпактніший повний збіг (node/201)"
    assert results[0]["matched_count"] == 2
    assert results[0]["total_categories"] == 2

    assert results[1]["anchor"]["osm_id"] == "204", "Другим має бути менш компактний повний збіг (node/204)"
    assert results[1]["matched_count"] == 2

    assert results[2]["anchor"]["osm_id"] == "202", "Третім має йти частковий збіг (node/202)"
    assert results[2]["matched_count"] == 1


def test_radius_boundary(df: pd.DataFrame) -> None:
    """3. Перевірка граничних значень радіуса пошуку (включення на межі та виключення за межею)."""
    # Для ["bridge", "church"] опорною є church (1 церква < 4 мости), тобто way/301
    res_inside = find_places(df, categories=["bridge", "church"], radius_m=400, limit=5)
    anchor_301 = next(r for r in res_inside if r["anchor"]["osm_id"] == "301")
    assert anchor_301["matched_count"] == 2, "На межі 400 м обидва орієнтири мають бути знайдені"

    # Зменшуємо радіус нижче відстані до ближчого мосту way/101 (~132 м) -> збіг стає 1/2
    res_outside = find_places(df, categories=["bridge", "church"], radius_m=100, limit=5)
    anchor_301_small = next(r for r in res_outside if r["anchor"]["osm_id"] == "301")
    assert anchor_301_small["matched_count"] == 1, "При радіусі 100 м сусідній міст має відсіятися"


def test_limit_and_no_duplicates(df: pd.DataFrame) -> None:
    """4. Перевірка обмеження кількості результатів (limit) та відсутності дублікатів."""
    results = find_places(df, categories=["bridge", "tram_stop"], radius_m=400, limit=2)
    assert len(results) == 2, f"Очікувалось рівно 2 результати, отримано {len(results)}"

    anchor_ids = [(r["anchor"]["osm_type"], r["anchor"]["osm_id"]) for r in results]
    assert len(anchor_ids) == len(set(anchor_ids)), "Знайдено дублікати опорних об'єктів у видачі"


def test_invalid_inputs(df: pd.DataFrame) -> None:
    """5. Перевірка валідації некоректних вхідних даних (має викидатися ValueError)."""
    invalid_cases = [
        ([], 400),                          # порожній список категорій
        (["bridge"], 400),                  # менше 2 категорій
        (["bridge", "bridge"], 400),        # дублікат однієї категорії
        (["bridge", "hospital"], 400),      # невідома категорія
        (["bridge", "church"], 50),         # радіус менший за 100 м
        (["bridge", "church"], 2000),       # радіус більший за 1500 м
    ]

    for cats, rad in invalid_cases:
        try:
            find_places(df, categories=cats, radius_m=rad, limit=3)
            raise AssertionError(f"Очікувався ValueError для categories={cats}, radius_m={rad}")
        except ValueError:
            pass


def run_all_checks() -> None:
    df = build_sample_df()
    test_haversine_distance()
    test_ranking_and_completeness(df)
    test_radius_boundary(df)
    test_limit_and_no_duplicates(df)
    test_invalid_inputs(df)
    print("OK: Усі перевірки check.py успішно пройдені!")


if __name__ == "__main__":
    run_all_checks()
