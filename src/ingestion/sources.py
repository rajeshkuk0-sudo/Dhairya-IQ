import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def read_sources(path: str | pathlib.Path = "sources.md") -> list[dict]:
    """Parse the source table: page_type | scheme | url."""
    p = pathlib.Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise RuntimeError(f"Sources file not found: {p}")

    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "http" not in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[3].startswith("http"):
            rows.append(
                {
                    "page_type": cells[1],
                    "scheme": None if cells[2] in ("—", "-", "") else cells[2],
                    "url": cells[3],
                }
            )
    if not rows:
        raise RuntimeError(f"No sources found in {p}")
    return rows
