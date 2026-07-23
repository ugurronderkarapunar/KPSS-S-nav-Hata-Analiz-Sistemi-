"""
Uygulama genelinde kullanılan merkezi ayar sabitleri.
İleride ortam değişkenlerinden veya .env dosyasından okunacak şekilde genişletilebilir.
"""
from __future__ import annotations

import os
from pathlib import Path

# Proje kök dizini (bu dosyadan iki seviye yukarısı)
ROOT_DIR: Path = Path(__file__).resolve().parent.parent

# Veri dizini
DATA_DIR: Path = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Veritabanı URL'si
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'exam_analyzer.db'}"
)

# Yedekleme dizini
BACKUP_DIR: Path = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Log dizini
LOG_DIR: Path = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE: Path = LOG_DIR / "app.log"

# Embedding model adı
EMBEDDING_MODEL_NAME: str = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr"
)

# Fallback embedding modeli (Türkçe model yüklenemezse)
EMBEDDING_MODEL_FALLBACK: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Benzerlik eşik değerleri
SIMILARITY_HIGH: float = 0.90       # Çok yüksek benzerlik - aynı soru
SIMILARITY_MEDIUM: float = 0.78    # Yüksek benzerlik
SIMILARITY_LOW: float = 0.65       # Orta benzerlik

# Sayfalama
PAGE_SIZE: int = 20

# Desteklenen dersler (ileride veritabanından da okunabilir)
DEFAULT_LESSONS: list[dict[str, str]] = [
    {"name": "Tarih", "code": "TARIH"},
    {"name": "Vatandaşlık", "code": "VATANDASLIK"},
]

# Kaynak türleri
SOURCE_TYPES: list[str] = ["KPSS", "ÖSYM", "Deneme", "Soru Bankası"]

# Kaynak türlerinden hangileri yıl zorunlu?
SOURCE_REQUIRES_YEAR: set[str] = {"KPSS", "ÖSYM", "Deneme"}

# Log seviyesi
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Streamlit Cloud'da kalıcı depolama uyarısı
STREAMLIT_CLOUD_WARNING: bool = os.getenv("STREAMLIT_CLOUD", "false").lower() == "true"
