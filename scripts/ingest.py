import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.loader import load_config
from src.ingestion.pipeline import load_document
from src.ingestion.sources import read_sources


def main() -> int:
    cfg = load_config()
    sources = read_sources(cfg.corpus.sources_file)
    print(f"Sources: {len(sources)}")

    docs = []
    for s in sources:
        try:
            doc = load_document(cfg, s["url"], s["scheme"], s["page_type"])
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {s['url']}: {e}")
            continue
        if doc:
            docs.append(doc)

    print(f"\nLoaded {len(docs)}/{len(sources)} documents")
    print("Page types:", dict(Counter(d["page_type"] for d in docs)))
    for d in docs:
        print(f"  {d['doc_id']} | {d['scheme'] or d['page_type']:<14} | {len(d['text']):>7} chars")
    return 0 if docs else 1


if __name__ == "__main__":
    raise SystemExit(main())
