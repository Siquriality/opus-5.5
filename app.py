import streamlit as st


CATEGORY_LABELS = {
    "bridge": "Міст",
    "tram_stop": "Трамвайна зупинка",
    "church": "Церква",
    "park": "Парк",
    "monument": "Пам’ятник",
}

st.title("Де зроблено це фото?")
st.write("Пошук можливих місць за поєднанням орієнтирів")
st.caption("Область пошуку — вибрана ділянка лівого берега Києва")

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
