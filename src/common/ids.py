import hashlib


def doc_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def chunk_id(doc: str, idx: int) -> str:
    return f"{doc}:{idx:04d}"


def query_id(q: str) -> str:
    return hashlib.sha256(q.encode("utf-8")).hexdigest()[:12]
