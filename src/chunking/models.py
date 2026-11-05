from dataclasses import asdict, dataclass


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    url: str
    scheme: str | None
    page_type: str
    section_title: str | None
    text: str
    token_count: int
    strategy: str
    order: int
    fetched_at: str

    def to_dict(self) -> dict:
        return asdict(self)
