"""
Soru iş mantığı servisi.
Soru ekleme, güncelleme, silme işlemlerini yönetir.
Embedding hesaplama ve analiz tetiklemeyi de içerir.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from database.repository import (
    QuestionRepository,
    OptionRepository,
    SimilarityRepository,
    OptionCrossMatchRepository,
    TopicFrequencyRepository,
    LessonRepository,
    SourceRepository,
)
from embeddings.embedding_engine import EmbeddingEngine
from analysis.similarity import SimilarityAnalyzer, FullAnalysisResult
from utils.logger import get_logger

logger = get_logger(__name__)


class QuestionService:
    """
    Soru CRUD ve analiz servisi.
    Veritabanı oturumunu dışarıdan alır (dependency injection).
    """

    def __init__(
        self,
        session: Session,
        embedding_engine: EmbeddingEngine,
    ):
        self.session = session
        self.embedding_engine = embedding_engine
        self.question_repo = QuestionRepository(session)
        self.option_repo = OptionRepository(session)
        self.similarity_repo = SimilarityRepository(session)
        self.cross_match_repo = OptionCrossMatchRepository(session)
        self.topic_freq_repo = TopicFrequencyRepository(session)
        self.lesson_repo = LessonRepository(session)
        self.source_repo = SourceRepository(session)

        self.analyzer = SimilarityAnalyzer(
            embedding_engine=embedding_engine,
            question_repo=self.question_repo,
            option_repo=self.option_repo,
            similarity_repo=self.similarity_repo,
            cross_match_repo=self.cross_match_repo,
        )

    def add_question(
        self,
        lesson_id: int,
        source_id: int,
        question_text: str,
        correct_answer: str,
        year: Optional[int],
        options: list[dict],
    ) -> tuple[Optional[int], FullAnalysisResult]:
        """
        Yeni soru ekler.
        Her şık için embedding hesaplar.
        Konu notlarını topic_frequencies tablosuna işler.
        Benzerlik analizini çalıştırır.

        Args:
            lesson_id: Ders ID
            source_id: Kaynak ID
            question_text: Soru metni
            correct_answer: Doğru cevap harfi (A-E)
            year: Yıl (opsiyonel)
            options: Şık listesi, her biri:
                {"letter": "A", "text": "...", "topic_note": "..."}

        Returns:
            (question_id, FullAnalysisResult) veya (None, ...)
        """
        try:
            # Soru embedding'i hesapla
            question_embedding = self.embedding_engine.encode(question_text)

            # Soruyu oluştur
            question = self.question_repo.create(
                lesson_id=lesson_id,
                source_id=source_id,
                question_text=question_text,
                correct_answer=correct_answer.upper(),
                year=year,
                question_embedding=question_embedding,
            )

            # Şıkları ekle ve embedding hesapla
            for opt in options:
                option_embedding = self.embedding_engine.encode(opt["text"])
                self.option_repo.create(
                    question_id=question.id,
                    option_letter=opt["letter"].upper(),
                    option_text=opt["text"],
                    topic_note=opt.get("topic_note", ""),
                    option_embedding=option_embedding,
                )

                # Konu notu varsa topic_frequency güncelle
                topic_note = opt.get("topic_note", "").strip()
                if topic_note:
                    self.topic_freq_repo.upsert(
                        lesson_id=lesson_id,
                        topic_name=topic_note,
                    )

            self.session.commit()

            # Benzerlik analizi yap
            analysis_result = self.analyzer.analyze_new_question(question.id)
            self.session.commit()

            logger.info(
                f"Soru eklendi: ID={question.id}, ders={lesson_id}, "
                f"benzer={len(analysis_result.similar_questions)}, "
                f"cross_match={len(analysis_result.cross_matches)}"
            )

            return question.id, analysis_result

        except Exception as e:
            self.session.rollback()
            logger.exception(f"Soru ekleme hatası: {e}")
            raise

    def update_question(
        self,
        question_id: int,
        question_text: Optional[str] = None,
        correct_answer: Optional[str] = None,
        year: Optional[int] = None,
        options: Optional[list[dict]] = None,
    ) -> Optional[int]:
        """Soruyu günceller."""
        try:
            question = self.question_repo.get_by_id(question_id)
            if not question:
                return None

            # Embedding yeniden hesapla (soru metni değiştiyse)
            if question_text is not None:
                new_embedding = self.embedding_engine.encode(question_text)
                self.question_repo.update(
                    question_id=question_id,
                    question_text=question_text,
                    correct_answer=correct_answer,
                    year=year,
                    question_embedding=new_embedding,
                )
            else:
                self.question_repo.update(
                    question_id=question_id,
                    correct_answer=correct_answer,
                    year=year,
                )

            # Şıkları güncelle (opsiyonel)
            if options is not None:
                self.option_repo.delete_by_question(question_id)
                for opt in options:
                    option_embedding = self.embedding_engine.encode(opt["text"])
                    self.option_repo.create(
                        question_id=question_id,
                        option_letter=opt["letter"].upper(),
                        option_text=opt["text"],
                        topic_note=opt.get("topic_note", ""),
                        option_embedding=option_embedding,
                    )

            self.session.commit()
            logger.info(f"Soru güncellendi: ID={question_id}")
            return question_id

        except Exception as e:
            self.session.rollback()
            logger.exception(f"Soru güncelleme hatası: {e}")
            raise

    def delete_question(self, question_id: int) -> bool:
        """Soruyu ve ilişkili tüm kayıtları siler."""
        try:
            result = self.question_repo.delete(question_id)
            if result:
                self.session.commit()
                logger.info(f"Soru silindi: ID={question_id}")
            return result
        except Exception as e:
            self.session.rollback()
            logger.exception(f"Soru silme hatası: {e}")
            raise

    def get_similar_questions(
        self, question_id: int, threshold: float = 0.75
    ) -> list:
        """Bir soruya benzer soruları getirir."""
        return self.similarity_repo.get_similar_questions(question_id, threshold)

    def get_cross_matches(self, question_id: int) -> list:
        """Bir sorudaki yanlış şıkların eşleşmelerini getirir."""
        options = self.option_repo.get_by_question(question_id)
        all_matches = []
        for opt in options:
            if opt.option_letter != self.question_repo.get_by_id(question_id).correct_answer:
                matches = self.cross_match_repo.get_matches_for_option(opt.id)
                all_matches.extend(matches)
        return all_matches
