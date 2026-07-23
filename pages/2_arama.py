"""
Gelişmiş Arama Sayfası.
Tam metin, konu, şık, yıl, ders, kaynak bazlı arama yapar.
Anlamsal benzerlik araması da içerir.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from database.connection import SessionLocal, init_db
from database.repository import (
    LessonRepository,
    SourceRepository,
    QuestionRepository,
)
from database.models import Question, Option
from analysis.similarity import SimilarityAnalyzer, SimilarityResult
from embeddings.embedding_engine import EmbeddingEngine
from components.sidebar import render_sidebar
from config.settings import SIMILARITY_MEDIUM
from utils.helpers import truncate_text, format_date
from utils.logger import get_logger

logger = get_logger(__name__)


@st.cache_resource
def get_embedding_engine() -> EmbeddingEngine:
    return EmbeddingEngine()


def search_by_text(
    question_repo: QuestionRepository,
    search_term: str,
    lesson_id: int | None,
    source_id: int | None,
    year: int | None,
    search_in: str,
    offset: int,
    limit: int,
) -> tuple[list[Question], int]:
    """Metin tabanlı arama."""
    return question_repo.get_all(
        lesson_id=lesson_id,
        source_id=source_id,
        year=year,
        search_text=search_term if search_term else None,
        offset=offset,
        limit=limit,
    )


def display_question_card(question: Question, index: int) -> None:
    """Soru kartını gösterir."""
    with st.container():
        st.markdown(f"**#{question.id}** | 📚 {question.lesson.name if question.lesson else '?'} | 📖 {question.source.name if question.source else '?'} | 📅 {question.year or 'Belirtilmemiş'} | 🕐 {format_date(question.created_at)}")
        st.markdown(f"**Soru:** {truncate_text(question.question_text, 200)}")

        # Şıkları göster
        for opt in sorted(question.options, key=lambda o: o.option_letter):
            is_correct = opt.option_letter == question.correct_answer
            prefix = "✅" if is_correct else "❌"
            st.caption(f"{prefix} **{opt.option_letter})** {truncate_text(opt.option_text, 150)}")
            if opt.topic_note:
                st.caption(f"   📌 Konu: *{opt.topic_note}*")

        st.divider()


def main():
    st.set_page_config(
        page_title="Arama | Exam Analyzer",
        page_icon="🔍",
        layout="wide",
    )

    render_sidebar()

    st.title("🔍 Gelişmiş Arama")
    st.caption("Soru metni, şık, konu notu, yıl, ders ve kaynak bazlı arama yapın.")

    init_db()
    session = SessionLocal()

    try:
        lesson_repo = LessonRepository(session)
        source_repo = SourceRepository(session)
        question_repo = QuestionRepository(session)

        lesson_repo.seed_defaults()
        source_repo.seed_defaults()
        session.commit()

        lessons = lesson_repo.get_all()
        sources = source_repo.get_all()

        # Arama formu
        col1, col2, col3 = st.columns(3)

        with col1:
            search_term = st.text_input(
                "🔎 Arama terimi",
                placeholder="Soru, şık veya konu notunda ara...",
            )

        with col2:
            lesson_options = ["Tümü"] + [l.name for l in lessons]
            selected_lesson = st.selectbox("📚 Ders", lesson_options)
            lesson_id = None
            if selected_lesson != "Tümü":
                lesson_obj = next((l for l in lessons if l.name == selected_lesson), None)
                lesson_id = lesson_obj.id if lesson_obj else None

        with col3:
            source_options = ["Tümü"] + [s.name for s in sources]
            selected_source = st.selectbox("📖 Kaynak", source_options)
            source_id = None
            if selected_source != "Tümü":
                source_obj = next((s for s in sources if s.name == selected_source), None)
                source_id = source_obj.id if source_obj else None

        # İkinci satır
        col4, col5 = st.columns(2)
        with col4:
            year = st.number_input(
                "📅 Yıl (boş = tümü)",
                min_value=2000,
                max_value=2030,
                value=None,
                step=1,
            )
            year = int(year) if year is not None and year > 0 else None

        with col5:
            search_in = st.selectbox(
                "Arama alanı",
                ["Her yerde", "Soru metninde", "Şıklarda", "Konu notlarında"],
            )

        # Arama butonu ve sonuçlar
        if search_term or lesson_id or source_id or year:
            st.divider()

            # Sayfalama
            page = st.number_input("Sayfa", min_value=1, value=1, step=1) - 1
            limit = 20
            offset = page * limit

            questions, total = search_by_text(
                question_repo=question_repo,
                search_term=search_term,
                lesson_id=lesson_id,
                source_id=source_id,
                year=year,
                search_in=search_in,
                offset=offset,
                limit=limit,
            )

            st.info(f"🔍 **{total}** sonuç bulundu. (Sayfa {page + 1}/{(total // limit) + 1})")

            # Anlamsal arama (opsiyonel - arama terimi varsa)
            if search_term and len(search_term.strip()) > 3:
                with st.expander("🧠 Anlamsal Benzerlik Araması (AI)", expanded=False):
                    st.caption("Metin benzerliği kullanılarak anlam olarak benzeyen sorular.")
                    try:
                        embedding_engine = get_embedding_engine()
                        analyzer = SimilarityAnalyzer(
                            embedding_engine=embedding_engine,
                            question_repo=question_repo,
                            option_repo=None,
                            similarity_repo=None,
                            cross_match_repo=None,
                        )
                        semantic_results = analyzer.find_similar_to_text(
                            search_term,
                            threshold=SIMILARITY_MEDIUM,
                            limit=10,
                        )
                        if semantic_results:
                            for sim in semantic_results:
                                with st.container():
                                    st.markdown(f"**Benzerlik: %{sim.percentage}** | {sim.similar_question_source} {sim.similar_question_year or ''}")
                                    st.text(truncate_text(sim.similar_question_text, 250))
                                    st.divider()
                        else:
                            st.caption("Anlamsal benzerlikte eşleşme bulunamadı.")
                    except Exception as e:
                        st.warning(f"Anlamsal arama şu anda kullanılamıyor: {e}")

            # Sonuçları listele
            for i, q in enumerate(questions):
                display_question_card(q, i)

            # Sayfalama navigasyonu
            if total > limit:
                total_pages = (total // limit) + 1
                st.caption(f"Sayfa {page + 1} / {total_pages}")
        else:
            st.info("👆 Arama yapmak için en az bir filtre veya arama terimi girin.")

    except Exception as e:
        logger.exception("Arama sayfasında hata")
        st.error(f"❌ Hata: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
