"""
Kenar çubuğu bileşeni.
"""
from __future__ import annotations

import streamlit as st


def render_sidebar() -> None:
    """Global kenar çubuğunu render eder."""
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/exam.png",
            width=80,
        )
        st.title("📋 Sınav Analiz")
        st.caption("KPSS Hata Analiz Sistemi")

        st.divider()

        # Tema seçimi
        if "theme" not in st.session_state:
            st.session_state.theme = "light"

        theme = st.selectbox(
            "🎨 Tema",
            ["Açık", "Koyu"],
            index=0 if st.session_state.theme == "light" else 1,
            key="theme_selector",
            on_change=lambda: setattr(
                st.session_state,
                "theme",
                "dark" if st.session_state.theme_selector == "Koyu" else "light",
            ),
        )

        st.divider()

        # Hızlı istatistikler
        st.subheader("⚡ Hızlı Erişim")
        st.page_link("app.py", label="🏠 Dashboard", icon="📊")
        st.page_link("pages/1_soru_ekle.py", label="➕ Soru Ekle", icon="📝")
        st.page_link("pages/2_arama.py", label="🔍 Arama", icon="🔎")
        st.page_link("pages/3_analizler.py", label="📈 Analizler", icon="📉")
        st.page_link("pages/4_veri_yonetimi.py", label="💾 Veri Yönetimi", icon="🗄️")
        st.page_link("pages/5_ayarlar.py", label="⚙️ Ayarlar", icon="🔧")

        st.divider()
        st.caption("© 2026 Exam Analyzer v1.0")
        st.caption("Geliştirici: Senior Architect")
