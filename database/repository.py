"""
Repository Pattern ile veri erişim katmanı.
Tüm CRUD işlemleri bu katman üzerinden yapılır.
İleride ORM değişirse yalnızca bu katman etkilenir.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, and_, or_, desc, asc, text
from sqlalchemy.orm import Session, joinedload

from database.models import (
    Lesson,
    Source,
    Question,
    Option,
    QuestionSimilarity,
    OptionCrossMatch,
    TopicFrequency,
)
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseRepository:
    """Temel repository sınıfı."""
    def __init__(self, session: Session):
        self.session = session


class LessonRepository(BaseRepository):
    """Ders CRUD işlemleri."""

    def get_all(self) -> list[Lesson]:
        return self.session.query(Lesson).order_by(Lesson.name).all()

    def get_by_id(self, lesson_id: int) -> Optional[Lesson]:
        return self.session.query(Lesson).filter(Lesson.id == lesson_id).first()

    def get_by_code(self, code: str) -> Optional[Lesson]:
        return self.session.query(Lesson).filter(Lesson.code == code).first()

    def create(self, name: str, code: str) -> Lesson:
        lesson = Lesson(name=name, code=code)
        self.session.add(lesson)
        self.session.flush()
        logger.info(f"Ders eklendi: {name} ({code})")
        return lesson

    def get_or_create(self, name: str, code: str) -> Lesson:
        lesson = self.get_by_code(code)
        if not lesson:
            lesson = self.create(name=name, code=code)
        return lesson

    def seed_defaults(self) -> None:
        """Varsayılan dersleri ekler."""
        defaults = [
            {"name": "Tarih", "code": "TARIH"},
            {"name": "Vatandaşlık", "code": "VATANDASLIK"},
        ]
        for d in defaults:
            if not self.get_by_code(d["code"]):
                self.create(**d)


class SourceRepository(BaseRepository):
    """Kaynak CRUD işlemleri."""

    def get_all(self) -> list[Source]:
        return self.session.query(Source).order_by(Source.name).all()

    def get_by_id(self, source_id: int) -> Optional[Source]:
        return self.session.query(Source).filter(Source.id == source_id).first()

    def get_by_name(self, name: str) -> Optional[Source]:
        return self.session.query(Source).filter(Source.name == name).first()

    def create(self, name: str, requires_year: bool = True) -> Source:
        source = Source(name=name, requires_year=requires_year)
        self.session.add(source)
        self.session.flush()
        return source

    def get_or_create(self, name: str, requires_year: bool = True) -> Source:
        source = self.get_by_name(name)
        if not source:
            source = self.create(name=name, requires_year=requires_year)
        return source

    def seed_defaults(self) -> None:
        """Varsayılan kaynak türlerini ekler.
        Yalnızca KPSS, Deneme, Soru Bankası.
        Yıl zorunluluğu sadece KPSS için geçerlidir.
        """
        defaults = {
            "KPSS": True,
            "Deneme": False,
            "Soru Bankası": False,
        }
        for name, requires_year in defaults.items():
            if not self.get_by_name(name):
                self.create(name=name, requires_year=requires_year)


class QuestionRepository(BaseRepository):
    """Soru CRUD ve sorgulama işlemleri."""

    def create(
        self,
        lesson_id: int,
        source_id: int,
        question_text: str,
        correct_answer: str,
        year: Optional[int] = None,
        question_embedding: Optional[list[float]] = None,
    ) -> Question:
        question = Question(
            lesson_id=lesson_id,
            source_id=source_id,
            year=year,
            question_text=question_text,
            correct_answer=correct_answer.upper(),
            question_embedding=json.dumps(question_embedding) if question_embedding else None,
        )
        self.session.add(question)
        self.session.flush()
        return question

    def get_by_id(self, question_id: int) -> Optional[Question]:
        return (
            self.session.query(Question)
            .options(
                joinedload(Question.lesson),
                joinedload(Question.source),
                joinedload(Question.options),
            )
            .filter(Question.id == question_id)
            .first()
        )

    def get_all(
        self,
        lesson_id: Optional[int] = None,
        source_id: Optional[int] = None,
        year: Optional[int] = None,
        search_text: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Question], int]:
        query = self.session.query(Question)
        count_query = self.session.query(func.count(Question.id))

        if lesson_id:
            query = query.filter(Question.lesson_id == lesson_id)
            count_query = count_query.filter(Question.lesson_id == lesson_id)
        if source_id:
            query = query.filter(Question.source_id == source_id)
            count_query = count_query.filter(Question.source_id == source_id)
        if year is not None:
            query = query.filter(Question.year == year)
            count_query = count_query.filter(Question.year == year)
        if search_text:
            search_filter = or_(
                Question.question_text.ilike(f"%{search_text}%"),
                Question.options.any(Option.option_text.ilike(f"%{search_text}%")),
                Question.options.any(Option.topic_note.ilike(f"%{search_text}%")),
            )
            query = query.filter(search_filter)
            count_query = count_query.filter(search_filter)

        total = count_query.scalar() or 0
        questions = (
            query
            .options(
                joinedload(Question.lesson),
                joinedload(Question.source),
                joinedload(Question.options),
            )
            .order_by(desc(Question.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return questions, total

    def update(
        self,
        question_id: int,
        question_text: Optional[str] = None,
        correct_answer: Optional[str] = None,
        year: Optional[int] = None,
        question_embedding: Optional[list[float]] = None,
    ) -> Optional[Question]:
        question = self.get_by_id(question_id)
        if not question:
            return None
        if question_text is not None:
            question.question_text = question_text
        if correct_answer is not None:
            question.correct_answer = correct_answer.upper()
        if year is not None:
            question.year = year
        if question_embedding is not None:
            question.question_embedding = json.dumps(question_embedding)
        question.updated_at = datetime.utcnow()
        self.session.flush()
        return question

    def delete(self, question_id: int) -> bool:
        question = self.session.query(Question).filter(Question.id == question_id).first()
        if not question:
            return False
        self.session.delete(question)
        self.session.flush()
        return True

    def get_all_with_embeddings(self, exclude_id: Optional[int] = None) -> list[Question]:
        """Embedding'i olan tüm soruları döner (benzerlik hesaplaması için)."""
        query = self.session.query(Question).filter(Question.question_embedding.isnot(None))
        if exclude_id:
            query = query.filter(Question.id != exclude_id)
        return query.options(
            joinedload(Question.lesson),
            joinedload(Question.source),
            joinedload(Question.options),
        ).all()

    def get_total_count(self) -> int:
        return self.session.query(func.count(Question.id)).scalar() or 0

    def get_count_by_lesson(self, lesson_id: int) -> int:
        return (
            self.session.query(func.count(Question.id))
            .filter(Question.lesson_id == lesson_id)
            .scalar()
        ) or 0

    def get_year_distribution(self, lesson_id: Optional[int] = None) -> list[tuple]:
        query = self.session.query(
            Question.year, func.count(Question.id)
        ).filter(Question.year.isnot(None))
        if lesson_id:
            query = query.filter(Question.lesson_id == lesson_id)
        return query.group_by(Question.year).order_by(Question.year).all()

    def get_source_distribution(self) -> list[tuple]:
        return (
            self.session.query(Source.name, func.count(Question.id))
            .join(Source, Question.source_id == Source.id)
            .group_by(Source.name)
            .all()
        )

    def get_correct_answer_distribution(self) -> list[tuple]:
        return (
            self.session.query(Question.correct_answer, func.count(Question.id))
            .group_by(Question.correct_answer)
            .order_by(Question.correct_answer)
            .all()
        )


