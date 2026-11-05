import glob
import json
import pathlib
from datetime import datetime, timezone

from src.common.logging import get_logger
from src.config.schema import AppConfig

from .models import Document

log = get_logger(__name__)
ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = ROOT / "data" / "load" / "documents.jsonl"


def load_documents(
    cfg: AppConfig,
    *,
    doc_ids: set[str] | None = None,
    scheme: str | None = None,
) -> list[Document]:
    """Read, validate, filter and dedupe cleaned docs written by the scrape stage."""
    files = sorted(glob.glob(f"{cfg.paths.clean}/*.json"))
    if not files:
        raise RuntimeError("No cleaned docs in data/clean — run scripts/ingest.py first")

    by_id: dict[str, Document] = {}
    skipped = 0

    for f in files:
        try:
            doc = Document.from_dict(json.loads(open(f, encoding="utf-8").read()))
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("skip %s: %s", f, e)
            skipped += 1
            continue

        if doc_ids and doc.doc_id not in doc_ids:
            continue
        if scheme and (doc.scheme or "").lower() != scheme.lower():
            continue

        prev = by_id.get(doc.doc_id)
        if prev is None or doc.fetched_at > prev.fetched_at:
            by_id[doc.doc_id] = doc

    docs = sorted(by_id.values(), key=lambda d: (d.scheme or "", d.page_type))
    if not docs:
        raise RuntimeError(f"No valid docs after filtering (skipped {skipped})")

    log.info("loaded %d docs (skipped %d invalid)", len(docs), skipped)
    return docs


def get_doc(cfg: AppConfig, doc_id: str) -> Document | None:
    return next((d for d in load_documents(cfg) if d.doc_id == doc_id), None)


def write_documents_artifact(
    cfg: AppConfig | None,
    docs: list[Document],
    path: str | pathlib.Path = DEFAULT_ARTIFACT,
) -> str:
    """Persist loaded documents so chunking can consume them as a separate stage."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d.to_dict(), ensure_ascii=False) + "\n")
    return str(p)


def load_documents_artifact(path: str | pathlib.Path = DEFAULT_ARTIFACT) -> list[Document]:
    p = pathlib.Path(path)
    if not p.exists():
        raise RuntimeError(f"{p} missing — run scripts/load_docs.py first")
    docs = [
        Document.from_dict(json.loads(line))
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not docs:
        raise RuntimeError(f"{p} is empty — run scripts/load_docs.py first")
    return docs


def write_manifest(docs: list[Document], path: str | pathlib.Path = "data/load/manifest.json") -> str:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "count": len(docs),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "docs": [
                    {
                        "doc_id": d.doc_id,
                        "scheme": d.scheme,
                        "page_type": d.page_type,
                        "url": d.url,
                        "fetched_at": d.fetched_at,
                        "chars": len(d.text),
                    }
                    for d in docs
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return str(p)
