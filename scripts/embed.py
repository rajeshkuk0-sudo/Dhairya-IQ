import glob
import hashlib
import json
import pathlib
import sys
from collections import Counter
from datetime import datetime, timezone

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.loader import load_config
from src.embedding.encoder import encode, text_for_embedding


def load_chunks(cfg) -> list[dict]:
    files = sorted(glob.glob(f"{cfg.paths.chunks}/*.jsonl"))
    if not files:
        raise RuntimeError("No chunks found — run scripts/chunk.py first")
    return [
        json.loads(line)
        for f in files
        for line in open(f, encoding="utf-8")
        if line.strip()
    ]


def main() -> int:
    cfg = load_config()
    chunks = load_chunks(cfg)
    if not chunks:
        raise RuntimeError("No chunks to embed")

    texts = [text_for_embedding(c) for c in chunks]
    print(f"Embedding {len(texts)} chunks with {cfg.embedding.model} ...")
    vectors = encode(texts, cfg).astype(np.float32)

    out = pathlib.Path(cfg.paths.embeddings)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "vectors.npy", vectors)

    manifest = {
        "model": cfg.embedding.model,
        "device": cfg.embedding.device,
        "text_preprocessing": "scheme_or_page_type | section_title + newline + chunk_text",
        "dim": int(vectors.shape[1]),
        "count": len(chunks),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "vectors_file": "vectors.npy",
        "vectors_sha256": hashlib.sha256(vectors.tobytes()).hexdigest(),
        "chunk_ids": [c["chunk_id"] for c in chunks],
        "row_for_chunk": {c["chunk_id"]: i for i, c in enumerate(chunks)},
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    norms = np.linalg.norm(vectors, axis=1)
    print(f"Shape: {vectors.shape} | dim: {vectors.shape[1]} | dtype: {vectors.dtype}")
    print(f"Norm min/max: {norms.min():.4f}/{norms.max():.4f}")
    print("By strategy:", dict(Counter(c["strategy"] for c in chunks)))
    print(f"Wrote {out / 'vectors.npy'}")
    print(f"Wrote {out / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
