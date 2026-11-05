import glob
import json
import pathlib
import sys

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.embedding.encoder import text_for_embedding as st_text_for_embedding
from src.embedding.onnx_encoder import encode as onnx_encode, text_for_embedding


def cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.clip(np.linalg.norm(a, axis=1, keepdims=True), 1e-9, None)
    b = b / np.clip(np.linalg.norm(b, axis=1, keepdims=True), 1e-9, None)
    return np.sum(a * b, axis=1)


def main() -> int:
    st = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")

    queries = [
        "What is the expense ratio of HDFC Flexi Cap Fund Direct Growth?",
        "What is the exit load and minimum SIP for HDFC Mid Cap Fund?",
        "What is the lock-in period for HDFC ELSS Tax Saver?",
    ]
    onnx_q = onnx_encode(queries)
    st_q = st.encode(queries, normalize_embeddings=True, show_progress_bar=False)
    print("query cosines:", np.round(cosine(onnx_q, st_q), 6).tolist())

    chunks = []
    for path in sorted(glob.glob(str(ROOT / "data" / "chunks" / "*.jsonl"))):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                chunks.append(json.loads(line))
    by_id = {c["chunk_id"]: c for c in chunks}
    manifest = json.loads((ROOT / "data" / "embeddings" / "manifest.json").read_text(encoding="utf-8"))
    ordered = [by_id[cid] for cid in manifest["chunk_ids"]]

    texts = [text_for_embedding(c) for c in ordered]
    assert all(text_for_embedding(c) == st_text_for_embedding(c) for c in ordered)

    onnx_vecs = onnx_encode(texts)
    stored = np.load(ROOT / "data" / "embeddings" / "vectors.npy").astype(np.float32)
    sims = cosine(onnx_vecs, stored)
    print(f"corpus shape: {onnx_vecs.shape} vs {stored.shape}")
    print(f"corpus cosine min={sims.min():.6f} mean={sims.mean():.6f} max={sims.max():.6f}")
    print(f"oracle top-4 overlap: {top_overlap(onnx_vecs, stored)}")
    return 0 if sims.min() > 0.99 else 1


def top_overlap(onnx_vecs: np.ndarray, stored: np.ndarray) -> int:
    matches = 0
    for i in range(len(onnx_vecs)):
        a = set(np.argsort(-(stored @ onnx_vecs[i]))[:4].tolist())
        b = set(np.argsort(-(stored @ stored[i]))[:4].tolist())
        matches += len(a & b)
    return matches


if __name__ == "__main__":
    raise SystemExit(main())
