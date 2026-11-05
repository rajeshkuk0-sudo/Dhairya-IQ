import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chunking.agent import chunk_document
from src.config.loader import load_config

ARTIFACT = ROOT / "data" / "load" / "documents.jsonl"


def load_input_docs(cfg) -> list[dict]:
    """Prefer the load-stage artifact; fall back to cleaned scrape output."""
    if ARTIFACT.exists():
        docs = [json.loads(line) for line in ARTIFACT.read_text(encoding="utf-8").splitlines() if line.strip()]
        if docs:
            print(f"Input: {ARTIFACT.relative_to(ROOT)} ({len(docs)} docs)")
            return docs

    files = sorted(pathlib.Path(cfg.paths.clean).glob("*.json"))
    docs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    if not docs:
        raise RuntimeError("No documents found — run scripts/ingest.py first")
    print(f"Input: {cfg.paths.clean} ({len(docs)} docs)")
    return docs


def main() -> int:
    cfg = load_config()
    docs = load_input_docs(cfg)

    out_dir = pathlib.Path(cfg.paths.chunks)
    out_dir.mkdir(parents=True, exist_ok=True)

    decisions: dict[str, dict] = {}
    total = 0

    for doc in docs:
        chunks, decision = chunk_document(doc, cfg)
        decisions[doc["doc_id"]] = decision

        out = out_dir / f"{doc['doc_id']}.jsonl"
        out.write_text(
            "\n".join(json.dumps(c.to_dict(), ensure_ascii=False) for c in chunks),
            encoding="utf-8",
        )
        total += len(chunks)
        print(
            f"  {doc['doc_id']} | {doc['scheme'] or doc['page_type']:<14} "
            f"| {decision['strategy']:<9} | {len(chunks):>3} chunks"
        )

    (out_dir / "decisions.json").write_text(
        json.dumps(decisions, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"\nTotal: {total} chunks from {len(docs)} docs")
    print("Strategies:", dict(Counter(d["strategy"] for d in decisions.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
