from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List

import numpy as np
from sentence_transformers import SentenceTransformer

from ..config import get_settings


@lru_cache()
def _get_model() -> SentenceTransformer:
    settings = get_settings()
    model = SentenceTransformer(settings.embedding_model)
    return model


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    model = _get_model()
    embeddings = model.encode(list(texts), normalize_embeddings=True)
    return [vec.tolist() for vec in embeddings]


def embed_single(text: str) -> List[float]:
    return embed_texts([text])[0]
