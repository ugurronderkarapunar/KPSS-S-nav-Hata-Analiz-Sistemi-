"""
Ayarlar Sayfası.
Tema, veritabanı yönetimi, sistem bilgileri.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from database.connection import SessionLocal, init_db, engine
from database.repository import LessonRepository, SourceRepository
from components.sidebar import render_sidebar
from config.settings import (
    DATABASE_URL,
    EMBEDDING_MODEL_NAME,
    SIMILARITY_HIGH,
    SIMILARITY_MEDIUM,
    SIMILARITY_LOW,
    LOG_FILE,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    st.set_page_config(
        page_title="Ayarlar | Exam Analyzer",
        page_icon="⚙️",
        layout="wide",
    )

    render_sidebar()
    st.title("⚙️ Ayarlar ve Sistem Bilgisi")

    init_db()
    session = SessionLocal()

    try:
        lesson_repo = LessonRepository(session)
        source_repo = SourceRepository(session)
        lesson_repo.seed_defaults()
        source_repo.seed_defaults()
        session.commit()

        tab1, tab2 = st.tabs(["🔧 Sistem Bilgisi", "🗄️ Veritabanı Yönetimi"])

        with tab1:
            st.subheader("📋 Yapılandırma")
            info = {
                "Veritabanı": DATABASE_URL,
                "Embedding Model": EMBEDDING_MODEL_NAME,
                "Benzerlik Eşikleri": f"Yüksek: {SIMILARITY_HIGH}, Orta: {SIMILARITY_MEDIUM}, Düşük: {SIMILARITY_LOW}",
                "Log Dosyası": str(LOG_FILE),
            }
            for key, value in info.items():
                st.text(f"{key}: {value}")

            st.subheader("📊 Veritabanı İstatistikleri")
            total_questions = session.query(Question).count() if 'Question' in dir() else 0
            # Quick inline import to avoid circular issues
            from database.models import Question, Lesson, Source
            total_q = session.query(Question).count()
            total_lessons = session.query(Lesson).count()
            total_sources = session.query(Source).count()
            st.text(f"Toplam Soru: {total_q}")
            st.text(f"Toplam Ders: {total_lessons}")
            st.text(f"Toplam Kaynak Türü: {total_sources}")

        with tab2:
            st.subheader("🛠️ Bakım İşlemleri")
            st.warning("Bu işlemler geri alınamaz, dikkatli kullanın.")

            if st.button("🔄 Tabloları Yeniden Oluştur (Tüm veri silinir!)"):
                with st.spinner("Tablolar siliniyor ve yeniden oluşturuluyor..."):
                    from database.models import Base
                    Base.metadata.drop_all(bind=engine)
                    Base.metadata.create_all(bind=engine)
                    st.success("✅ Tablolar sıfırlandı. Varsayılan dersler ve kaynaklar yeniden eklenecek.")
                    lesson_repo.seed_defaults()
                    source_repo.seed_defaults()
                    session.commit()
                st.rerun()

            if st.button("📦 Varsayılan Ders/Kaynak Ekle (Eksikse)"):
                lesson_repo.seed_defaults()
                source_repo.seed_defaults()
                session.commit()
                st.success("✅ Kontrol edildi, eksikler eklendi.")

    except Exception as e:
        logger.exception("Ayarlar sayfasında hata")
        st.error(f"❌ Hata: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
