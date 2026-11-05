from dataclasses import dataclass

REQUIRED = {"doc_id", "url", "scheme", "page_type", "fetched_at", "text"}


@dataclass
class Document:
    doc_id: str
    url: str
    scheme: str | None
    page_type: str
    fetched_at: str
    content_hash: str
    title: str
    text: str

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        missing = REQUIRED - d.keys()
        if missing:
            raise ValueError(f"missing fields: {sorted(missing)}")
        if not str(d.get("text", "")).strip():
            raise ValueError("empty text")
        return cls(
            doc_id=d["doc_id"],
            url=d["url"],
            scheme=d.get("scheme"),
            page_type=d["page_type"],
            fetched_at=d["fetched_at"],
            content_hash=d.get("content_hash", ""),
            title=d.get("title", ""),
            text=d["text"],
        )

    def to_dict(self) -> dict:
        return self.__dict__.copy()
