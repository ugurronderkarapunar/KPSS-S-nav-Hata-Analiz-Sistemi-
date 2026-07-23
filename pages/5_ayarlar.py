"""
Ayarlar Sayfası.
Tema, veritabanı yönetimi, sistem bilgileri.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from datetime import datetime

from database.connection import SessionLocal, init_db, engine
from database.repository import LessonRepository, SourceRepository
from components.sidebar import render_sidebar
from config.settings import (
    DATABASE_URL,
    EMBEDDING_MODEL_NAME,
    SIMILARITY_HIGH,
    SIMILARITY_MEDIUM,
