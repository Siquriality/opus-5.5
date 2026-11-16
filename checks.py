import pandas as pd
from search import find_places, haversine_m


def build_sample_df() -> pd.DataFrame:
    """Штучний набір даних із відомими відстанями для перевірки алгоритмів."""
    rows = [
        # Кластер 1: Повний збіг (bridge + tram_stop + church в межах ~150 м)
        # У наборі 4 мости, 3 зупинки та 1 церква -> опорною категорією стає найрідкісніша.
        {"osm_type": "way", "osm_id": "101", "category": "bridge", "name": "Міст 1", "lat": 50.4500, "lon": 30.5200, "url": "https://www.openstreetmap.org/way/101"},
        {"osm_type": "node", "osm_id": "201", "category": "tram_stop", "name": "Зупинка 1", "lat": 50.4505, "lon": 30.5205, "url": "https://www.openstreetmap.org/node/201"},
        {"osm_type": "way", "osm_id": "301", "category": "church", "name": "Церква 1", "lat": 50.4510, "lon": 30.5210, "url": "https://www.openstreetmap.org/way/301"},

        # Кластер 2: Повний збіг (bridge + tram_stop), але далі один від одного (~300 м)
        {"osm_type": "way", "osm_id": "104", "category": "bridge", "name": "Міст 4 (далі)", "lat": 50.4700, "lon": 30.5400, "url": "https://www.openstreetmap.org/way/104"},
        {"osm_type": "node", "osm_id": "204", "category": "tram_stop", "name": "Зупинка 4 (далі)", "lat": 50.4720, "lon": 30.5425, "url": "https://www.openstreetmap.org/node/204"},

        # Кластер 3: Одиночні точки (відстань > 400 м -> мають відсіятися, бо matched_count < 2)
        {"osm_type": "way", "osm_id": "102", "category": "bridge", "name": "Міст 2 (одинокий)", "lat": 50.4600, "lon": 30.5300, "url": "https://www.openstreetmap.org/way/102"},
        {"osm_type": "node", "osm_id": "202", "category": "tram_stop", "name": "Зупинка 2 (далеко)", "lat": 50.4650, "lon": 30.5350, "url": "https://www.openstreetmap.org/node/202"},

        # Додатковий міст для збереження переваги кількості (4 мости > 3 зупинки)
        {"osm_type": "way", "osm_id": "103", "category": "bridge", "name": "Міст 3 (резерв)", "lat": 50.4900, "lon": 30.5600, "url": "https://www.openstreetmap.org/way/103"},
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
    """2. Перевірка фільтрації (<2 збігів відсіюються) та сортування за компактністю."""
    results = find_places(df, categories=["bridge", "tram_stop"], radius_m=400, limit=5)

    # У видачу потрапляють тільки кандидати з мінімум 2 збігами (одиночний node/202 відсіюється)
    assert len(results) == 2, f"Очікувалось 2 кандидати з >=2 збігами, отримано {len(results)}"

    assert results[0]["candidate_key"] == "node/201", "Першим має бути найкомпактніший збіг (node/201)"
    assert results[0]["matched_count"] == 2
    assert results[0]["requested_count"] == 2

    assert results[1]["candidate_key"] == "node/204", "Другим має бути менш компактний збіг (node/204)"
    assert results[1]["matched_count"] == 2
    assert results[1]["requested_count"] == 2


def test_radius_boundary() -> None:
    """3. Перевірка точної межі радіуса на окремій парі об'єктів (1 церква + 1 міст)."""
    boundary_df = pd.DataFrame([
        {"osm_type": "way", "osm_id": "301", "category": "church", "name": "Церква межова", "lat": 50.4500, "lon": 30.5200, "url": "https://www.openstreetmap.org/way/301"},
        {"osm_type": "way", "osm_id": "101", "category": "bridge", "name": "Міст межовий", "lat": 50.4525, "lon": 30.5200, "url": "https://www.openstreetmap.org/way/101"},
    ])
    exact_dist = haversine_m(50.4500, 30.5200, 50.4525, 30.5200)

    # Точний радіус == відстані -> пара має знайтися
    res_exact = find_places(boundary_df, categories=["bridge", "church"], radius_m=exact_dist, limit=5)
    assert len(res_exact) == 1, "На точній межі радіуса пара об'єктів має знаходитися"
    assert res_exact[0]["matched_count"] == 2

    # Трохи менший радіус -> пара не дає 2 збігів, видача порожня
    res_smaller = find_places(boundary_df, categories=["bridge", "church"], radius_m=exact_dist - 0.5, limit=5)
    assert res_smaller == [], f"При радіусі меншому за відстань очікувався [], отримано {res_smaller}"


def test_limit_and_no_duplicates(df: pd.DataFrame) -> None:
    """4. Перевірка обмеження кількості результатів (limit) та відсутності дублікатів."""
    results = find_places(df, categories=["bridge", "tram_stop"], radius_m=400, limit=1)
    assert len(results) == 1, f"Очікувався рівно 1 результат при limit=1, отримано {len(results)}"

    results_all = find_places(df, categories=["bridge", "tram_stop"], radius_m=400, limit=5)
    candidate_keys = [r["candidate_key"] for r in results_all]
    assert len(candidate_keys) == len(set(candidate_keys)), "Знайдено дублікати кандидатів у видачі"


def test_invalid_inputs(df: pd.DataFrame) -> None:
    """5. Перевірка валідації некоректних вхідних даних (має викидатися ValueError)."""
    invalid_cases = [
        ([], 400),                          # порожній список категорій
        (["bridge"], 400),                  # менше 2 категорій
        (["bridge", "bridge"], 400),        # дублікат однієї категорії
        (["bridge", "hospital"], 400),      # невідома категорія
        (["bridge", "church"], 50),         # радіус менший за 100 м
        (["bridge", "church"], 2000),       # радіус більший за 1500 м
        (["bridge", "church"], float("nan")),  # NaN радіус
        (["bridge", "church"], float("inf")),  # нескінченний радіус
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
    test_radius_boundary()
    test_limit_and_no_duplicates(df)
    test_invalid_inputs(df)
    print("OK: Усі перевірки check.py успішно пройдені!")


if __name__ == "__main__":
    run_all_checks()
