import re

PII_PATTERNS = {
    "pan": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "otp": r"\b(?:otp|code)\b\s*[:=]?\s*\d{4,6}|\b\d{4,6}\b(?=\s*(?:otp|code))",
    "email": r"[\w.+-]+@[\w-]+\.[\w.]+",
    "phone": r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b",
    "account": r"\b\d{9,18}\b",
}


def redact(text: str, patterns: dict | None = None) -> str:
    """Replace known PII shapes with [REDACTED]; never echo the original value."""
    for pat in (patterns or PII_PATTERNS).values():
        text = re.sub(pat, "[REDACTED]", text, flags=re.I)
    return text
