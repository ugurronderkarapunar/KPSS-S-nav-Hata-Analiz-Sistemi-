"""
Detaylı Analiz Sayfası.
Tüm analizleri detaylı olarak gösterir.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd

from database.connection import SessionLocal, init_db
from database.repository import LessonRepository
from analysis.stats import StatisticsCalculator
from components.sidebar import render_sidebar
from components.charts import (
    chart_year_distribution,
    chart_topic_distribution,
    chart_pie_source,
    chart_answer_distribution,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    st.set_page_config(
        page_title="Analizler | Exam Analyzer",
        page_icon="📈",
        layout="wide",
    )

    render_sidebar()
    st.title("📈 Detaylı Analizler")

    init_db()
    stats_calc = StatisticsCalculator()

    # Filtreler
    session = SessionLocal()
    try:
        lesson_repo = LessonRepository(session)
        lesson_repo.seed_defaults()
        session.commit()
        lessons = lesson_repo.get_all()
    finally:
        session.close()

    lesson_options = ["Tümü"] + [l.name for l in lessons]
    selected_lesson = st.selectbox("📚 Ders Filtresi", lesson_options)
    lesson_id = None
    if selected_lesson != "Tümü":
        lesson_obj = next((l for l in lessons if l.name == selected_lesson), None)
        lesson_id = lesson_obj.id if lesson_obj else None

    # Tab'lar ile analizleri grupla
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dağılımlar",
        "🔥 Konu Analizi",
        "🔄 Tekrar Analizi",
        "📋 Özet Tablo",
    ])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            year_data = stats_calc.get_year_distribution(lesson_id)
            chart_year_distribution(year_data, title="Yıllara Göre Soru Dağılımı")
        with col2:
            source_data = stats_calc.get_source_distribution()
            chart_pie_source(source_data)

        answer_data = stats_calc.get_answer_distribution()
        chart_answer_distribution(answer_data)

    with tab2:
        topics = stats_calc.get_topic_distribution(lesson_id)
        chart_topic_distribution(topics, top_n=20, title="En Çok Çıkan Konular (Top 20)")

        st.subheader("📋 Konu Listesi")
        if topics:
            df_topics = pd.DataFrame([
                {"Konu": t.topic_name, "Soru Sayısı": t.count, "Oran (%)": t.percentage, "Ders": t.lesson_name}
                for t in topics
            ])
            st.dataframe(df_topics, use_container_width=True, hide_index=True)

    with tab3:
        st.subheader("🔄 Yıllara Göre Tekrar Eden Soru Oranı")
        similarity_rate = stats_calc.get_similarity_rate_by_year()
        if similarity_rate:
            df_rate = pd.DataFrame(
                {"Yıl": list(similarity_rate.keys()), "Tekrar Oranı (%)": list(similarity_rate.values())}
            ).sort_values("Yıl")
            st.bar_chart(df_rate.set_index("Yıl"), use_container_width=True)
        else:
            st.info("Henüz yeterli veri yok.")

    with tab4:
        st.subheader("📋 Özet İstatistik Tablosu")
        stats = stats_calc.get_dashboard_stats()
        summary_data = {
            "Metrik": [
                "Toplam Soru", "Toplam Konu", "Benzer Soru Çifti",
                "Tekrar Oranı (%)", "En Çok Çıkan Konu", "En Zayıf Konu",
            ],
            "Değer": [
                stats.total_questions, stats.total_topics, stats.total_similar_pairs,
                stats.similarity_rate, stats.top_topic, stats.most_wrong_topic,
            ],
        }
        st.table(pd.DataFrame(summary_data))


if __name__ == "__main__":
    main()
