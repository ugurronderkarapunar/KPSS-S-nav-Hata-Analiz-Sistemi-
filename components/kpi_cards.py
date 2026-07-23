"""
Dashboard KPI kart bileşenleri.
"""
from __future__ import annotations

import streamlit as st


def kpi_card(
    title: str,
    value: str | int | float,
    icon: str = "📊",
    delta: str | None = None,
    color: str = "#1f77b4",
) -> None:
    """
    Modern KPI kartı render eder.

    Args:
        title: Kart başlığı
        value: Gösterilecek değer
        icon: Emoji ikonu
        delta: Değişim göstergesi (opsiyonel)
        color: Vurgu rengi
    """
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
        border: 1px solid {color}30;
        border-left: 4px solid {color};
        border-radius: 12px;
        padding: 1.2rem 1rem;
        margin: 0.3rem 0;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    "
    onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(0,0,0,0.1)';"
    onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none';"
    >
        <div style="font-size: 2rem; margin-bottom: 0.3rem;">{icon}</div>
        <div style="font-size: 1.6rem; font-weight: 700; color: {color};">{value}</div>
        <div style="font-size: 0.85rem; color: #666; margin-top: 0.2rem;">{title}</div>
        {"<div style='font-size: 0.75rem; color: #28a745; margin-top: 0.2rem;'>▲ " + str(delta) + "</div>" if delta else ""}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def kpi_row(stats) -> None:
    """KPI kartlarını grid olarak render eder."""
    cols = st.columns(4)

    with cols[0]:
        kpi_card("Toplam Soru", stats.total_questions, "📝", color="#1f77b4")

    with cols[1]:
        kpi_card("Toplam Konu", stats.total_topics, "📚", color="#ff7f0e")

    with cols[2]:
        kpi_card("Benzer Soru Çifti", stats.total_similar_pairs, "🔄", color="#2ca02c")

    with cols[3]:
        kpi_card("Tekrar Oranı", f"%{stats.similarity_rate}", "📈", color="#d62728")

    cols2 = st.columns(4)
    with cols2[0]:
        kpi_card("En Çok Çıkan Konu", stats.top_topic[:30] if stats.top_topic != "-" else "-", "⭐", color="#9467bd")
    with cols2[1]:
        kpi_card("Çıkış Sayısı", stats.top_topic_count, "🔢", color="#8c564b")
    with cols2[2]:
        kpi_card("En Zayıf Konu", stats.most_wrong_topic[:30] if stats.most_wrong_topic != "-" else "-", "⚠️", color="#e377c2")
    with cols2[3]:
        kpi_card("Son Soru", stats.last_question_date, "🕐", color="#17becf")
