import pytest

from src.chunking import strategies as S
from src.chunking.agent import chunk_document, decide_strategy
from src.config.loader import load_config


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def make_doc(text: str, doc_id: str = "d1") -> dict:
    return {
        "doc_id": doc_id,
        "url": "https://groww.in/mutual-funds/example",
        "scheme": "HDFC Example Fund",
        "page_type": "scheme_fact",
        "fetched_at": "2026-11-01T00:00:00+00:00",
        "content_hash": "h",
        "title": "Example",
        "text": text,
    }


FACT_TEXT = """Key Facts (from official page):
- Expense ratio: 0.75%
- Minimum SIP: ₹100
- Benchmark: NIFTY 500 Total Return Index
- Exit load: Exit load of 1% if redeemed within 1 year
- Riskometer (risk level): Very High risk

About the fund
This is a flexi cap fund that invests across market capitalisations.
"""


def test_auto_strategy_picks_section_for_key_facts(cfg):
    decision = decide_strategy(make_doc(FACT_TEXT), cfg)
    assert decision["strategy"] == "section"
    assert "key-facts" in decision["rationale"]


def test_chunk_document_keeps_facts_together(cfg):
    chunks, decision = chunk_document(make_doc(FACT_TEXT), cfg)
    assert chunks
    joined = "\n".join(c.text for c in chunks)
    assert "Expense ratio: 0.75%" in joined
    assert "Exit load of 1%" in joined
    assert decision["n_chunks"] == len(chunks)


def test_chunk_ids_are_deterministic(cfg):
    a, _ = chunk_document(make_doc(FACT_TEXT, "docA"), cfg)
    b, _ = chunk_document(make_doc(FACT_TEXT, "docA"), cfg)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert a[0].chunk_id.startswith("docA:")


def test_no_chunk_shorter_than_minimum(cfg):
    chunks, _ = chunk_document(make_doc(FACT_TEXT), cfg)
    assert all(len(c.text) >= 30 for c in chunks)


def test_table_split_repeats_header_per_row():
    text = "| Scheme | TER |\n|---|---|\n| HDFC Flexi | 0.75% |\n| HDFC Mid | 0.74% |"
    chunks = S.table_split(text, 800, 120)
    table_chunks = [c for _, c in chunks if "|" in c]
    assert table_chunks
    assert all("| Scheme | TER |" in c for c in table_chunks)


def test_section_split_regroups_paragraphs():
    text = "Heading One\nBody one is here.\n\nHeading Two\nBody two is here."
    chunks = S.section_split(text, 800, 0)
    titles = [t for t, _ in chunks]
    assert "Heading One" in titles
    assert "Heading Two" in titles
