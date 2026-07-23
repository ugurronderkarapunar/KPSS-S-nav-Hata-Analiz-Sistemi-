"""
SQLAlchemy ORM modelleri.
Veritabanı şemasının tek kaynağı burasıdır.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Tüm modellerin temel sınıfı."""
    pass


class Lesson(Base):
    """Ders tablosu. Örn: Tarih, Vatandaşlık."""
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # İlişkiler
    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="lesson", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, name='{self.name}')>"


class Source(Base):
    """Kaynak tablosu. Örn: KPSS, ÖSYM, Deneme, Soru Bankası."""
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    requires_year: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    questions: Mapped[list["Question"]] = relationship(
        "Question", back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}')>"


class Question(Base):
    """Soru tablosu."""
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(
        String(1), nullable=False
    )  # A, B, C, D, E
    question_embedding: Mapped[Optional[bytes]] = mapped_column(
        Text, nullable=True
    )  # JSON string olarak embedding vektörü
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # İlişkiler
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="questions")
    source: Mapped["Source"] = relationship("Source", back_populates="questions")
    options: Mapped[list["Option"]] = relationship(
        "Option", back_populates="question", cascade="all, delete-orphan",
        order_by="Option.option_letter"
    )

    # Benzerlik ilişkileri
    similarities_as_source: Mapped[list["QuestionSimilarity"]] = relationship(
        "QuestionSimilarity",
        foreign_keys="QuestionSimilarity.question_id_1",
        back_populates="question_1",
        cascade="all, delete-orphan",
    )
    similarities_as_target: Mapped[list["QuestionSimilarity"]] = relationship(
        "QuestionSimilarity",
        foreign_keys="QuestionSimilarity.question_id_2",
        back_populates="question_2",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_question_lesson", "lesson_id"),
        Index("idx_question_source", "source_id"),
        Index("idx_question_year", "year"),
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, lesson={self.lesson_id}, year={self.year})>"


class Option(Base):
    """Şık tablosu. Her şık için konu notu tutulur."""
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_letter: Mapped[str] = mapped_column(
        String(1), nullable=False
    )  # A, B, C, D, E
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    topic_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    option_embedding: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON string olarak embedding
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # İlişkiler
    question: Mapped["Question"] = relationship("Question", back_populates="options")

    __table_args__ = (
        UniqueConstraint("question_id", "option_letter", name="uq_question_option"),
        Index("idx_option_question", "question_id"),
    )

    def __repr__(self) -> str:
        return f"<Option(id={self.id}, q_id={self.question_id}, letter='{self.option_letter}')>"


class QuestionSimilarity(Base):
    """Sorular arası benzerlik önbelleği."""
    __tablename__ = "question_similarities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id_1: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id_2: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    question_1: Mapped["Question"] = relationship(
        "Question", foreign_keys=[question_id_1], back_populates="similarities_as_source"
    )
    question_2: Mapped["Question"] = relationship(
        "Question", foreign_keys=[question_id_2], back_populates="similarities_as_target"
    )

    __table_args__ = (
        UniqueConstraint("question_id_1", "question_id_2", name="uq_similarity_pair"),
        Index("idx_similarity_q1", "question_id_1"),
        Index("idx_similarity_q2", "question_id_2"),
    )

    def __repr__(self) -> str:
        return f"<QuestionSimilarity(q1={self.question_id_1}, q2={self.question_id_2}, score={self.similarity_score:.3f})>"


class OptionCrossMatch(Base):
    """
    Yanlış şıkların başka sorularda doğru cevap olma durumunu izler.
    Örn: Bu sorudaki B şıkkı (yanlış), 2017 KPSS'de doğru cevap olarak geçmiş.
    """
    __tablename__ = "option_cross_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_option_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("options.id", ondelete="CASCADE"), nullable=False
    )
    matched_question_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_type: Mapped[str] = mapped_column(
        String(50), default="OPTION_TO_CORRECT"
    )  # Eşleşme türü
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_option: Mapped["Option"] = relationship("Option", foreign_keys=[source_option_id])
    matched_question: Mapped["Question"] = relationship(
        "Question", foreign_keys=[matched_question_id]
    )

    __table_args__ = (
        UniqueConstraint(
            "source_option_id", "matched_question_id", name="uq_cross_match"
        ),
    )

    def __repr__(self) -> str:
        return f"<OptionCrossMatch(opt={self.source_option_id} -> q={self.matched_question_id})>"


class TopicFrequency(Base):
    """Konu tekrar sıklığı önbelleği (denormalize, performans için)."""
    __tablename__ = "topic_frequencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_name: Mapped[str] = mapped_column(String(300), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lesson: Mapped["Lesson"] = relationship("Lesson")

    __table_args__ = (
        UniqueConstraint("lesson_id", "topic_name", name="uq_topic_lesson"),
    )

    def __repr__(self) -> str:
        return f"<TopicFrequency(topic='{self.topic_name}', count={self.count})>"
