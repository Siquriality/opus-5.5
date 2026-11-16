from pathlib import Path

import pandas as pd
import streamlit as st


CATEGORY_LABELS = {
    "bridge": "Міст",
    "tram_stop": "Трамвайна зупинка",
    "church": "Церква",
    "park": "Парк",
    "monument": "Пам’ятник",
}

REQUIRED_COLUMNS = ["osm_type", "osm_id", "name", "category", "lat", "lon", "url"]


def load_places():
    csv_path = Path(__file__).resolve().parent / "data" / "places.csv"
    if not csv_path.is_file():
        st.error("Файл data/places.csv відсутній. Перевірте, чи завантажено набір даних.")
        st.stop()

    try:
        places = pd.read_csv(csv_path, dtype={"osm_id": str})
    except pd.errors.EmptyDataError:
        st.error("Файл data/places.csv порожній.")
        st.stop()
    except (pd.errors.ParserError, UnicodeDecodeError, OSError):
        st.error("Не вдалося прочитати data/places.csv. Перевірте формат і доступ до файлу.")
        st.stop()

    missing_columns = []
    for column in REQUIRED_COLUMNS:
        if column not in places.columns:
            missing_columns.append(column)
    if missing_columns:
        st.error(f"У файлі data/places.csv бракує колонок: {', '.join(missing_columns)}.")
        st.stop()

    if places.empty:
        st.error("У файлі data/places.csv немає жодного об’єкта.")
        st.stop()

    places["lat"] = pd.to_numeric(places["lat"], errors="coerce")
    places["lon"] = pd.to_numeric(places["lon"], errors="coerce")
    if not places["lat"].between(-90, 90).all() or not places["lon"].between(-180, 180).all():
        st.error(
            "У файлі data/places.csv є некоректні координати. "
            "Широта й довгота мають бути скінченними числами в межах "
            "від −90 до 90 і від −180 до 180 відповідно."
        )
        st.stop()

    return places


st.title("Де зроблено це фото?")
st.write("Пошук можливих місць за поєднанням орієнтирів")
st.caption("Область пошуку — вибрана ділянка лівого берега Києва")
st.write("Орієнтири, які видно на фото, обирайте вручну.")

places = load_places()

with st.form("search_form"):
    selected_categories = st.multiselect(
        "Орієнтири",
        options=list(CATEGORY_LABELS),
        format_func=CATEGORY_LABELS.__getitem__,
        placeholder="Оберіть орієнтири",
    )
    radius_m = st.slider(
        "Радіус пошуку, м",
        min_value=100,
        max_value=1500,
        value=400,
        step=50,
    )
    submitted = st.form_submit_button("Знайти місця")

if submitted:
    if len(selected_categories) < 2:
        st.warning("Оберіть щонайменше два орієнтири")
    else:
        selected_labels = ", ".join(
            CATEGORY_LABELS[category] for category in selected_categories
        )
        st.write(f"Обрані орієнтири: {selected_labels}")
        st.write(f"Радіус пошуку: {radius_m} м")
        st.info("Пошук буде підключено на наступному етапі")

st.header("Орієнтири в наборі даних")
st.caption("Огляд набору даних. Карта показує всі наявні орієнтири незалежно від вибору у формі.")
st.write(f"Усього об’єктів: {len(places)}")

category_names = places["category"].map(CATEGORY_LABELS).fillna("Невідома категорія")
for category_name, count in category_names.value_counts().items():
    st.write(f"{category_name}: {count}")

st.map(places[["lat", "lon"]])
with st.expander("Переглянути дані"):
    overview = pd.DataFrame({"Назва": places["name"], "Категорія": category_names})
    st.dataframe(overview, hide_index=True)

st.markdown("[© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)")
