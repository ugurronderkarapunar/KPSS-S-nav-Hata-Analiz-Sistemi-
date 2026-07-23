"""
Embedding motoru.
Sentence-transformers kullanarak metinleri vektörlere dönüştürür.
Streamlit cache ile model bir kez yüklenir.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import numpy as np

from config.settings import EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_FALLBACK
from utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingEngine:
    """
    Metin embedding motoru.
    Singleton olarak kullanılması önerilir (model yükleme maliyetli).
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or EMBEDDING_MODEL_NAME
        self._model = None
        self._dimension: int = 0
        self._load_model()

    def _load_model(self) -> None:
        """Modeli yükler, hata durumunda fallback dener."""
        from sentence_transformers import SentenceTransformer

        models_to_try = [self.model_name, EMBEDDING_MODEL_FALLBACK]
        last_error = None

        for model_name in models_to_try:
            try:
                logger.info(f"Embedding model yükleniyor: {model_name}")
                start = time.time()
                self._model = SentenceTransformer(model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                elapsed = time.time() - start
                logger.info(
                    f"Model yüklendi: {model_name} (dim={self._dimension}, süre={elapsed:.1f}s)"
                )
                self.model_name = model_name
                return
            except Exception as e:
                last_error = e
                logger.warning(f"Model yüklenemedi ({model_name}): {e}")

        raise RuntimeError(
            f"Hiçbir embedding model yüklenemedi. Son hata: {last_error}"
        )

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(
        self,
        text: str,
        normalize: bool = True,
    ) -> Optional[list[float]]:
        """
        Tek bir metni vektöre dönüştürür.
        Boş metin için None döner.
        """
        if not text or not text.strip():
            return None
        if self._model is None:
            self._load_model()
        try:
            embedding = self._model.encode(
                text.strip(),
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding hesaplama hatası: {e}")
            return None

    def encode_batch(
        self,
        texts: list[str],
        normalize: bool = True,
    ) -> list[Optional[list[float]]]:
        """Birden çok metni toplu olarak vektörleştirir."""
        if not texts:
            return []
        if self._model is None:
            self._load_model()
        try:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            )
            return [emb.tolist() if emb is not None else None for emb in embeddings]
        except Exception as e:
            logger.error(f"Batch embedding hatası: {e}")
            return [None] * len(texts)

    @staticmethod
    def cosine_similarity(
        vec1: list[float],
        vec2: list[float],
    ) -> float:
        """İki vektör arasındaki kosinüs benzerliğini hesaplar."""
        if not vec1 or not vec2:
            return 0.0
        a = np.array(vec1)
        b = np.array(vec2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def embedding_to_json(embedding: Optional[list[float]]) -> Optional[str]:
        """Embedding vektörünü JSON string'e dönüştürür."""
        if embedding is None:
            return None
        return json.dumps(embedding)

    @staticmethod
    def json_to_embedding(json_str: Optional[str]) -> Optional[list[float]]:
        """JSON string'den embedding vektörü çıkarır."""
        if json_str is None:
            return None
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return None
