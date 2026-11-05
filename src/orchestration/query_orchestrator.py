import json
import pathlib
from datetime import datetime, timezone

from src.common.ids import query_id
from src.config.schema import AppConfig
from src.generation.citation import valid_citation
from src.generation.generator import FAIL_CLOSED_MESSAGE, generate
from src.generation.guardrails import AMC_LINK, EDU_LINK, GuardResult, classify
from src.generation.providers.groq import GroqProvider, ProviderError
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.models import NOT_FOUND_MESSAGE
from src.retrieval.retriever import Retriever

_ADVICE_REFUSAL = (
    "I can only answer factual questions about HDFC mutual funds. "
    "I cannot give investment advice or recommend a fund."
)
_OUT_OF_SCOPE_REFUSAL = (
    "I can only answer factual questions about HDFC mutual funds covered by "
    "the official sources."
)
_EMPTY_REFUSAL = "Please type a factual question about HDFC mutual funds."
_PII_REFUSAL = (
    "I removed personal information from your message and cannot process it. "
    "Please ask a factual HDFC mutual fund question without personal details."
)
_PII_NOTICE = "Personal information was removed before processing this question."


class QueryOrchestrator:
    def __init__(
        self,
        cfg: AppConfig,
        retriever: Retriever | None = None,
        provider=None,
    ):
        self.cfg = cfg
        self.retriever = retriever or Retriever(cfg)
        self.provider = provider or GroqProvider(cfg)

    def ask(self, query: str) -> dict:
        guard = self._guard(query)

        if guard.intent == "ADVICE":
            return self._refusal(guard, _ADVICE_REFUSAL, EDU_LINK)
        if guard.intent == "OUT_OF_SCOPE":
            message = _EMPTY_REFUSAL if not guard.clean_query.strip() else _OUT_OF_SCOPE_REFUSAL
            return self._refusal(guard, message, AMC_LINK)
        if guard.intent == "PII_RISK" and guard.residual_intent != "FACTUAL":
            return self._refusal(guard, _PII_REFUSAL, AMC_LINK)

        result = self.retriever.retrieve(guard.clean_query)
        bundle = ContextBuilder().build(result.hits)
        last_updated = self._last_updated(result.hits)

        if result.empty:
            answer = f"{NOT_FOUND_MESSAGE} See {AMC_LINK}"
            payload = self._payload(
                query=guard.clean_query,
                qid=result.query_id,
                guard=guard,
                answer=answer,
                citation=AMC_LINK,
                refused=True,
                mode="not_found",
                last_updated=last_updated,
                prompt=bundle.text,
                raw_response=answer,
            )
            payload["hits"] = []
            self._write_generation_trace(payload)
            return payload

        citation = valid_citation(result.hits[0]["metadata"].get("url"), bundle.sources)

        try:
            gen = generate(self.cfg, guard.clean_query, bundle.text, self.provider)
        except ProviderError as exc:
            payload = self._payload(
                query=guard.clean_query,
                qid=result.query_id,
                guard=guard,
                answer=FAIL_CLOSED_MESSAGE,
                citation=citation,
                refused=True,
                mode="error",
                last_updated=last_updated,
                prompt=bundle.text,
                raw_response="",
                errors=[str(exc)],
            )
            payload["hits"] = result.hits
            self._write_generation_trace(payload)
            return payload

        payload = self._payload(
            query=guard.clean_query,
            qid=result.query_id,
            guard=guard,
            answer=gen["answer"],
            citation=citation,
            refused=not gen["valid"],
            mode="llm" if gen["valid"] else "llm_fail_closed",
            last_updated=last_updated,
            prompt=gen["prompt"],
            raw_response=gen["raw_response"],
            errors=gen["validation_errors"],
            attempts=gen["attempts"],
        )
        payload["hits"] = result.hits
        self._write_generation_trace(payload)
        return payload

    def _guard(self, query: str) -> GuardResult:
        clean = (query or "").strip()
        if not self.cfg.guardrails.enabled:
            return GuardResult("FACTUAL", clean[:512], [], "FACTUAL", "guardrails disabled")
        return classify(query, self.cfg)

    def _refusal(
        self,
        guard: GuardResult,
        answer: str,
        citation: str,
    ) -> dict:
        payload = self._payload(
            query=guard.clean_query,
            qid=query_id(guard.clean_query),
            guard=guard,
            answer=answer,
            citation=citation,
            refused=True,
            mode="guardrail",
            last_updated="",
            prompt="",
            raw_response=answer,
        )
        payload["hits"] = []
        self._write_generation_trace(payload)
        return payload

    def _payload(
        self,
        *,
        query: str,
        qid: str,
        guard: GuardResult,
        answer: str,
        citation: str,
        refused: bool,
        mode: str,
        last_updated: str,
        prompt: str,
        raw_response: str,
        errors: list[str] | None = None,
        attempts: int = 0,
    ) -> dict:
        payload = {
            "query": query,
            "query_id": qid,
            "answer": answer,
            "citation": citation,
            "refused": refused,
            "mode": mode,
            "model": self._model_name(),
            "last_updated": last_updated,
            "prompt": prompt,
            "raw_response": raw_response,
            "validation_errors": errors or [],
            "attempts": attempts,
            "intent": guard.intent,
            "pii_redacted": bool(guard.pii_found),
        }
        if guard.pii_found and guard.residual_intent == "FACTUAL":
            payload["notice"] = _PII_NOTICE
        return payload

    def _model_name(self) -> str:
        return getattr(self.provider, "model", None) or "guardrail"

    def _write_generation_trace(self, payload: dict) -> pathlib.Path:
        out = pathlib.Path(self.cfg.paths.generation)
        out.mkdir(parents=True, exist_ok=True)
        trace = {
            "query_id": payload["query_id"],
            "query": payload["query"],
            "mode": payload["mode"],
            "model": payload["model"],
            "intent": payload.get("intent", ""),
            "pii_redacted": payload.get("pii_redacted", False),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "citation": payload["citation"],
            "prompt": payload["prompt"],
            "raw_response": payload["raw_response"],
            "validation_errors": payload.get("validation_errors", []),
            "attempts": payload.get("attempts", 0),
        }
        p = out / f"{payload['query_id']}.json"
        p.write_text(json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    @staticmethod
    def _last_updated(hits: list[dict]) -> str:
        stamps = [
            (h.get("metadata") or {}).get("fetched_at", "")
            for h in hits
            if (h.get("metadata") or {}).get("fetched_at")
        ]
        return max(stamps)[:10] if stamps else ""
