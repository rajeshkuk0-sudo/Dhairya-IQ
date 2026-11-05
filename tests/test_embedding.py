import glob
import json
import pathlib

import numpy as np

from src.embedding.encoder import text_for_embedding


def test_embedding_text_includes_source_context():
    text = text_for_embedding(
        {
            "scheme": "HDFC Flexi Cap Direct Plan Growth",
            "page_type": "scheme_fact",
            "section_title": "Key Facts",
            "text": "- Expense ratio: 0.75%",
        }
    )
    assert text.startswith("HDFC Flexi Cap Direct Plan Growth | Key Facts\n")
    assert text.endswith("- Expense ratio: 0.75%")


def test_manifest_matches_chunks():
    manifest = json.loads(
        pathlib.Path("data/embeddings/manifest.json").read_text(encoding="utf-8")
    )
    n_chunks = sum(
        1
        for f in glob.glob("data/chunks/*.jsonl")
        for line in open(f, encoding="utf-8")
        if line.strip()
    )
    assert manifest["count"] == n_chunks == len(manifest["chunk_ids"])


def test_vectors_shape_and_dim():
    manifest = json.loads(
        pathlib.Path("data/embeddings/manifest.json").read_text(encoding="utf-8")
    )
    vectors = np.load("data/embeddings/vectors.npy")
    assert vectors.shape == (manifest["count"], 384)
    assert manifest["dim"] == 384


def test_vectors_are_normalized():
    vectors = np.load("data/embeddings/vectors.npy")
    norms = np.linalg.norm(vectors, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-4)


def test_row_mapping_is_stable():
    manifest = json.loads(
        pathlib.Path("data/embeddings/manifest.json").read_text(encoding="utf-8")
    )
    for row, cid in enumerate(manifest["chunk_ids"]):
        assert manifest["row_for_chunk"][cid] == row
