import re

_SEPARATOR = re.compile(r"^\|?[\s:|-]+\|?$")


def _window(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step)]


def _title_of(text: str) -> str | None:
    first = text.splitlines()[0].strip().lstrip("# ").strip()
    if not first or len(first) > 80 or first.startswith("- "):
        return None
    return first


def section_split(text: str, size: int, overlap: int) -> list[tuple[str | None, str]]:
    """Split on blank-line paragraphs / headings; window long sections."""
    out: list[tuple[str | None, str]] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        title = _title_of(para)
        for w in _window(para, size, overlap):
            out.append((title, w))
    return out


def recursive_split(text: str, size: int, overlap: int) -> list[tuple[str | None, str]]:
    return [(None, w) for w in _window(text, size, overlap)]


def table_split(text: str, size: int, overlap: int) -> list[tuple[str | None, str]]:
    """Keep a table header with each row; window other text normally."""
    out: list[tuple[str | None, str]] = []
    header: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if buffer:
            chunk = "\n".join(buffer).strip()
            if chunk:
                for w in _window(chunk, size, overlap):
                    out.append((None, w))
            buffer = []

    for line in text.splitlines():
        if line.count("|") >= 2:
            flush()
            if _SEPARATOR.match(line.strip()):
                continue
            if header is None:
                header = line
                continue
            out.append((None, f"{header}\n{line}"))
        else:
            header = None
            if not line.strip():
                flush()
                continue
            buffer.append(line)

    flush()
    return out
