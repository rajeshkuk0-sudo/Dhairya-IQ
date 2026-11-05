import pathlib
import re
from dataclasses import dataclass

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]

EDU_LINK = "https://investor.sebi.gov.in/"
AMC_LINK = "https://groww.in/mutual-funds/amc/hdfc-mutual-funds"

MAX_QUERY_CHARS = 512

ADVICE = (
    "should i",
    "should we",
    "better",
    "best fund",
    "which fund",
    "buy",
    "sell",
    "switch",
    "hold",
    "recommend",
    "good for me",
    "worth investing",
    "compare",
    "performance",
    "returns",
    "return",
    "outperform",
)
FACT_HINTS = (
    "hdfc",
    "expense",
    "exit load",
    "sip",
    "lock",
    "riskometer",
    "benchmark",
    "statement",
    "capital gain",
    "elss",
    "large cap",
    "flexi",
    "mid cap",
    "minimum",
    "nav",
    "aum",
    "fund size",
    "download",
)
INJECTION = (
    "ignore previous",
    "ignore all previous",
    "ignore the rules",
    "disregard",
    "system prompt",
    "you are now",
    "jailbreak",
    "developer mode",
    "act as",
)
OTHER_AMCS = (
    "sbi",
    "icici",
    "axis",
    "kotak",
    "nippon",
    "aditya birla",
    "uti",
    "tata",
    "motilal",
    "parag parikh",
    "mirae",
    "dsp",
    "franklin",
    "canara",
    "idfc",
    "bandhan",
    "quant",
    "navi",
    "hsbc",
    "invesco",
    "edelweiss",
    "lic",
    "pgim",
    "baroda",
    "shriram",
)


@dataclass
class GuardResult:
    intent: str
    clean_query: str
    pii_found: list[str]
    residual_intent: str = ""
    reason: str = ""


def load_patterns(path: str | pathlib.Path | None = None) -> dict[str, str]:
    if path is None:
        path = ROOT / "config" / "prompts" / "pii_patterns.yaml"
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def redact(query: str, patterns: dict | None = None) -> tuple[str, list[str]]:
    found: list[str] = []
    patterns = patterns if patterns is not None else load_patterns()
    for name, pat in patterns.items():
        if re.search(pat, query, flags=re.I):
            found.append(name)
            query = re.sub(pat, "[REDACTED]", query, flags=re.I)
    return query, found


def _has_fact(q: str) -> bool:
    return any(h in q for h in FACT_HINTS)


def _has_advice(q: str) -> bool:
    return any(h in q for h in ADVICE)


def _classify_clean(q: str) -> tuple[str, str]:
    q = q.lower().strip()
    if not q:
        return "OUT_OF_SCOPE", "empty query"

    if any(term in q for term in INJECTION):
        return ("ADVICE" if _has_fact(q) else "OUT_OF_SCOPE"), "prompt injection"

    if _has_advice(q):
        return "ADVICE", "advice or recommendation language"

    mentions_other = any(re.search(rf"\b{re.escape(a)}\b", q) for a in OTHER_AMCS)
    if mentions_other and "hdfc" not in q:
        return "OUT_OF_SCOPE", "non-HDFC fund"

    if not _has_fact(q):
        return "OUT_OF_SCOPE", "no HDFC factual topic"

    return "FACTUAL", ""


def classify(query: str, cfg) -> GuardResult:
    clean = (query or "").strip()[:MAX_QUERY_CHARS]
    patterns = load_patterns(cfg.guardrails.pii_patterns_file)
    clean, pii = redact(clean, patterns)

    residual, reason = _classify_clean(clean)
    if pii:
        return GuardResult(
            intent="PII_RISK",
            clean_query=clean,
            pii_found=pii,
            residual_intent=residual,
            reason="personal information detected",
        )
    return GuardResult(
        intent=residual,
        clean_query=clean,
        pii_found=[],
        residual_intent=residual,
        reason=reason,
    )
