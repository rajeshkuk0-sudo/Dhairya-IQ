import json
from types import SimpleNamespace

import numpy as np
import pytest

from src.config.loader import load_config
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.models import AMC_LINK, NOT_FOUND_MESSAGE
from src.retrieval.retriever import Retriever, rerank
from src.tracing.trace_store import redact


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def _hit(chunk_id, url, text="chunk text here", score=0.9, **meta):
    return {
        "chunk_id": chunk_id,
        "text": text,
        "score": score,
        "metadata": {"url": url, "section_title": meta.get("section_title", "Key Facts"), **meta},
    }


def test_context_builder_dedupes_and_keeps_source_order():
    hits = [
        _hit("a:0001", "https://groww.in/a"),
        _hit("a:0001", "https://groww.in/a"),
        _hit("b:0000", "https://groww.in/b"),
        _hit("c:0000", "https://groww.in/a"),
    ]
    bundle = ContextBuilder().build(hits)
    assert [c["chunk_id"] for c in bundle.chunks] == ["a:0001", "b:0000", "c:0000"]
    assert bundle.sources == ["https://groww.in/a", "https://groww.in/b"]
    assert bundle.text.startswith("[1] https://groww.in/a")
    assert "[2] https://groww.in/b" in bundle.text
    assert not bundle.empty


def test_empty_hits_do_not_call_for_llm_context():
    bundle = ContextBuilder().build([])
    assert bundle.empty
    assert bundle.sources == []
    assert bundle.text == ""
    assert AMC_LINK in bundle.message
    assert "not found in official sources" in bundle.message.lower()


def test_retriever_writes_redacted_trace(cfg, tmp_path, monkeypatch):
    cfg = cfg.model_copy(update={"paths": cfg.paths.model_copy(update={"retrieval": str(tmp_path)})})
    monkeypatch.setattr("src.retrieval.retriever.encode", lambda texts, c: np.zeros((1, 384)))
    store = SimpleNamespace(query=lambda *a, **k: [_hit("x:0000", "https://groww.in/x")])
    retriever = Retriever(cfg, store=store)
    result = retriever.retrieve("My PAN is ABCDE1234F expense ratio")
    assert not result.empty
    payload = json.loads((tmp_path / f"{result.query_id}.json").read_text(encoding="utf-8"))
    assert "ABCDE1234F" not in payload["query"]
    assert "[REDACTED]" in payload["query"]
    assert payload["results"][0]["url"] == "https://groww.in/x"
    assert payload["collection"] == cfg.vector_db.collection
    assert payload["model"] == cfg.embedding.model


def test_empty_retrieval_returns_amc_link(cfg, tmp_path, monkeypatch):
    cfg = cfg.model_copy(update={"paths": cfg.paths.model_copy(update={"retrieval": str(tmp_path)})})
    monkeypatch.setattr("src.retrieval.retriever.encode", lambda texts, c: np.zeros((1, 384)))
    store = SimpleNamespace(query=lambda *a, **k: [])
    result = Retriever(cfg, store=store).retrieve("no such fact")
    assert result.empty
    assert result.message == NOT_FOUND_MESSAGE
    assert result.amc_link == AMC_LINK
    payload = json.loads((tmp_path / f"{result.query_id}.json").read_text(encoding="utf-8"))
    assert payload["empty"] is True
    assert payload["results"] == []


def test_redact_helper():
    assert "ABCDE1234F" not in redact("PAN ABCDE1234F")


def test_search_passes_scheme_filter(cfg, monkeypatch):
    monkeypatch.setattr("src.retrieval.retriever.encode", lambda texts, c: np.zeros((1, 384)))
    seen = {}

    def query(vec, top_k, where=None):
        seen["top_k"] = top_k
        seen["where"] = where
        return []

    Retriever(cfg, store=SimpleNamespace(query=query)).search(
        "expense ratio", top_k=2, scheme="HDFC Flexi Cap Direct Plan Growth"
    )
    assert seen["top_k"] == 2
    assert seen["where"] == {"scheme": "HDFC Flexi Cap Direct Plan Growth"}


def test_rerank_prefers_key_facts_over_similar_tables():
    sebi = _hit(
        "edu:0000",
        "https://investor.sebi.gov.in/",
        text="Welcome to the SEBI investor website",
        score=0.19,
        page_type="education",
        scheme="",
        section_title="",
    )
    facts = _hit(
        "elss:0000",
        "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
        text="Key Facts\n- Lock-in: ELSS • 3Y Lock-in\n- Expense ratio: 1.20%",
        score=0.16,
        page_type="scheme_fact",
        scheme="HDFC ELSS Tax Saver Direct Plan Growth",
        section_title="Key Facts (from official page):",
    )
    ranked = rerank("ELSS lock-in", [sebi, facts])
    assert ranked[0]["chunk_id"] == "elss:0000"


def test_probe_expense_ratio_flexi_cap(cfg):
    result = Retriever(cfg).retrieve("expense ratio flexi cap")
    assert not result.empty
    top = result.hits[0]
    url = top["metadata"]["url"]
    assert url.startswith("https://")
    assert "hdfc-equity-fund-direct-growth" in url
    assert "expense" in top["text"].lower()


def test_probe_elss_lock_in(cfg):
    result = Retriever(cfg).retrieve("ELSS lock-in")
    assert not result.empty
    url = result.hits[0]["metadata"]["url"]
    assert url.startswith("https://")
    assert "hdfc-elss-tax-saver" in url
    assert "lock-in" in result.hits[0]["text"].lower()


def test_probe_capital_gains_has_official_url(cfg):
    result = Retriever(cfg).retrieve("download capital gains statement")
    assert result.hits or result.empty
    if result.empty:
        assert result.amc_link.startswith("https://")
        return
    url = result.hits[0]["metadata"]["url"]
    assert url.startswith("https://")
    assert any(d in url for d in ("groww.in", "sebi.gov.in", "amfiindia.com"))
