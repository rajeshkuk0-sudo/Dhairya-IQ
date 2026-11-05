import argparse
import json
import pathlib
from datetime import datetime, timezone

import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModel, AutoTokenizer

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_OUT = ROOT / "models" / "minilm-onnx"
MAX_LENGTH = 256


class LastHiddenState(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask, token_type_ids):
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            return_dict=False,
        )
        return outputs[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export all-MiniLM-L6-v2 to quantized ONNX")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.model} ...")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    try:
        model = AutoModel.from_pretrained(args.model, attn_implementation="eager")
    except TypeError:
        model = AutoModel.from_pretrained(args.model)
    model.eval()

    wrapper = LastHiddenState(model)
    wrapper.eval()

    sample = tokenizer(
        ["Dhairya-IQ embedding export check"],
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    input_ids = sample["input_ids"]
    attention_mask = sample["attention_mask"]
    token_type_ids = sample.get("token_type_ids")
    if token_type_ids is None:
        token_type_ids = torch.zeros_like(input_ids)

    fp32_path = out / "model.fp32.onnx"
    print("Exporting fp32 ONNX ...")
    with torch.no_grad():
        torch.onnx.export(
            wrapper,
            (input_ids, attention_mask, token_type_ids),
            str(fp32_path),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["last_hidden_state"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "sequence"},
                "attention_mask": {0: "batch", 1: "sequence"},
                "token_type_ids": {0: "batch", 1: "sequence"},
                "last_hidden_state": {0: "batch", 1: "sequence"},
            },
            opset_version=17,
            do_constant_folding=True,
            dynamo=False,
        )

    print("Quantizing to uint8 ...")
    quantize_dynamic(
        str(fp32_path),
        str(out / "model.onnx"),
        weight_type=QuantType.QUInt8,
        per_channel=True,
    )
    fp32_path.unlink(missing_ok=True)

    print("Saving tokenizer ...")
    tokenizer.save_pretrained(out)
    if not (out / "tokenizer.json").exists():
        tokenizer.backend_tokenizer.save(str(out / "tokenizer.json"))

    info = {
        "model": args.model,
        "max_length": MAX_LENGTH,
        "dim": int(model.config.hidden_size),
        "pooling": "mean",
        "normalize": True,
        "quantization": "uint8_dynamic",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (out / "model_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    size_mb = (out / "model.onnx").stat().st_size / (1024 * 1024)
    print(f"Wrote {out / 'model.onnx'} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
