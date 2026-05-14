from __future__ import annotations

import os
from dataclasses import dataclass

import faiss
import numpy as np

from app.settings import settings


@dataclass(frozen=True)
class FaissPaths:
    index_path: str


def _paths(kind: str, model: str) -> FaissPaths:
    safe_model = model.replace("/", "_").replace(":", "_")
    base = os.path.join(settings.faiss_dir, safe_model)
    os.makedirs(base, exist_ok=True)
    return FaissPaths(index_path=os.path.join(base, f"{kind}.index"))


def _normalize(v: np.ndarray) -> np.ndarray:
    # cosine similarity via inner product on normalized vectors
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms


class FaissIndex:
    def __init__(self, kind: str, dims: int, model: str):
        self.kind = kind
        self.dims = dims
        self.model = model
        self.paths = _paths(kind=kind, model=model)
        self.index = self._load_or_create()

    def _load_or_create(self) -> faiss.Index:
        if os.path.exists(self.paths.index_path):
            return faiss.read_index(self.paths.index_path)
        return faiss.IndexFlatIP(self.dims)

    def persist(self) -> None:
        faiss.write_index(self.index, self.paths.index_path)

    def add(self, vectors: np.ndarray) -> list[int]:
        vectors = vectors.astype("float32")
        vectors = _normalize(vectors)
        start = self.index.ntotal
        self.index.add(vectors)
        self.persist()
        return list(range(start, start + vectors.shape[0]))

    def search(self, query_vecs: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        query_vecs = query_vecs.astype("float32")
        query_vecs = _normalize(query_vecs)
        scores, ids = self.index.search(query_vecs, k)
        return scores, ids