class OptionRepository(BaseRepository):
    """Şık CRUD işlemleri."""

    def create(
        self,
        question_id: int,
        option_letter: str,
        option_text: str,
        topic_note: Optional[str] = None,
        option_embedding: Optional[list[float]] = None,
    ) -> Option:
        option = Option(
            question_id=question_id,
            option_letter=option_letter.upper(),
            option_text=option_text,
            topic_note=topic_note,
            option_embedding=json.dumps(option_embedding) if option_embedding else None,
        )
        self.session.add(option)
        self.session.flush()
        return option

    def get_by_question(self, question_id: int) -> list[Option]:
        return (
            self.session.query(Option)
            .filter(Option.question_id == question_id)
            .order_by(Option.option_letter)
            .all()
        )

    def update(
        self,
        option_id: int,
        option_text: Optional[str] = None,
        topic_note: Optional[str] = None,
    ) -> Optional[Option]:
        option = self.session.query(Option).filter(Option.id == option_id).first()
        if not option:
            return None
        if option_text is not None:
            option.option_text = option_text
        if topic_note is not None:
            option.topic_note = topic_note
        self.session.flush()
        return option

    def delete_by_question(self, question_id: int) -> None:
        self.session.query(Option).filter(Option.question_id == question_id).delete()

    def get_all_with_embeddings(self) -> list[Option]:
        return self.session.query(Option).filter(
            Option.option_embedding.isnot(None)
        ).options(joinedload(Option.question)).all()


