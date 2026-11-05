import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.loader import load_config
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.retriever import Retriever

PROBES = [
    "expense ratio flexi cap",
    "ELSS lock-in",
    "download capital gains statement",
]


def run(retriever: Retriever, query: str, top_k: int, scheme: str | None, as_json: bool) -> None:
    result = retriever.retrieve(query, top_k=top_k, scheme=scheme)
    bundle = ContextBuilder().build(result.hits)

    if as_json:
        print(
            json.dumps(
                {
                    "query": result.query,
                    "query_id": result.query_id,
                    "empty": result.empty,
                    "message": result.message,
                    "results": [
                        {
                            "rank": i,
                            "chunk_id": h["chunk_id"],
                            "score": round(h["score"], 6),
                            "rerank_score": round(h["rerank_score"], 6),
                            "scheme": h["metadata"]["scheme"],
                            "page_type": h["metadata"]["page_type"],
                            "url": h["metadata"]["url"],
                        }
                        for i, h in enumerate(result.hits, 1)
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    print(f"\nQ: {result.query}" + (f"  [scheme={scheme}]" if scheme else ""))
    if result.empty:
        print(f"  {result.message} -> {result.amc_link}")
        return
    for i, h in enumerate(result.hits, 1):
        m = h["metadata"]
        snippet = " ".join(h["text"].split())[:90]
        print(
            f"  {i}. score={h['score']:.4f} (rerank {h['rerank_score']:.4f})"
            f" | {m['scheme'] or m['page_type']:<38} | {m['url']}"
        )
        print(f"     {snippet}")
    print(f"  sources: {len(bundle.sources)} unique | trace: {result.query_id}")


def main() -> int:
    p = argparse.ArgumentParser(description="Retrieve ranked chunks for a query")
    p.add_argument("query", nargs="*", help="query text (omit to run probe queries)")
    p.add_argument("--scheme", help="metadata filter: exact scheme name")
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--json", action="store_true", help="machine-readable output")
    args = p.parse_args()

    cfg = load_config()
    retriever = Retriever(cfg)
    top_k = args.top_k or cfg.retrieval.top_k

    queries = [" ".join(args.query)] if args.query else PROBES
    for q in queries:
        run(retriever, q, top_k, args.scheme, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
