from dataclasses import dataclass, field

AMC_LINK = "https://groww.in/mutual-funds/amc/hdfc-mutual-funds"
NOT_FOUND_MESSAGE = "Not found in official sources."


class EmptyRetrievalError(RuntimeError):
    """Raised when retrieval has no usable hits (fail-closed downstream)."""


@dataclass
class RetrievalResult:
    query: str
    query_id: str
    hits: list[dict] = field(default_factory=list)
    message: str = ""
    amc_link: str = AMC_LINK

    @property
    def empty(self) -> bool:
        return not self.hits


@dataclass
class ContextBundle:
    text: str = ""
    sources: list[str] = field(default_factory=list)
    chunks: list[dict] = field(default_factory=list)
    message: str = ""

    @property
    def empty(self) -> bool:
        return not self.chunks
