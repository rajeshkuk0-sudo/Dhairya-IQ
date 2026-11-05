import json
import pathlib
import re
from datetime import datetime, timezone

from src.common.ids import query_id
from src.config.schema import AppConfig
from src.embedding.encoder import encode
from src.tracing.trace_store import redact
from src.vectorstore.chroma_store import ChromaStore

from .models import NOT_FOUND_MESSAGE, RetrievalResult

_FACT_TERMS = (
    "expense ratio",
    "exit load",
    "minimum sip",
    "lock-in",
    "lock in",
    "riskometer",
    "benchmark",
    "fund size",
)
_QUERY_FACT_HINTS = (
    "expense",
    "exit load",
    "sip",
    "lock",
    "risk",
    "benchmark",
    "minimum",
    "nav",
    "aum",
)


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3}


def _scheme_bonus(query: str, scheme: str) -> float:
    if not scheme:
        return 0.0
    return min(0.02 * len(_tokens(query) & _tokens(scheme)), 0.06)


def rerank(query: str, hits: list[dict]) -> list[dict]:
    """Small factual boost: official Key Facts blocks beat look-alike tables."""
    q = query.lower()
    asks_fact = any(h in q for h in _QUERY_FACT_HINTS)
    out = []

    for h in hits:
        m = h.get("metadata") or {}
        text = (h.get("text") or "").lower()
        section = (m.get("section_title") or "").lower()

        bonus = 0.0
        if "key facts" in section or "key facts" in text[:200]:
            bonus += 0.05
            if any(t in text for t in _FACT_TERMS):
                bonus += 0.03
        if asks_fact and any(t in text for t in _FACT_TERMS):
            bonus += 0.02
        bonus += _scheme_bonus(q, m.get("scheme") or "")

        item = dict(h)
        item["rerank_score"] = h.get("score", 0.0) + bonus
        out.append(item)

    return sorted(out, key=lambda h: h["rerank_score"], reverse=True)


class Retriever:
    def __init__(self, cfg: AppConfig, store=None):
        self.cfg = cfg
        self.store = store or ChromaStore(cfg)

    def search(self, query: str, top_k: int | None = None, scheme: str | None = None) -> list[dict]:
        if not query.strip():
            return []
        vec = encode([query], self.cfg)[0]
        k = top_k or self.cfg.retrieval.top_k
        where = {"scheme": scheme} if scheme else None
        return self.store.query(vec, k, where)

    def retrieve(
        self, query: str, top_k: int | None = None, scheme: str | None = None
    ) -> RetrievalResult:
        qid = query_id(query)
        clean = redact(query)
        hits = rerank(clean, self.search(clean, top_k=top_k, scheme=scheme))
        result = RetrievalResult(
            query=clean,
            query_id=qid,
            hits=hits,
            message="" if hits else NOT_FOUND_MESSAGE,
        )
        self._write_trace(qid, clean, hits, top_k or self.cfg.retrieval.top_k, scheme)
        return result

    def _write_trace(
        self,
        qid: str,
        query: str,
        hits: list[dict],
        top_k: int,
        scheme: str | None,
    ) -> pathlib.Path:
        out = pathlib.Path(self.cfg.paths.retrieval)
        out.mkdir(parents=True, exist_ok=True)
        payload = {
            "query_id": qid,
            "query": query,
            "collection": self.cfg.vector_db.collection,
            "model": self.cfg.embedding.model,
            "top_k": top_k,
            "filters": {"scheme": scheme} if scheme else {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "empty": not hits,
            "results": [self._trace_hit(h) for h in hits],
        }
        p = out / f"{qid}.json"
        p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    @staticmethod
    def _trace_hit(hit: dict) -> dict:
        m = hit.get("metadata") or {}
        return {
            "chunk_id": hit["chunk_id"],
            "score": round(hit.get("score", 0.0), 6),
            "rerank_score": round(hit.get("rerank_score", hit.get("score", 0.0)), 6),
            "url": m.get("url", ""),
            "scheme": m.get("scheme", ""),
            "page_type": m.get("page_type", ""),
            "section_title": m.get("section_title", ""),
        }
