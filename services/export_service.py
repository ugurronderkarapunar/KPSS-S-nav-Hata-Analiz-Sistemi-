"""
Dışa aktarma servisi.
Excel, CSV formatında veri dışa aktarımı yapar.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from database.models import Question, Option, Lesson, Source
from database.repository import QuestionRepository
from utils.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """Veri dışa aktarma servisi."""

    def __init__(self, session: Session):
        self.session = session
        self.question_repo = QuestionRepository(session)

    def export_to_dataframe(
        self,
        lesson_id: Optional[int] = None,
        source_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> pd.DataFrame:
        """Soruları pandas DataFrame olarak döndürür."""
        questions, _ = self.question_repo.get_all(
            lesson_id=lesson_id,
            source_id=source_id,
            year=year,
            limit=100000,  # Tümünü al
        )

        rows = []
        for q in questions:
            row = {
                "ID": q.id,
                "Ders": q.lesson.name if q.lesson else "",
                "Kaynak": q.source.name if q.source else "",
                "Yıl": q.year if q.year else "",
                "Soru Metni": q.question_text,
                "Doğru Cevap": q.correct_answer,
                "Eklenme Tarihi": q.created_at.strftime("%d.%m.%Y %H:%M"),
            }
            for opt in sorted(q.options, key=lambda o: o.option_letter):
                row[f"{opt.option_letter} Şıkkı"] = opt.option_text
                row[f"{opt.option_letter} Konu Notu"] = opt.topic_note or ""
            rows.append(row)

        return pd.DataFrame(rows)

    def to_excel_bytes(
        self,
        lesson_id: Optional[int] = None,
        source_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> bytes:
        """Excel dosyası olarak byte dizisi döndürür."""
        df = self.export_to_dataframe(lesson_id, source_id, year)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Sorular")
        return output.getvalue()

    def to_csv_string(
        self,
        lesson_id: Optional[int] = None,
        source_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> str:
        """CSV formatında string döndürür."""
        df = self.export_to_dataframe(lesson_id, source_id, year)
        return df.to_csv(index=False)
