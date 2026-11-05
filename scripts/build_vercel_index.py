import glob
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "vercel"

FIELDS = (
    "doc_id",
    "url",
    "scheme",
    "page_type",
    "section_title",
    "strategy",
    "order",
    "token_count",
    "fetched_at",
)


def main() -> int:
    manifest = json.loads(
        (ROOT / "data" / "embeddings" / "manifest.json").read_text(encoding="utf-8")
    )
    vectors = np.load(ROOT / "data" / "embeddings" / "vectors.npy").astype(np.float32)
    if len(vectors) != len(manifest["chunk_ids"]):
        raise RuntimeError("vectors/manifest count mismatch")

    chunks = {}
    for path in sorted(glob.glob(str(ROOT / "data" / "chunks" / "*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                chunk = json.loads(line)
                chunks[chunk["chunk_id"]] = chunk

    ordered = []
    for cid in manifest["chunk_ids"]:
        if cid not in chunks:
            raise RuntimeError(f"Missing chunk {cid}")
        chunk = chunks[cid]
        ordered.append(
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                **{field: chunk.get(field) if chunk.get(field) is not None else "" for field in FIELDS},
            }
        )

    for item in ordered:
        item["order"] = int(item["order"] or 0)
        item["token_count"] = int(item["token_count"] or 0)

    OUT.mkdir(parents=True, exist_ok=True)
    np.save(OUT / "vectors.npy", vectors)

    index = {
        "model": manifest["model"],
        "dim": int(manifest["dim"]),
        "count": len(ordered),
        "text_preprocessing": manifest["text_preprocessing"],
        "vectors_sha256": manifest["vectors_sha256"],
        "chunks": ordered,
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"Wrote {OUT / 'vectors.npy'} {vectors.shape}")
    print(f"Wrote {OUT / 'index.json'} ({len(ordered)} chunks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
