"""
Veri Yönetimi Sayfası.
Excel/CSV dışa aktarma, yedekleme, geri yükleme.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import datetime

from database.connection import SessionLocal, init_db
from database.repository import LessonRepository, SourceRepository
from services.export_service import ExportService
from services.backup_service import BackupService
from components.sidebar import render_sidebar
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    st.set_page_config(
        page_title="Veri Yönetimi | Exam Analyzer",
        page_icon="💾",
        layout="wide",
    )

    render_sidebar()
    st.title("💾 Veri Yönetimi")

    init_db()
    session = SessionLocal()

    try:
        lesson_repo = LessonRepository(session)
        source_repo = SourceRepository(session)
        lesson_repo.seed_defaults()
        source_repo.seed_defaults()
        session.commit()

        lessons = lesson_repo.get_all()
        sources = source_repo.get_all()

        tab1, tab2, tab3 = st.tabs(["📤 Dışa Aktar", "💿 Yedekleme", "📥 Geri Yükleme"])

        with tab1:
            st.subheader("📤 Verileri Dışa Aktar")

            col1, col2, col3 = st.columns(3)
            with col1:
                lesson_options = ["Tümü"] + [l.name for l in lessons]
                selected_lesson = st.selectbox("Ders", lesson_options)
                lesson_id = None
                if selected_lesson != "Tümü":
                    lesson_obj = next((l for l in lessons if l.name == selected_lesson), None)
                    lesson_id = lesson_obj.id if lesson_obj else None

            with col2:
                source_options = ["Tümü"] + [s.name for s in sources]
                selected_source = st.selectbox("Kaynak", source_options)
                source_id = None
                if selected_source != "Tümü":
                    source_obj = next((s for s in sources if s.name == selected_source), None)
                    source_id = source_obj.id if source_obj else None

            with col3:
                export_format = st.selectbox("Format", ["Excel (.xlsx)", "CSV (.csv)"])

            export_service = ExportService(session)

            if st.button("📥 Dışa Aktar", type="primary"):
                with st.spinner("Veriler hazırlanıyor..."):
                    try:
                        if export_format == "Excel (.xlsx)":
                            data = export_service.to_excel_bytes(
                                lesson_id=lesson_id,
                                source_id=source_id,
                            )
                            st.download_button(
                                label="📥 Excel Dosyasını İndir",
                                data=data,
                                file_name=f"sorular_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        else:
                            data = export_service.to_csv_string(
                                lesson_id=lesson_id,
                                source_id=source_id,
                            )
                            st.download_button(
                                label="📥 CSV Dosyasını İndir",
                                data=data,
                                file_name=f"sorular_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv",
                            )
                    except Exception as e:
                        st.error(f"Dışa aktarma hatası: {e}")

        with tab2:
            st.subheader("💿 Yedekleme")
            backup_service = BackupService(session)

            if st.button("🔄 Yeni Yedek Oluştur", type="primary"):
                try:
                    backup_path = backup_service.create_backup()
                    st.success(f"✅ Yedek oluşturuldu: {backup_path.name}")
                except Exception as e:
                    st.error(f"Yedekleme hatası: {e}")

            st.divider()
            st.caption("Mevcut Yedekler:")
            backups = backup_service.list_backups()
            if backups:
                for b in backups:
                    st.text(f"📁 {b.name} - {datetime.fromtimestamp(b.stat().st_mtime).strftime('%d.%m.%Y %H:%M')}")
            else:
                st.info("Henüz yedek bulunmuyor.")

        with tab3:
            st.subheader("📥 Yedekten Geri Yükle")
            st.warning("⚠️ Geri yükleme mevcut verilerin üzerine yazar! Önce otomatik güvenlik yedeği alınır.")

            backup_service = BackupService(session)
            backups = backup_service.list_backups()

            if backups:
                selected_backup = st.selectbox(
                    "Geri yüklenecek yedeği seçin",
                    [b.name for b in backups],
                )
                if st.button("📥 Geri Yükle", type="primary"):
                    backup_path = next((b for b in backups if b.name == selected_backup), None)
                    if backup_path:
                        try:
                            with st.spinner("Geri yükleniyor..."):
                                backup_service.restore_backup(backup_path)
                            st.success("✅ Geri yükleme tamamlandı! Sayfayı yenileyin.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Geri yükleme hatası: {e}")
            else:
                st.info("Geri yüklenecek yedek bulunmuyor.")

    except Exception as e:
        logger.exception("Veri yönetimi sayfasında hata")
        st.error(f"❌ Hata: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
