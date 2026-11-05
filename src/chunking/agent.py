from src.common.ids import chunk_id
from src.config.schema import AppConfig

from . import strategies as S
from .models import Chunk

FACT_HEADINGS = [
    "expense ratio",
    "exit load",
    "minimum sip",
    "min. for sip",
    "lock-in",
    "riskometer",
    "benchmark",
]


def _f(doc, name: str):
    return doc.get(name) if isinstance(doc, dict) else getattr(doc, name)


def decide_strategy(doc, cfg: AppConfig) -> dict:
    """Pick a chunking strategy from the document's structure."""
    if cfg.chunking.strategy != "auto":
        return {"strategy": cfg.chunking.strategy, "rationale": "config override"}

    text = _f(doc, "text") or ""
    low = text.lower()
    table_lines = sum(1 for line in text.splitlines() if line.count("|") >= 2)
    headings = sum(1 for line in text.splitlines() if any(k in line.lower() for k in FACT_HEADINGS))

    if "key facts" in low:
        return {"strategy": "section", "rationale": "structured key-facts block present"}
    if table_lines >= 5:
        return {"strategy": "table", "rationale": f"{table_lines} table rows detected"}
    if headings >= 2:
        return {"strategy": "section", "rationale": f"{headings} fact headings detected"}
    return {"strategy": "recursive", "rationale": "narrative text without tables/headings"}


def chunk_document(doc, cfg: AppConfig) -> tuple[list[Chunk], dict]:
    decision = decide_strategy(doc, cfg)
    splitter = {
        "section": S.section_split,
        "recursive": S.recursive_split,
        "table": S.table_split,
    }[decision["strategy"]]

    pairs = splitter(
        _f(doc, "text"),
        cfg.chunking.chunk_size,
        cfg.chunking.chunk_overlap,
    )

    chunks: list[Chunk] = []
    seen: set[str] = set()
    order = 0

    for head, txt in pairs:
        txt = (txt or "").strip()
        if len(txt) < 30 or txt in seen:
            continue
        seen.add(txt)
        chunks.append(
            Chunk(
                chunk_id=chunk_id(_f(doc, "doc_id"), order),
                doc_id=_f(doc, "doc_id"),
                url=_f(doc, "url"),
                scheme=_f(doc, "scheme"),
                page_type=_f(doc, "page_type"),
                section_title=head,
                text=txt,
                token_count=max(1, len(txt) // 4),
                strategy=decision["strategy"],
                order=order,
                fetched_at=_f(doc, "fetched_at"),
            )
        )
        order += 1

    decision["n_chunks"] = len(chunks)
    decision["params"] = {
        "chunk_size": cfg.chunking.chunk_size,
        "chunk_overlap": cfg.chunking.chunk_overlap,
    }
    return chunks, decision
