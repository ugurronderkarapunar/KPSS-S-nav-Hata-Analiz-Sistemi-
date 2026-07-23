"""
Yedekleme ve geri yükleme servisi.
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from config.settings import BACKUP_DIR, DATA_DIR
from database.models import Base          # <-- Doğru konumdan import
from database.connection import engine    # engine burada kullanılıyor
from utils.logger import get_logger

logger = get_logger(__name__)


class BackupService:
    """Veritabanı yedekleme ve geri yükleme."""

    def __init__(self, session: Session):
        self.session = session

    def create_backup(self) -> Path:
        """
        SQLite veritabanı dosyasını kopyalayarak yedekler.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"backup_{timestamp}.db"

        # SQLite dosyasını bul
        db_path = DATA_DIR / "exam_analyzer.db"
        if db_path.exists():
            shutil.copy2(db_path, backup_file)
            logger.info(f"Yedekleme oluşturuldu: {backup_file}")
        else:
            raise FileNotFoundError(f"Veritabanı dosyası bulunamadı: {db_path}")

        return backup_file

    def list_backups(self) -> list[Path]:
        """Mevcut yedekleri listeler."""
        if not BACKUP_DIR.exists():
            return []
        return sorted(
            BACKUP_DIR.glob("backup_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

    def restore_backup(self, backup_path: Path) -> bool:
        """Yedekten geri yükleme yapar."""
        db_path = DATA_DIR / "exam_analyzer.db"

        if not backup_path.exists():
            raise FileNotFoundError(f"Yedek dosyası bulunamadı: {backup_path}")

        # Mevcut veritabanını yedekle (güvenlik)
        if db_path.exists():
            safety_backup = BACKUP_DIR / f"safety_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, safety_backup)

        # Engine'i kapat
        engine.dispose()

        # Yedeği geri yükle
        shutil.copy2(backup_path, db_path)
        logger.info(f"Yedek geri yüklendi: {backup_path}")

        return True
