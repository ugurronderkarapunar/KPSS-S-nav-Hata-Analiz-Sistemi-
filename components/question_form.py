"""
Soru ekleme/düzenleme form bileşeni.
"""
from __future__ import annotations

from typing import Optional

import streamlit as st

from config.settings import SOURCE_REQUIRES_YEAR


def question_input_form(
    lessons: list,
    sources: list,
    editing_question: Optional[dict] = None,
) -> Optional[dict]:
    """
    Soru giriş formunu render eder.

    Returns:
        Form verileri dict olarak veya None (iptal edildiyse).
    """
    with st.form(key="question_form", clear_on_submit=not editing_question):
        st.subheader("📝 Soru Bilgileri" if not editing_question else "✏️ Soruyu Düzenle")

        col1, col2 = st.columns(2)

        with col1:
            # Ders seçimi
            lesson_names = [l.name for l in lessons]
            default_lesson = editing_question["lesson_name"] if editing_question else None
            default_lesson_idx = (
                lesson_names.index(default_lesson)
                if default_lesson and default_lesson in lesson_names
                else 0
            )
            selected_lesson_name = st.selectbox(
                "📚 Ders *",
                lesson_names,
                index=default_lesson_idx,
            )
            selected_lesson = next(
                (l for l in lessons if l.name == selected_lesson_name), None
            )

        with col2:
            # Kaynak seçimi
            source_names = [s.name for s in sources]
            default_source = editing_question["source_name"] if editing_question else None
            default_source_idx = (
                source_names.index(default_source)
                if default_source and default_source in source_names
                else 0
            )
            selected_source_name = st.selectbox(
                "📖 Kaynak *",
                source_names,
                index=default_source_idx,
                on_change=None,
            )
            selected_source = next(
                (s for s in sources if s.name == selected_source_name), None
            )

        # Yıl (koşullu)
        year = None
        if selected_source and selected_source.name in SOURCE_REQUIRES_YEAR:
            year = st.number_input(
                "📅 Yıl *",
                min_value=2000,
                max_value=2030,
                value=editing_question.get("year") if editing_question else 2024,
                step=1,
            )

        # Soru metni
        question_text = st.text_area(
            "❓ Soru Metni *",
            value=editing_question.get("question_text", "") if editing_question else "",
            height=120,
            placeholder="Soruyu buraya yazın...",
        )

        st.divider()
        st.subheader("🔤 Şıklar")

        option_letters = ["A", "B", "C", "D", "E"]
        options_data = {}

        # Editing modunda mevcut şıkları al
        existing_options = {}
        if editing_question and "options" in editing_question:
            existing_options = {
                opt["letter"]: opt
                for opt in editing_question["options"]
            }

        for letter in option_letters:
            col_opt, col_note = st.columns([3, 2])
            existing = existing_options.get(letter, {})

            with col_opt:
                option_text = st.text_area(
                    f"{letter}) Şık Metni *",
                    value=existing.get("text", ""),
                    height=68,
                    key=f"opt_text_{letter}",
                    placeholder=f"{letter} şıkkını girin...",
                )

            with col_note:
                topic_note = st.text_area(
                    f"{letter}) Konu Notu",
                    value=existing.get("topic_note", ""),
                    height=68,
                    key=f"opt_note_{letter}",
                    placeholder="Bu şık hangi konuya ait?",
                )

            options_data[letter] = {
                "text": option_text,
                "topic_note": topic_note,
            }

        st.divider()

        # Doğru cevap
        correct_answer = st.radio(
            "✅ Doğru Cevap *",
            option_letters,
            horizontal=True,
            index=(
                option_letters.index(editing_question["correct_answer"])
                if editing_question and editing_question.get("correct_answer") in option_letters
                else 0
            ),
        )

        submitted = st.form_submit_button(
            "💾 Soruyu Kaydet" if not editing_question else "✅ Güncelle",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            # Validasyon
            errors = []
            if not question_text.strip():
                errors.append("Soru metni boş olamaz.")
            for letter in option_letters:
                if not options_data[letter]["text"].strip():
                    errors.append(f"{letter} şıkkı boş olamaz.")
            if selected_source and selected_source.name in SOURCE_REQUIRES_YEAR and year is None:
                errors.append("Bu kaynak için yıl zorunludur.")

            if errors:
                for error in errors:
                    st.error(f"⚠️ {error}")
                return None

            return {
                "lesson_id": selected_lesson.id if selected_lesson else None,
                "lesson_name": selected_lesson_name,
                "source_id": selected_source.id if selected_source else None,
                "source_name": selected_source_name,
                "year": year,
                "question_text": question_text.strip(),
                "correct_answer": correct_answer,
                "options": [
                    {
                        "letter": letter,
                        "text": options_data[letter]["text"].strip(),
                        "topic_note": options_data[letter]["topic_note"].strip(),
                    }
                    for letter in option_letters
                ],
            }

    return None
