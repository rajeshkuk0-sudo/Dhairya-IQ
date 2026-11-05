import json
import pathlib

import pytest

from src.config.loader import load_config
from src.generation.generator import FAIL_CLOSED_MESSAGE
from src.generation.guardrails import AMC_LINK, EDU_LINK
from src.generation.providers.groq import ProviderError
from src.orchestration.query_orchestrator import QueryOrchestrator


class FakeProvider:
    model = "fake-model"

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def complete(self, system, user):
        self.calls.append((system, user))
        return self.answer


class BrokenProvider(FakeProvider):
    def complete(self, system, user):
        raise ProviderError("provider unavailable")


@pytest.fixture(scope="module")
def cfg():
    return load_config()


def test_factual_answer_has_one_official_citation(cfg):
    provider = FakeProvider("The expense ratio is 0.75%.")
    result = QueryOrchestrator(cfg, provider=provider).ask("expense ratio flexi cap")

    assert result["answer"] == "The expense ratio is 0.75%."
    assert result["citation"] == (
        "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth"
    )
    assert result["mode"] == "llm"
    assert result["refused"] is False
    assert result["last_updated"] == "2026-11-01"
    assert provider.calls


def test_elss_lock_in_answer(cfg):
    provider = FakeProvider("The lock-in period is 3 years.")
    result = QueryOrchestrator(cfg, provider=provider).ask("ELSS lock-in")

    assert "3 years" in result["answer"]
    assert "hdfc-elss-tax-saver" in result["citation"]


def test_empty_query_refused_without_retrieval_or_llm(cfg):
    provider = FakeProvider("should not be used")
    result = QueryOrchestrator(cfg, provider=provider).ask("")

    assert result["refused"] is True
    assert result["mode"] == "guardrail"
    assert result["citation"] == AMC_LINK
    assert "factual question" in result["answer"].lower()
    assert not provider.calls


def test_advice_refused_with_educational_link(cfg):
    provider = FakeProvider("should not be used")
    result = QueryOrchestrator(cfg, provider=provider).ask(
        "Should I buy HDFC Flexi Cap?"
    )

    assert result["refused"] is True
    assert result["intent"] == "ADVICE"
    assert result["citation"] == EDU_LINK
    assert "cannot give investment advice" in result["answer"]
    assert not provider.calls


def test_pii_redacted_before_retrieval_and_llm(cfg):
    provider = FakeProvider("The expense ratio is 0.75%.")
    result = QueryOrchestrator(cfg, provider=provider).ask(
        "My PAN is ABCDE1234F, expense ratio of HDFC Flexi Cap?"
    )

    assert result["intent"] == "PII_RISK"
    assert result["pii_redacted"] is True
    assert result["notice"]
    assert "ABCDE1234F" not in result["query"]
    assert "ABCDE1234F" not in provider.calls[0][1]

    trace = (
        pathlib.Path(cfg.paths.generation) / f"{result['query_id']}.json"
    ).read_text(encoding="utf-8")
    assert "ABCDE1234F" not in trace


def test_invalid_llm_answer_retries_then_fails_closed(cfg):
    provider = FakeProvider("One. Two. Three. Four.")
    result = QueryOrchestrator(cfg, provider=provider).ask("expense ratio flexi cap")

    assert result["refused"] is True
    assert result["mode"] == "llm_fail_closed"
    assert result["answer"] == FAIL_CLOSED_MESSAGE
    assert result["attempts"] == 2
    assert result["validation_errors"]


def test_model_url_is_rejected(cfg):
    provider = FakeProvider("See https://example.com for details.")
    result = QueryOrchestrator(cfg, provider=provider).ask("expense ratio flexi cap")

    assert result["refused"] is True
    assert result["mode"] == "llm_fail_closed"
    assert "https://example.com" not in result["answer"]


def test_provider_error_fails_closed(cfg):
    result = QueryOrchestrator(cfg, provider=BrokenProvider("")).ask(
        "expense ratio flexi cap"
    )

    assert result["refused"] is True
    assert result["mode"] == "error"
    assert result["answer"] == FAIL_CLOSED_MESSAGE
    assert result["citation"]


def test_generation_trace_written(cfg):
    provider = FakeProvider("The exit load is 1%.")
    result = QueryOrchestrator(cfg, provider=provider).ask("exit load flexi cap")

    p = pathlib.Path(cfg.paths.generation) / f"{result['query_id']}.json"
    assert p.exists()
    trace = json.loads(p.read_text(encoding="utf-8"))
    assert trace["model"] == "fake-model"
    assert trace["mode"] == "llm"
    assert trace["prompt"]
