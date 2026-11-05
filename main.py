import json
import logging
import os
import pathlib
import sys
import threading
import types
from functools import lru_cache

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = pathlib.Path(__file__).resolve().parent
if not (ROOT / "config").exists() and (pathlib.Path.cwd() / "config").exists():
    ROOT = pathlib.Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "config" / "vercel.yaml"
if not CONFIG_PATH.exists():
    CONFIG_PATH = ROOT / "config" / "config.yaml"

INDEX_HTML = ROOT / "public" / "index.html"
INDEX_PATH = ROOT / "data" / "vercel" / "index.json"
MODEL_DIR = ROOT / "models" / "minilm-onnx"

DEFAULT_MODEL = "qwen/qwen3.8-27b"
DEFAULT_EXAMPLES = [
    "What is the expense ratio of HDFC Flexi Cap Fund Direct Growth?",
    "What is the mandatory lock-in period for HDFC ELSS Tax Saver Fund?",
    "What is the exit load and minimum SIP for HDFC Mid Cap Fund?",
    "Should I invest in HDFC Large Cap Fund?",
]
SCHEMES = [
    {"label": "HDFC AMC Overview", "prompt": "What is the overview of HDFC Mutual Fund?"},
    {
        "label": "HDFC Large Cap Fund",
        "prompt": "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    },
    {
        "label": "HDFC Flexi Cap Fund",
        "prompt": "What is the expense ratio of HDFC Flexi Cap Fund Direct Growth?",
    },
    {
        "label": "HDFC ELSS Tax Saver",
        "prompt": "What is the lock-in period for HDFC ELSS Tax Saver?",
    },
    {
        "label": "HDFC Mid Cap Fund",
        "prompt": "What is the exit load and minimum SIP for HDFC Mid Cap Fund?",
    },
]
TOPICS = [
    {"label": "Expense Ratios · TER", "prompt": "What is the expense ratio of HDFC Flexi Cap Fund?"},
    {"label": "Exit Load · Redemption", "prompt": "What is the exit load for HDFC Flexi Cap Fund?"},
    {"label": "Minimum SIP · Lumpsum", "prompt": "What is the minimum SIP for HDFC Flexi Cap Fund?"},
    {"label": "ELSS Lock-in · Sec 80C", "prompt": "What is the lock-in period for HDFC ELSS Tax Saver?"},
    {
        "label": "Riskometer · Benchmark",
        "prompt": "What are the riskometer and benchmark for HDFC Flexi Cap Fund?",
    },
    {"label": "Statement Download", "prompt": "How do I download my capital gains statement?"},
]

logger = logging.getLogger("dhairya-iq")
_lock = threading.Lock()
_orchestrator = None


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=512)


class AskResponse(BaseModel):
    query: str
    query_id: str
    answer: str
    citation: str
    last_updated: str
    notice: str
    refused: bool
    mode: str


def _install_shims() -> None:
    from src.embedding import onnx_encoder

    encoder = types.ModuleType("src.embedding.encoder")
    encoder.encode = onnx_encoder.encode
    encoder.text_for_embedding = onnx_encoder.text_for_embedding
    sys.modules["src.embedding.encoder"] = encoder

    chroma = types.ModuleType("src.vectorstore.chroma_store")

    class ChromaStore:
        def __init__(self, cfg=None):
            raise RuntimeError("ChromaStore is unavailable in the Vercel build")

    chroma.ChromaStore = ChromaStore
    sys.modules["src.vectorstore.chroma_store"] = chroma


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        with _lock:
            if _orchestrator is None:
                _install_shims()
                from src.config.loader import load_config
                from src.orchestration.query_orchestrator import QueryOrchestrator
                from src.retrieval.retriever import Retriever
                from src.vectorstore.numpy_store import NumpyStore

                cfg = load_config(CONFIG_PATH)
                retriever = Retriever(cfg, store=NumpyStore(cfg))
                _orchestrator = QueryOrchestrator(cfg, retriever=retriever)
    return _orchestrator


@lru_cache(maxsize=1)
def _index_count() -> int:
    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return int(payload.get("count", 0))
    except (OSError, ValueError, TypeError):
        return 0


@lru_cache(maxsize=1)
def _ui_settings() -> dict:
    try:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        raw = {}
    ui = raw.get("ui") or {}
    examples = ui.get("example_questions") or DEFAULT_EXAMPLES
    return {
        "title": ui.get("title") or "Dhairya-IQ",
        "disclaimer": ui.get("disclaimer") or "Facts-only. No investment advice.",
        "examples": examples,
    }


def _ready() -> bool:
    return (
        INDEX_PATH.exists()
        and (MODEL_DIR / "model.onnx").exists()
        and (MODEL_DIR / "tokenizer.json").exists()
    )


app = FastAPI(title="Dhairya-IQ", version="1.0.0")


@app.get("/api/health")
@app.get("/health")
def health():
    settings = _ui_settings()
    return {
        "status": "ok" if _ready() else "degraded",
        "service": "dhairya-iq",
        "title": settings["title"],
        "embedding": "onnx-all-MiniLM-L6-v2",
        "chunks": _index_count(),
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "orchestrator_ready": _orchestrator is not None,
    }


@app.get("/api/config")
@app.get("/config")
def config():
    settings = _ui_settings()
    return {
        "title": settings["title"],
        "disclaimer": settings["disclaimer"],
        "examples": settings["examples"],
        "schemes": SCHEMES,
        "topics": TOPICS,
    }


@app.post("/api/ask", response_model=AskResponse)
@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = get_orchestrator().ask(query)
    except Exception:
        logger.exception("Ask request failed")
        raise HTTPException(
            status_code=503,
            detail="The assistant is not ready. Please try again shortly.",
        )

    return AskResponse(
        query=result.get("query") or query,
        query_id=result.get("query_id") or "",
        answer=result.get("answer") or "",
        citation=result.get("citation") or "",
        last_updated=result.get("last_updated") or "",
        notice=result.get("notice") or "",
        refused=bool(result.get("refused")),
        mode=result.get("mode") or "",
    )


@app.get("/", include_in_schema=False)
def root():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return {"service": "dhairya-iq", "status": "ok"}
