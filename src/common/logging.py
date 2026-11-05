import logging
import re
import sys

PII_KEYS = ("pan", "aadhaar", "otp", "email", "phone", "account")

_PII_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"),
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
]


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pat in _PII_PATTERNS:
            msg = pat.sub("[REDACTED]", msg)
        record.msg = msg
        record.args = ()
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        handler.addFilter(RedactFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
