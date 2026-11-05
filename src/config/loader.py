import datetime
import json
import os
import pathlib

import yaml
from dotenv import load_dotenv

from .schema import AppConfig

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.yaml"


def load_config(path: pathlib.Path | str = CONFIG_PATH, require_llm: bool = False) -> AppConfig:
    load_dotenv(ROOT / ".env")
    raw = yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))
    cfg = AppConfig(**raw)

    if require_llm and cfg.llm.provider == "groq" and not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY missing in .env")

    assert_parity(cfg)
    snapshot(cfg)
    return cfg


def assert_parity(cfg: AppConfig) -> None:
    """Ingestion and retrieval must share the embedding model + vector DB."""
    slug = cfg.embedding.model.split("/")[-1].lower().replace("-", "").replace("_", "")
    expected = f"mf_faq_{slug}_{cfg.corpus.version}"
    if cfg.vector_db.collection != expected:
        raise RuntimeError(
            f"Collection '{cfg.vector_db.collection}' does not match embedding "
            f"model/corpus version (expected '{expected}')."
        )


def snapshot(cfg: AppConfig) -> None:
    rid = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    out = ROOT / cfg.paths.runs / rid
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
