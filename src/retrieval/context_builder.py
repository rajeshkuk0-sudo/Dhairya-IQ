from .models import AMC_LINK, NOT_FOUND_MESSAGE, ContextBundle


class ContextBuilder:
    """Dedupe hits, keep one citation per URL, and assemble prompt context."""

    def build(self, results: list[dict]) -> ContextBundle:
        seen: set[str] = set()
        sources: list[str] = []
        chunks: list[dict] = []
        blocks: list[str] = []

        for r in results:
            if r["chunk_id"] in seen:
                continue
            seen.add(r["chunk_id"])
            chunks.append(r)

            m = r.get("metadata") or {}
            url = m.get("url") or ""
            if url and url not in sources:
                sources.append(url)

            label = " | ".join(p for p in (m.get("scheme"), m.get("section_title")) if p)
            blocks.append(f"[{len(chunks)}] {url} | {label}\n{r['text']}")

        message = "" if chunks else f"{NOT_FOUND_MESSAGE} See {AMC_LINK}"
        return ContextBundle(text="\n\n".join(blocks), sources=sources, chunks=chunks, message=message)
