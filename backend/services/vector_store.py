from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dim: int, index_path: Path):
        self.dim = dim
        self.index_path = index_path
        if index_path.exists():
            self.index = faiss.read_index(str(index_path))
        else:
            self.index = faiss.IndexFlatIP(dim)

    def add(self, vectors: List[List[float]]) -> None:
        arr = np.array(vectors).astype("float32")
        if arr.shape[1] != self.dim:
            raise ValueError("Vector dimension mismatch")
        self.index.add(arr)
        self._persist()

    def search(self, query: List[float], k: int = 4) -> List[Tuple[int, float]]:
        query_arr = np.array([query]).astype("float32")
        scores, indices = self.index.search(query_arr, k)
        result = []
        for idx, score in zip(indices[0], scores[0]):
            if idx == -1:
                continue
            result.append((int(idx), float(score)))
        return result

    def _persist(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
