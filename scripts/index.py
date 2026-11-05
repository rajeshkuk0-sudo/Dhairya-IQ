import argparse
import glob
import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config.loader import load_config
from src.vectorstore.chroma_store import ChromaStore


def load_chunks(cfg) -> dict[str, dict]:
    chunks: dict[str, dict] = {}
    for f in sorted(glob.glob(f"{cfg.paths.chunks}/*.jsonl")):
        for line in open(f, encoding="utf-8"):
            if line.strip():
                c = json.loads(line)
                chunks[c["chunk_id"]] = c
    if not chunks:
        raise RuntimeError("No chunks found — run scripts/chunk.py first")
    return chunks


def main(reset: bool = False) -> int:
    cfg = load_config()
    emb_dir = pathlib.Path(cfg.paths.embeddings)
    manifest = json.loads((emb_dir / "manifest.json").read_text(encoding="utf-8"))
    vectors = np.load(emb_dir / manifest["vectors_file"])

    chunks_by_id = load_chunks(cfg)
    missing = [cid for cid in manifest["chunk_ids"] if cid not in chunks_by_id]
    if missing:
        raise RuntimeError(f"{len(missing)} embedded ids have no chunk — rerun embed")
    if len(vectors) != len(manifest["chunk_ids"]):
        raise RuntimeError("vectors/manifest count mismatch — rerun scripts/embed.py")

    ordered = [chunks_by_id[cid] for cid in manifest["chunk_ids"]]

    store = ChromaStore(cfg)
    if reset:
        print(f"Resetting collection '{cfg.vector_db.collection}'")
        store.reset()

    store.upsert(ordered, vectors)
    count = store.count()

    out = pathlib.Path(cfg.vector_db.persist_dir)
    meta = {
        "collection": cfg.vector_db.collection,
        "persist_dir": cfg.vector_db.persist_dir,
        "distance": cfg.vector_db.distance,
        "model": manifest["model"],
        "dim": manifest["dim"],
        "count": count,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "vectors_sha256": manifest["vectors_sha256"],
    }
    (out / "index.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Indexed {count} chunks into '{cfg.vector_db.collection}'")
    print(f"Wrote {out / 'index.json'}")
    return 0 if count == len(ordered) else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Store chunk embeddings in Chroma")
    p.add_argument("--reset", action="store_true", help="wipe the collection before indexing")
    raise SystemExit(main(p.parse_args().reset))
