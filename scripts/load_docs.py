import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.loader import load_config
from src.ingestion.loader import (
    load_documents,
    write_documents_artifact,
    write_manifest,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Load documents before chunking")
    p.add_argument("--scheme", help="filter by scheme name (case-insensitive)")
    p.add_argument("--doc-id", help="load a single document by id")
    p.add_argument("--manifest", action="store_true", help="also write data/load/manifest.json")
    args = p.parse_args()

    cfg = load_config()
    docs = load_documents(
        cfg,
        scheme=args.scheme,
        doc_ids={args.doc_id} if args.doc_id else None,
    )

    print(f"Loaded {len(docs)} docs")
    for d in docs:
        print(f"  {d.doc_id} | {d.scheme or d.page_type:<14} | {len(d.text):>6} chars")

    artifact = write_documents_artifact(cfg, docs)
    print(f"Wrote {artifact}")

    if args.manifest:
        print(f"Wrote {write_manifest(docs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