class SimilarityRepository(BaseRepository):
    """Benzerlik önbelleği CRUD."""

    def save_similarity(self, q1_id: int, q2_id: int, score: float) -> QuestionSimilarity:
        # Her zaman küçük ID'yi q1 yap
        if q1_id > q2_id:
            q1_id, q2_id = q2_id, q1_id

        existing = (
            self.session.query(QuestionSimilarity)
            .filter(
                QuestionSimilarity.question_id_1 == q1_id,
                QuestionSimilarity.question_id_2 == q2_id,
            )
            .first()
        )
        if existing:
            existing.similarity_score = score
            self.session.flush()
            return existing

        sim = QuestionSimilarity(
            question_id_1=q1_id,
            question_id_2=q2_id,
            similarity_score=score,
        )
        self.session.add(sim)
        self.session.flush()
        return sim

    def get_similar_questions(
        self, question_id: int, threshold: float = 0.75
    ) -> list[tuple[Question, float]]:
        """Bir soruya benzer soruları döner."""
        results = (
            self.session.query(QuestionSimilarity)
            .filter(
                or_(
                    QuestionSimilarity.question_id_1 == question_id,
                    QuestionSimilarity.question_id_2 == question_id,
                ),
                QuestionSimilarity.similarity_score >= threshold,
            )
            .order_by(desc(QuestionSimilarity.similarity_score))
            .all()
        )

        similar_questions: list[tuple[Question, float]] = []
        for sim in results:
            other_id = (
                sim.question_id_2
                if sim.question_id_1 == question_id
                else sim.question_id_1
            )
            other_q = self.session.query(Question).filter(
                Question.id == other_id
            ).options(
                joinedload(Question.lesson),
                joinedload(Question.source),
            ).first()
            if other_q:
                similar_questions.append((other_q, sim.similarity_score))
        return similar_questions

    def get_similarity_between(self, q1_id: int, q2_id: int) -> Optional[float]:
        if q1_id > q2_id:
            q1_id, q2_id = q2_id, q1_id
        sim = (
            self.session.query(QuestionSimilarity)
            .filter(
                QuestionSimilarity.question_id_1 == q1_id,
                QuestionSimilarity.question_id_2 == q2_id,
            )
            .first()
        )
        return sim.similarity_score if sim else None


class OptionCrossMatchRepository(BaseRepository):
    """Yanlış şık - doğru cevap eşleşme CRUD."""

    def save_match(
        self,
        source_option_id: int,
        matched_question_id: int,
        similarity_score: float,
        match_type: str = "OPTION_TO_CORRECT",
    ) -> OptionCrossMatch:
        existing = (
            self.session.query(OptionCrossMatch)
            .filter(
                OptionCrossMatch.source_option_id == source_option_id,
                OptionCrossMatch.matched_question_id == matched_question_id,
            )
            .first()
        )
        if existing:
            existing.similarity_score = similarity_score
            self.session.flush()
            return existing

        match = OptionCrossMatch(
            source_option_id=source_option_id,
            matched_question_id=matched_question_id,
            similarity_score=similarity_score,
            match_type=match_type,
        )
        self.session.add(match)
        self.session.flush()
        return match

    def get_matches_for_option(self, option_id: int) -> list[OptionCrossMatch]:
        return (
            self.session.query(OptionCrossMatch)
            .filter(OptionCrossMatch.source_option_id == option_id)
            .options(
                joinedload(OptionCrossMatch.matched_question).joinedload(Question.lesson),
                joinedload(OptionCrossMatch.matched_question).joinedload(Question.source),
            )
            .order_by(desc(OptionCrossMatch.similarity_score))
            .all()
        )


class TopicFrequencyRepository(BaseRepository):
    """Konu frekans CRUD."""

    def upsert(self, lesson_id: int, topic_name: str) -> TopicFrequency:
        tf = (
            self.session.query(TopicFrequency)
            .filter(
                TopicFrequency.lesson_id == lesson_id,
                TopicFrequency.topic_name == topic_name,
            )
            .first()
        )
        if tf:
            tf.count += 1
            tf.last_seen = datetime.utcnow()
        else:
            tf = TopicFrequency(
                lesson_id=lesson_id,
                topic_name=topic_name,
                count=1,
            )
            self.session.add(tf)
        self.session.flush()
        return tf

    def get_top_topics(
        self, lesson_id: Optional[int] = None, limit: int = 10
    ) -> list[TopicFrequency]:
        query = self.session.query(TopicFrequency)
        if lesson_id:
            query = query.filter(TopicFrequency.lesson_id == lesson_id)
        return query.order_by(desc(TopicFrequency.count)).limit(limit).all()

    def get_all(self, lesson_id: Optional[int] = None) -> list[TopicFrequency]:
        query = self.session.query(TopicFrequency)
        if lesson_id:
            query = query.filter(TopicFrequency.lesson_id == lesson_id)
        return query.order_by(desc(TopicFrequency.count)).all()
