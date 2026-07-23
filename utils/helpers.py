"""
Genel amaçlı yardımcı fonksiyonlar.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any

import pandas as pd


def generate_hash(text: str, length: int = 16) -> str:
    """Metinden benzersiz hash üretir."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def normalize_text(text: str) -> str:
    """Metni normalleştirir: küçük harf, fazla boşlukları temizle."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def truncate_text(text: str, max_length: int = 100) -> str:
    """Metni belirli uzunlukta keser, sonuna ... ekler."""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def format_date(date_obj: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Tarih nesnesini formatlar."""
    if date_obj is None:
        return "-"
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj)
        except ValueError:
            return date_obj
    return date_obj.strftime(fmt)


def safe_int(value: Any, default: int = 0) -> int:
    """Güvenli integer dönüşümü."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def percentage(numerator: int, denominator: int, decimals: int = 1) -> float:
    """Yüzde hesaplama, sıfıra bölme korumalı."""
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, decimals)
