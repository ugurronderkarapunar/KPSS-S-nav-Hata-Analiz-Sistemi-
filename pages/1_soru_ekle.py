"""
Soru Ekleme Sayfası.
Yeni soru ekler ve anlık analiz sonuçlarını gösterir.
"""
from __future__ import annotations

import streamlit as st
import sys
from pathlib import Path

# Proje kök dizinini Python path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import SessionLocal, init_db
from database.repository import (
    LessonRepository,
    SourceRepository,
)
from services.question_service import QuestionService
from embeddings.embedding_engine import EmbeddingEngine
from components.question_form import question_input_form
from components.sidebar import render_sidebar
from utils.logger import get_logger

logger = get_logger(__name__)


@st.cache_resource
def get_embedding_engine() -> EmbeddingEngine:
    """Embedding motorunu cache'le (bir kez yüklenir)."""
    return EmbeddingEngine()


def render_analysis_results(analysis_result) -> None:
    """Analiz sonuçlarını gösterir."""
    if not analysis_result:
        return

    has_similar = len(analysis_result.similar_questions) > 0
    has_cross = len(analysis_result.cross_matches) > 0

    if not has_similar and not has_cross:
        st.success("✅ Soru başarıyla kaydedildi! Benzer soru bulunamadı.")
        return

    st.info("🔍 Otomatik analiz sonuçları:")

    # Benzer sorular
    if has_similar:
        st.subheader("📋 Benzer Sorular")
        high_matches = [s for s in analysis_result.similar_questions if s.level == "HIGH"]
        if high_matches:
            st.warning(
                f"⚠️ **{len(high_matches)} adet çok benzer soru bulundu!** "
                "Bu soru daha önce sorulmuş olabilir."
            )

        for i, sim in enumerate(analysis_result.similar_questions[:10]):
            with st.expander(
                f"{sim.level_label} | %{sim.percentage} | "
                f"{sim.similar_question_source} {sim.similar_question_year or ''}",
                expanded=(sim.level == "HIGH"),
            ):
                st.caption(f"**Kaynak:** {sim.similar_question_source} | **Yıl:** {sim.similar_question_year or 'Belirtilmemiş'} | **Ders:** {sim.similar_question_lesson}")
                st.text(sim.similar_question_text[:500])

    # Yanlış şık - doğru cevap eşleşmeleri
    if has_cross:
        st.subheader("🔄 Yanlış Şık / Doğru Cevap Eşleşmeleri")
        for i, cross in enumerate(analysis_result.cross_matches[:10]):
            with st.expander(
                f"🔸 {cross.option_letter} şıkkı → {cross.matched_question_source} "
                f"{cross.matched_question_year or ''} doğru cevabı | %{cross.percentage}",
            ):
                st.caption(f"**Bu sorudaki {cross.option_letter} şıkkı (yanlış):**")
                st.text(cross.option_text[:300])
                st.caption(f"**{cross.matched_question_year} {cross.matched_question_source} sınavında DOĞRU CEVAP olarak geçmiş:**")
                st.text(cross.matched_question_text[:300])
                st.success(f"📌 Bu bilgi {cross.matched_question_year} yılında doğru cevaptı, şimdi yanlış şık olarak kullanılmış!")


def main():
    st.set_page_config(
        page_title="Soru Ekle | Exam Analyzer",
        page_icon="📝",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_sidebar()

    st.title("➕ Yeni Soru Ekle")
    st.caption("Yanlış yaptığınız soruyu sisteme kaydedin. Sistem otomatik analiz yapacaktır.")

    # Veritabanı ve servisleri başlat
    init_db()
    embedding_engine = get_embedding_engine()

    session = SessionLocal()
    try:
        lesson_repo = LessonRepository(session)
        source_repo = SourceRepository(session)

        # Varsayılan verileri ekle (yoksa)
        lesson_repo.seed_defaults()
        source_repo.seed_defaults()
        session.commit()

        lessons = lesson_repo.get_all()
        sources = source_repo.get_all()

        # Form
        form_data = question_input_form(lessons, sources)

        if form_data:
            question_service = QuestionService(session, embedding_engine)

            with st.spinner("Soru kaydediliyor ve analiz yapılıyor..."):
                question_id, analysis_result = question_service.add_question(
                    lesson_id=form_data["lesson_id"],
                    source_id=form_data["source_id"],
                    question_text=form_data["question_text"],
                    correct_answer=form_data["correct_answer"],
                    year=form_data.get("year"),
                    options=form_data["options"],
                )

            if question_id:
                st.toast("✅ Soru başarıyla kaydedildi!", icon="🎉")
                render_analysis_results(analysis_result)
                st.balloons()
                # Sayfayı yenileme (Streamlit doğal davranış)
                st.rerun()

    except Exception as e:
        logger.exception("Soru ekleme sayfasında hata")
        st.error(f"❌ Bir hata oluştu: {str(e)}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
