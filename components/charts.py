"""
Grafik bileşenleri.
Plotly kullanarak etkileşimli grafikler oluşturur.
"""
from __future__ import annotations

from typing import Optional

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from analysis.stats import StatisticsCalculator, TopicStats
from utils.logger import get_logger

logger = get_logger(__name__)


def chart_year_distribution(
    data: dict[int, int],
    title: str = "Yıllara Göre Soru Sayısı",
    height: int = 350,
) -> None:
    """Yıllara göre soru dağılımı çubuk grafiği."""
    if not data:
        st.info("Henüz yıl bilgisi olan soru bulunmuyor.")
        return

    df = pd.DataFrame(
        {"Yıl": list(data.keys()), "Soru Sayısı": list(data.values())}
    ).sort_values("Yıl")

    fig = px.bar(
        df,
        x="Yıl",
        y="Soru Sayısı",
        title=title,
        text="Soru Sayısı",
        color="Soru Sayısı",
        color_continuous_scale="Blues",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(tickmode="linear", dtick=1),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_topic_distribution(
    topics: list[TopicStats],
    top_n: int = 15,
    title: str = "En Çok Çıkan Konular",
    height: int = 450,
) -> None:
    """Konu dağılımı yatay çubuk grafiği."""
    if not topics:
        st.info("Henüz konu verisi bulunmuyor.")
        return

    df = pd.DataFrame([
        {"Konu": t.topic_name[:50], "Soru Sayısı": t.count, "Ders": t.lesson_name}
        for t in topics[:top_n]
    ])

    fig = px.bar(
        df,
        x="Soru Sayısı",
        y="Konu",
        orientation="h",
        title=title,
        text="Soru Sayısı",
        color="Ders",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_pie_source(data: dict[str, int], height: int = 350) -> None:
    """Kaynaklara göre pasta grafiği."""
    if not data:
        st.info("Veri bulunmuyor.")
        return

    fig = px.pie(
        names=list(data.keys()),
        values=list(data.values()),
        title="Kaynaklara Göre Dağılım",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textinfo="label+percent+value")
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)


def chart_answer_distribution(data: dict[str, int], height: int = 300) -> None:
    """Doğru cevap şık dağılımı."""
    if not data:
        return

    all_letters = ["A", "B", "C", "D", "E"]
    values = [data.get(letter, 0) for letter in all_letters]

    fig = px.bar(
        x=all_letters,
        y=values,
        title="Doğru Cevap Şık Dağılımı",
        text=values,
        color=all_letters,
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
        xaxis_title="Şık",
        yaxis_title="Sayı",
    )
    st.plotly_chart(fig, use_container_width=True)


def chart_heatmap_similarity(data: list[dict], height: int = 400) -> None:
    """Benzerlik ısı haritası (opsiyonel)."""
    if not data:
        st.info("Benzerlik verisi bulunmuyor.")
        return

    df = pd.DataFrame(data)
    fig = px.density_heatmap(
        df,
        x="year",
        y="topic",
        z="count",
        title="Konu-Yıl Isı Haritası",
    )
    fig.update_layout(height=height)
    st.plotly_chart(fig, use_container_width=True)
