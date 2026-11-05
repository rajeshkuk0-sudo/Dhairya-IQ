import re


def normalize(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_fresh(old_hash: str | None, new_hash: str) -> bool:
    return old_hash != new_hash
