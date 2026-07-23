"""
İstatistik hesaplama modülü.
Dashboard ve analiz sayfaları için gerekli tüm istatistikleri üretir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func

from database.models import (
    Question,
    Option,
    QuestionSimilarity,
    TopicFrequency,
    Lesson,
    Source,
)
from database.connection import SessionLocal
from database.repository import (
    QuestionRepository,
    TopicFrequencyRepository,
)
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DashboardStats:
    """Dashboard için özet istatistikler."""
    total_questions: int = 0
    total_topics: int = 0
    total_similar_pairs: int = 0
    similarity_rate: float = 0.0
    top_topic: str = "-"
    top_topic_count: int = 0
    last_question_date: str = "-"
    most_wrong_topic: str = "-"
    lesson_counts: dict[str, int] = None

    def __post_init__(self):
        if self.lesson_counts is None:
            self.lesson_counts = {}


@dataclass
class TopicStats:
    """Konu bazlı istatistik."""
    topic_name: str
    count: int
    lesson_name: str
    percentage: float = 0.0


class StatisticsCalculator:
    """İstatistik hesaplama sınıfı."""

    def __init__(self):
        self.session = SessionLocal()

    def get_dashboard_stats(self) -> DashboardStats:
        """Dashboard için özet istatistikleri hesaplar."""
        stats = DashboardStats()

        try:
            # Toplam soru
            stats.total_questions = (
                self.session.query(func.count(Question.id)).scalar() or 0
            )

            # Toplam benzersiz konu
            stats.total_topics = (
                self.session.query(func.count(TopicFrequency.id)).scalar() or 0
            )

            # Toplam benzer soru çifti
            stats.total_similar_pairs = (
                self.session.query(func.count(QuestionSimilarity.id))
                .filter(QuestionSimilarity.similarity_score >= 0.78)
                .scalar()
            ) or 0

            # Benzerlik oranı
            if stats.total_questions > 0:
                stats.similarity_rate = round(
                    (stats.total_similar_pairs / stats.total_questions) * 100, 1
                )

            # En çok çıkan konu
            top_topic = (
                self.session.query(TopicFrequency)
                .order_by(TopicFrequency.count.desc())
                .first()
            )
            if top_topic:
                stats.top_topic = top_topic.topic_name
                stats.top_topic_count = top_topic.count

            # Son eklenen soru tarihi
            last_q = (
                self.session.query(Question)
                .order_by(Question.created_at.desc())
                .first()
            )
            if last_q:
                stats.last_question_date = last_q.created_at.strftime("%d.%m.%Y %H:%M")

            # En çok yanlış yapılan konu (en çok soru girilen konu)
            if top_topic:
                stats.most_wrong_topic = top_topic.topic_name

            # Ders bazında soru sayıları
            lesson_counts = (
                self.session.query(Lesson.name, func.count(Question.id))
                .join(Question, Lesson.id == Question.lesson_id)
                .group_by(Lesson.name)
                .all()
            )
            stats.lesson_counts = {name: count for name, count in lesson_counts}

        except Exception as e:
            logger.error(f"Dashboard istatistik hatası: {e}")
        finally:
            self.session.close()

        return stats

    def get_year_distribution(self, lesson_id: Optional[int] = None) -> dict[int, int]:
        """Yıllara göre soru dağılımı."""
        try:
            query = self.session.query(
                Question.year, func.count(Question.id)
            ).filter(Question.year.isnot(None))
            if lesson_id:
                query = query.filter(Question.lesson_id == lesson_id)
            results = query.group_by(Question.year).order_by(Question.year).all()
            return {year: count for year, count in results if year is not None}
        finally:
            self.session.close()

    def get_topic_distribution(self, lesson_id: Optional[int] = None) -> list[TopicStats]:
        """Konulara göre soru dağılımı."""
        total = 0
        topics: list[TopicStats] = []
        try:
            query = self.session.query(TopicFrequency)
            if lesson_id:
                query = query.filter(TopicFrequency.lesson_id == lesson_id)
            results = query.order_by(TopicFrequency.count.desc()).all()

            total = sum(r.count for r in results)
            for r in results:
                lesson_name = r.lesson.name if r.lesson else "?"
                topics.append(
                    TopicStats(
                        topic_name=r.topic_name,
                        count=r.count,
                        lesson_name=lesson_name,
                        percentage=round((r.count / total * 100), 1) if total > 0 else 0,
                    )
                )
        except Exception as e:
            logger.error(f"Konu dağılımı hatası: {e}")
        finally:
            self.session.close()
        return topics

    def get_source_distribution(self) -> dict[str, int]:
        """Kaynaklara göre dağılım."""
        try:
            results = (
                self.session.query(Source.name, func.count(Question.id))
                .join(Question, Source.id == Question.source_id)
                .group_by(Source.name)
                .all()
            )
            return {name: count for name, count in results}
        finally:
            self.session.close()

    def get_answer_distribution(self) -> dict[str, int]:
        """Doğru cevap şık dağılımı."""
        try:
            results = (
                self.session.query(Question.correct_answer, func.count(Question.id))
                .group_by(Question.correct_answer)
                .order_by(Question.correct_answer)
                .all()
            )
            return {ans: count for ans, count in results}
        finally:
            self.session.close()

    def get_similarity_rate_by_year(self) -> dict[int, float]:
        """Yıllara göre tekrar eden soru oranı."""
        try:
            results = (
                self.session.query(
                    Question.year,
                    func.count(Question.id),
                )
                .filter(Question.year.isnot(None))
                .group_by(Question.year)
                .all()
            )
            # Her yıl için benzerlik oranını hesapla
            rates: dict[int, float] = {}
            for year, count in results:
                # O yıla ait sorulardan kaçının benzerlik kaydı var
                similar_count = (
                    self.session.query(func.count(func.distinct(QuestionSimilarity.id)))
                    .filter(
                        (
                            (QuestionSimilarity.question_id_1 == Question.id)
                            | (QuestionSimilarity.question_id_2 == Question.id)
                        ),
                        Question.year == year,
                        QuestionSimilarity.similarity_score >= 0.78,
                    )
                    .scalar()
                ) or 0
                rates[year] = round((similar_count / count * 100), 1) if count > 0 else 0.0
            return rates
        finally:
            self.session.close()
