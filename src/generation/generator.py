import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SYSTEM_PROMPT_PATH = ROOT / "config" / "prompts" / "system.txt"

FAIL_CLOSED_MESSAGE = (
    "I could not produce a verified answer from the official sources. "
    "Please use the linked source for the facts."
)

_MAX_SENTENCES = 3
_ADVICE_ANSWER = (
    "you should",
    "we recommend",
    "i recommend",
    "we suggest",
    "i suggest",
    "best fund",
    "better fund",
    "guaranteed",
    "worth investing",
    "buy this",
    "sell this",
    "switch to",
    "invest in this",
)
_URL_RE = re.compile(r"https?://|www\.", re.I)


def system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def validate(answer: str, allowed_urls: list[str] | None = None) -> tuple[bool, list[str]]:
    text = (answer or "").strip()
    errors: list[str] = []

    if not text:
        errors.append("empty answer")
    if _URL_RE.search(text):
        errors.append("answer contains a URL")
    if len(sentences(text)) > _MAX_SENTENCES:
        errors.append(f"answer exceeds {_MAX_SENTENCES} sentences")

    low = text.lower()
    if any(phrase in low for phrase in _ADVICE_ANSWER):
        errors.append("answer contains investment advice")

    return not errors, errors


def build_prompt(question: str, context: str) -> str:
    return (
        "Official source context:\n"
        f"{context}\n\n"
        f"User question: {question}\n\n"
        "Answer using only the facts above. Maximum 3 sentences. "
        "No URLs. No advice."
    )


def generate(cfg, question: str, context: str, provider) -> dict:
    prompt = build_prompt(question, context)
    raw = provider.complete(system_prompt(), prompt)
    ok, errors = validate(raw)
    attempts = 1

    if not ok:
        corrective = (
            f"{prompt}\n\nYour previous answer was rejected for: {', '.join(errors)}. "
            "Answer again using only the context, with at most 3 sentences, no URLs, "
            "and no investment advice."
        )
        raw = provider.complete(system_prompt(), corrective)
        ok, errors = validate(raw)
        attempts = 2

    return {
        "answer": raw.strip() if ok else FAIL_CLOSED_MESSAGE,
        "valid": ok,
        "raw_response": raw.strip(),
        "prompt": prompt,
        "validation_errors": errors,
        "attempts": attempts,
    }
