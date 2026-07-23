"""
Benzerlik analiz motoru.
Yeni eklenen soruyu tüm mevcut sorularla karşılaştırır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from database.repository import (
    QuestionRepository,
    OptionRepository,
    SimilarityRepository,
    OptionCrossMatchRepository,
)
from embeddings.embedding_engine import EmbeddingEngine
from config.settings import SIMILARITY_HIGH, SIMILARITY_MEDIUM, SIMILARITY_LOW
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SimilarityResult:
    """Benzerlik analizi sonucu."""
    question_id: int
    similar_question_id: int
    score: float
    similar_question_text: str
    similar_question_year: Optional[int]
    similar_question_source: str
    similar_question_lesson: str
    level: str  # HIGH, MEDIUM, LOW

    @property
    def percentage(self) -> int:
        return int(self.score * 100)

    @property
    def level_label(self) -> str:
        labels = {"HIGH": "🟢 Çok Benzer", "MEDIUM": "🟡 Benzer", "LOW": "🟠 Az Benzer"}
        return labels.get(self.level, "⚪")


@dataclass
class CrossMatchResult:
    """Yanlış şık - doğru cevap eşleşme sonucu."""
    option_letter: str
    option_text: str
    matched_question_id: int
    matched_question_text: str
    matched_question_year: Optional[int]
    matched_question_source: str
    similarity_score: float

    @property
    def percentage(self) -> int:
        return int(self.similarity_score * 100)


@dataclass
class FullAnalysisResult:
    """Tam analiz sonucu."""
    similar_questions: list[SimilarityResult] = field(default_factory=list)
    cross_matches: list[CrossMatchResult] = field(default_factory=list)
    topic_frequencies: list[tuple[str, int]] = field(default_factory=list)


class SimilarityAnalyzer:
    """
    Benzerlik analizi yapan ana sınıf.
    Yeni soru eklendiğinde çağrılır.
    """

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        question_repo: QuestionRepository,
        option_repo: OptionRepository,
        similarity_repo: SimilarityRepository,
        cross_match_repo: OptionCrossMatchRepository,
    ):
        self.embedding_engine = embedding_engine
        self.question_repo = question_repo
        self.option_repo = option_repo
        self.similarity_repo = similarity_repo
        self.cross_match_repo = cross_match_repo

    def analyze_new_question(self, question_id: int) -> FullAnalysisResult:
        """
        Yeni eklenen soru için tam analiz yapar.
        1. Benzer soruları bulur
        2. Yanlış şıkların başka sorularda doğru cevap olup olmadığını kontrol eder
        """
        result = FullAnalysisResult()
        question = self.question_repo.get_by_id(question_id)
        if not question or not question.question_embedding:
            logger.warning(f"Soru {question_id} için embedding bulunamadı, analiz atlanıyor.")
            return result

        # Embedding'i al
        q_embedding = EmbeddingEngine.json_to_embedding(question.question_embedding)
        if not q_embedding:
            return result

        # 1. Benzer soru analizi
        result.similar_questions = self._find_similar_questions(
            question_id, q_embedding
        )

        # 2. Yanlış şık - doğru cevap eşleşme analizi
        result.cross_matches = self._find_cross_matches(question)

        return result

    def _find_similar_questions(
        self,
        question_id: int,
        q_embedding: list[float],
    ) -> list[SimilarityResult]:
        """Benzer soruları bulur ve similarity tablosuna kaydeder."""
        similar_results: list[SimilarityResult] = []
        all_questions = self.question_repo.get_all_with_embeddings(exclude_id=question_id)

        for other_q in all_questions:
            other_embedding = EmbeddingEngine.json_to_embedding(other_q.question_embedding)
            if not other_embedding:
                continue

            score = EmbeddingEngine.cosine_similarity(q_embedding, other_embedding)

            # Eşik değerleri kontrol et
            level = None
            if score >= SIMILARITY_HIGH:
                level = "HIGH"
            elif score >= SIMILARITY_MEDIUM:
                level = "MEDIUM"
            elif score >= SIMILARITY_LOW:
                level = "LOW"

            if level:
                # Similarity tablosuna kaydet
                self.similarity_repo.save_similarity(question_id, other_q.id, score)

                similar_results.append(
                    SimilarityResult(
                        question_id=question_id,
                        similar_question_id=other_q.id,
                        score=score,
                        similar_question_text=other_q.question_text,
                        similar_question_year=other_q.year,
                        similar_question_source=other_q.source.name if other_q.source else "?",
                        similar_question_lesson=other_q.lesson.name if other_q.lesson else "?",
                        level=level,
                    )
                )

        # Skora göre sırala
        similar_results.sort(key=lambda x: x.score, reverse=True)
        return similar_results

    def _find_cross_matches(self, question) -> list[CrossMatchResult]:
        """
        Yanlış şıkların başka sorularda doğru cevap olma durumunu analiz eder.
        """
        cross_results: list[CrossMatchResult] = []
        correct_letter = question.correct_answer.upper()

        # Tüm şıkları al
        options = self.option_repo.get_by_question(question.id)

        # Yanlış şıkları filtrele
        wrong_options = [opt for opt in options if opt.option_letter != correct_letter]

        if not wrong_options:
            return cross_results

        # Embedding'i olan tüm seçenekleri al
        all_options = self.option_repo.get_all_with_embeddings()

        for wrong_opt in wrong_options:
            wrong_embedding = EmbeddingEngine.json_to_embedding(wrong_opt.option_embedding)
            if not wrong_embedding:
                continue

            for other_opt in all_options:
                # Aynı sorunun şıklarıyla karşılaştırma
                if other_opt.question_id == question.id:
                    continue

                # Sadece diğer sorunun DOĞRU CEVABI olan şıkları kontrol et
                if other_opt.question.correct_answer != other_opt.option_letter:
                    continue

                other_embedding = EmbeddingEngine.json_to_embedding(other_opt.option_embedding)
                if not other_embedding:
                    continue

                score = EmbeddingEngine.cosine_similarity(wrong_embedding, other_embedding)

                if score >= SIMILARITY_MEDIUM:
                    # Cross match tablosuna kaydet
                    self.cross_match_repo.save_match(
                        source_option_id=wrong_opt.id,
                        matched_question_id=other_opt.question_id,
                        similarity_score=score,
                    )

                    cross_results.append(
                        CrossMatchResult(
                            option_letter=wrong_opt.option_letter,
                            option_text=wrong_opt.option_text,
                            matched_question_id=other_opt.question_id,
                            matched_question_text=other_opt.question.question_text,
                            matched_question_year=other_opt.question.year,
                            matched_question_source=other_opt.question.source.name
                            if other_opt.question.source else "?",
                            similarity_score=score,
                        )
                    )

        # Skora göre sırala
        cross_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return cross_results

    def find_similar_to_text(
        self,
        text: str,
        threshold: float = SIMILARITY_MEDIUM,
        limit: int = 10,
    ) -> list[SimilarityResult]:
        """
        Harici metne benzer soruları bulur (arama için).
        """
        text_embedding = self.embedding_engine.encode(text)
        if not text_embedding:
            return []

        results: list[SimilarityResult] = []
        all_questions = self.question_repo.get_all_with_embeddings()

        for q in all_questions:
            q_embedding = EmbeddingEngine.json_to_embedding(q.question_embedding)
            if not q_embedding:
                continue

            score = EmbeddingEngine.cosine_similarity(text_embedding, q_embedding)
            if score >= threshold:
                level = (
                    "HIGH" if score >= SIMILARITY_HIGH
                    else "MEDIUM" if score >= SIMILARITY_MEDIUM
                    else "LOW"
                )
                results.append(
                    SimilarityResult(
                        question_id=0,
                        similar_question_id=q.id,
                        score=score,
                        similar_question_text=q.question_text,
                        similar_question_year=q.year,
                        similar_question_source=q.source.name if q.source else "?",
                        similar_question_lesson=q.lesson.name if q.lesson else "?",
                        level=level,
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
