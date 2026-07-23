"""
Ana Dashboard Sayfası.
KPI kartları, özet grafikler ve hızlı istatistikler.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from database.connection import SessionLocal, init_db
from database.repository import LessonRepository, SourceRepository
from analysis.stats import StatisticsCalculator
from components.kpi_cards import kpi_row
from components.charts import (
    chart_year_distribution,
    chart_topic_distribution,
    chart_pie_source,
    chart_answer_distribution,
)
from components.sidebar import render_sidebar
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    st.set_page_config(
        page_title="Exam Analyzer - KPSS Hata Analiz Sistemi",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Tema ayarı
    if "theme" not in st.session_state:
        st.session_state.theme = "light"

    # CSS
    with open("static/style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    render_sidebar()

    st.title("📊 Dashboard")
    st.caption("KPSS Sınav Hata Analiz Sistemi - Özet Görünüm")

    # Veritabanı başlat
    init_db()

    # Varsayılan verileri seed et
    session = SessionLocal()
    try:
        lesson_repo = LessonRepository(session)
        source_repo = SourceRepository(session)
        lesson_repo.seed_defaults()
        source_repo.seed_defaults()
        session.commit()
    finally:
        session.close()

    # İstatistikleri hesapla
    stats_calc = StatisticsCalculator()
    stats = stats_calc.get_dashboard_stats()

    # KPI kartları
    st.subheader("📈 Özet Göstergeler")
    kpi_row(stats)

    st.divider()

    # Grafikler - 2 sütunlu layout
    col1, col2 = st.columns(2)

    with col1:
        # Yıllara göre soru dağılımı
        year_data = stats_calc.get_year_distribution()
        chart_year_distribution(year_data)

        # Kaynak dağılımı
        source_data = stats_calc.get_source_distribution()
        chart_pie_source(source_data)

    with col2:
        # Konu dağılımı
        topics = stats_calc.get_topic_distribution()
        chart_topic_distribution(topics, top_n=10)

        # Doğru cevap dağılımı
        answer_data = stats_calc.get_answer_distribution()
        chart_answer_distribution(answer_data)

    # Alt bilgi
    st.divider()
    st.caption(f"Toplam {stats.total_questions} soru, {stats.total_topics} benzersiz konu analiz ediliyor.")

    # Ders özeti
    if stats.lesson_counts:
        st.subheader("📚 Ders Bazında Soru Sayıları")
        cols = st.columns(len(stats.lesson_counts))
        for i, (lesson_name, count) in enumerate(stats.lesson_counts.items()):
            with cols[i]:
                st.metric(label=lesson_name, value=count)


if __name__ == "__main__":
    main()
