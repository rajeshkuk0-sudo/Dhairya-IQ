import pathlib

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "minilm-onnx"
MODEL_PATH = MODEL_DIR / "model.onnx"
TOKENIZER_PATH = MODEL_DIR / "tokenizer.json"
MAX_LENGTH = 256

_SESSION = None
_TOKENIZER = None


def _load():
    global _SESSION, _TOKENIZER
    if _SESSION is None:
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        _SESSION = ort.InferenceSession(
            str(MODEL_PATH),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
    if _TOKENIZER is None:
        _TOKENIZER = Tokenizer.from_file(str(TOKENIZER_PATH))
        _TOKENIZER.enable_truncation(max_length=MAX_LENGTH)
        _TOKENIZER.enable_padding(pad_id=0, pad_token="[PAD]")
    return _SESSION, _TOKENIZER


def is_loaded() -> bool:
    return _SESSION is not None


def text_for_embedding(chunk: dict) -> str:
    label = chunk.get("scheme") or chunk.get("page_type") or ""
    section = chunk.get("section_title") or ""
    prefix = " | ".join(p for p in (label, section) if p)
    return f"{prefix}\n{chunk['text']}" if prefix else chunk["text"]


def encode(texts, cfg=None) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    session, tokenizer = _load()
    encodings = tokenizer.encode_batch([text or "" for text in texts])

    input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    token_type_ids = np.array([e.type_ids for e in encodings], dtype=np.int64)

    feeds = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "token_type_ids": token_type_ids,
    }
    available = {item.name for item in session.get_inputs()}
    feeds = {name: value for name, value in feeds.items() if name in available}

    last_hidden = session.run(None, feeds)[0]

    mask = attention_mask[..., None].astype(np.float32)
    summed = (last_hidden * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), 1e-9, None)
    pooled = summed / counts

    norms = np.linalg.norm(pooled, axis=1, keepdims=True)
    return (pooled / np.clip(norms, 1e-9, None)).astype(np.float32)
