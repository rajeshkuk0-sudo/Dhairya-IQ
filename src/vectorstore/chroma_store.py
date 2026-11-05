import chromadb
from chromadb.config import Settings

from src.config.schema import AppConfig


class ChromaStore:
    """Persistent Chroma adapter: chunk metadata in, similarity hits out."""

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.client = chromadb.PersistentClient(
            path=cfg.vector_db.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.col = self.client.get_or_create_collection(
            name=cfg.vector_db.collection,
            configuration={"hnsw": {"space": cfg.vector_db.distance}},
            metadata={"model": cfg.embedding.model},
        )

    def upsert(self, chunks: list[dict], vectors) -> None:
        self.col.upsert(
            ids=[c["chunk_id"] for c in chunks],
            embeddings=vectors.tolist(),
            documents=[c["text"] for c in chunks],
            metadatas=[
                {
                    "doc_id": c["doc_id"],
                    "url": c.get("url") or "",
                    "scheme": c.get("scheme") or "",
                    "page_type": c.get("page_type") or "",
                    "section_title": c.get("section_title") or "",
                    "strategy": c.get("strategy") or "",
                    "order": int(c.get("order", 0)),
                    "token_count": int(c.get("token_count", 0)),
                    "fetched_at": c.get("fetched_at") or "",
                }
                for c in chunks
            ],
        )

    def query(self, embedding, top_k: int, where: dict | None = None) -> list[dict]:
        n = self.col.count()
        if n == 0 or top_k <= 0:
            return []
        kwargs = {
            "query_embeddings": [
                embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
            ],
            "n_results": min(top_k, n),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        try:
            res = self.col.query(**kwargs)
        except Exception:
            return []
        ids = (res.get("ids") or [[]])[0] or []
        docs = (res.get("documents") or [[]])[0] or []
        metas = (res.get("metadatas") or [[]])[0] or []
        dists = (res.get("distances") or [[]])[0] or []
        return [
            {
                "chunk_id": ids[i],
                "text": docs[i],
                "metadata": metas[i] or {},
                "score": 1 - dists[i],
            }
            for i in range(len(ids))
        ]

    def count(self) -> int:
        return self.col.count()

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.cfg.vector_db.collection)
        except Exception:
            pass
        self.__init__(self.cfg)
