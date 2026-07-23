"""
Veritabanı bağlantı yönetimi.
SQLAlchemy engine ve session factory.
PostgreSQL'e geçiş yalnızca DATABASE_URL değiştirilerek yapılabilir.
"""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL
from utils.logger import get_logger

logger = get_logger(__name__)

# Engine oluşturma
# SQLite için özel ayarlar
if "sqlite" in DATABASE_URL:
    engine: Engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},  # SQLite çoklu thread desteği
        pool_pre_ping=True,
    )
else:
    # PostgreSQL veya diğer veritabanları için
    engine: Engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

# Session factory
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite bağlantısında performans ayarları."""
    if "sqlite" in DATABASE_URL:
        import sqlite3
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()


def get_db() -> Generator[Session, None, None]:
    """
    Veritabanı oturumu üretir.
    Context manager olarak kullanılır, otomatik kapatır.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Veritabanı işlem hatası")
        raise
    finally:
        session.close()


def init_db() -> None:
    """Tüm tabloları oluşturur (uygulama başlangıcında çağrılır)."""
    from database.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Veritabanı tabloları oluşturuldu/kontrol edildi.")


def drop_db() -> None:
    """Tüm tabloları siler (dikkatli kullanın)."""
    from database.models import Base
    Base.metadata.drop_all(bind=engine)
    logger.warning("Veritabanı tabloları silindi!")
