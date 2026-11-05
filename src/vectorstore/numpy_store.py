import json
import pathlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX_DIR = ROOT / "data" / "vercel"

_METADATA_FIELDS = (
    "doc_id",
    "url",
    "scheme",
    "page_type",
    "section_title",
    "strategy",
    "order",
    "token_count",
    "fetched_at",
)


class NumpyStore:
    """Read-only cosine store for the small FAQ corpus (no Chroma needed)."""

    def __init__(self, cfg=None, index_dir: str | pathlib.Path | None = None):
        self.dir = pathlib.Path(index_dir) if index_dir else INDEX_DIR
        payload = json.loads((self.dir / "index.json").read_text(encoding="utf-8"))
        self.chunks = payload["chunks"]
        vectors = np.load(self.dir / "vectors.npy").astype(np.float32)
        if len(vectors) != len(self.chunks):
            raise RuntimeError("Vercel index/vectors count mismatch")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        self.vectors = vectors / np.clip(norms, 1e-9, None)

    def query(self, embedding, top_k: int, where: dict | None = None) -> list[dict]:
        if top_k <= 0 or not self.chunks:
            return []
        query = np.asarray(embedding, dtype=np.float32).reshape(-1)
        query = query / max(float(np.linalg.norm(query)), 1e-9)
        scores = self.vectors @ query

        indices = np.arange(len(self.chunks))
        if where:
            keep = np.array(
                [
                    all(chunk.get(key) == value for key, value in where.items())
                    for chunk in self.chunks
                ],
                dtype=bool,
            )
            indices = indices[keep]
            scores = scores[keep]

        if indices.size == 0:
            return []

        order = np.argsort(-scores)[: min(top_k, indices.size)]
        hits = []
        for position in order:
            chunk = self.chunks[int(indices[position])]
            hits.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "metadata": {field: chunk.get(field, "") for field in _METADATA_FIELDS},
                    "score": float(scores[position]),
                }
            )
        return hits

    def count(self) -> int:
        return len(self.chunks)
