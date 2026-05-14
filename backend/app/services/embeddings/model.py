from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.settings import settings


@lru_cache(maxsize=2)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embeddings_model)

