from src.retrieval.models import AMC_LINK


def valid_citation(url: str | None, sources: list[str]) -> str:
    """A citation must come from retrieved metadata, never from the model."""
    if url and url in sources:
        return url
    return sources[0] if sources else AMC_LINK
