import numpy as np
from sentence_transformers import SentenceTransformer

from src.config.schema import AppConfig

_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def get_model(cfg: AppConfig) -> SentenceTransformer:
    key = cfg.embedding.model
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = SentenceTransformer(key, device=cfg.embedding.device)
    return _MODEL_CACHE[key]


def text_for_embedding(chunk: dict) -> str:
    """Prepend source context so short fact chunks are matchable by scheme."""
    label = chunk.get("scheme") or chunk.get("page_type") or ""
    section = chunk.get("section_title") or ""
    prefix = " | ".join(p for p in (label, section) if p)
    return f"{prefix}\n{chunk['text']}" if prefix else chunk["text"]


def encode(texts: list[str], cfg: AppConfig) -> np.ndarray:
    model = get_model(cfg)
    return model.encode(
        texts,
        batch_size=cfg.embedding.batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
