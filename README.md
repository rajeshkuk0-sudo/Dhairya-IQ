# Dhairya-IQ

Dhairya-IQ is a facts-only RAG (Retrieval-Augmented Generation) chatbot that answers questions about selected HDFC Mutual Fund schemes using official Groww/AMC, SEBI, and AMFI pages. It refuses investment advice and personal-information requests.

## Requirements

- Windows (commands below use PowerShell)
- Python 3.11 or newer (tested with Python 3.13)
- A free Groq API key: <https://console.groq.com/keys>

## 1. Install dependencies

For the local Streamlit app (includes Chroma and sentence-transformers):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-local.txt
```

The Vercel deployment uses the smaller `requirements.txt` (FastAPI + ONNX Runtime + NumPy) and does not install Streamlit or PyTorch. See [Deploy to Vercel](#6-deploy-to-vercel).

## 2. Configure environment variables

Copy `.env.example` to `.env`, then open `.env` and fill in your real values:

```powershell
Copy-Item .env.example .env
```

```dotenv
GROQ_API_KEY=your_real_groq_api_key_here
LLM_MODEL=qwen/qwen3.8-27b
```

Never commit `.env`. It is already listed in `.gitignore`.

## 3. Build or rebuild the data pipeline (optional)

This repository includes `data/raw`, `data/clean`, `data/chunks`, and `data/chroma`, so you can run the local app immediately. It also includes `data/vercel/` (prebuilt index + vectors) and `models/minilm-onnx/` (quantized ONNX model) for the Vercel deployment.

Rebuild the local pipeline only if those folders are missing or you change the sources/config:

```powershell
python scripts/ingest.py
python scripts/load_docs.py
python scripts/chunk.py
python scripts/embed.py
python scripts/index.py --reset
```

Rebuild the Vercel assets only if the local index or model changes:

```powershell
python scripts/export_minilm_onnx.py
python scripts/build_vercel_index.py
```

The following generated folders are intentionally excluded from Git and are recreated when the app runs:

| Excluded folder | Recreated by |
|---|---|
| `data/embeddings/` | `python scripts/embed.py` |
| `data/load/` | `python scripts/load_docs.py` |
| `data/retrieval/` | created automatically when you ask a question |
| `data/generation/` | created automatically when you ask a question |
| `data/runs/` | created automatically when the app runs |

## 4. Run the app

```powershell
python -m streamlit run app\streamlit_app.py
```

Open the Local URL shown in the terminal, usually <http://localhost:8501>. Hard-refresh with `Ctrl+Shift+R` after CSS changes.

## 5. Run the Vercel-style API locally (optional)

```powershell
python -m uvicorn main:app --reload --port 8000
```

Open <http://localhost:8000>. Locally, FastAPI serves `public/index.html` at `/`; on Vercel, the same `public/` folder is served from the CDN. The API exposes:

- `GET /api/health`
- `GET /api/config`
- `POST /api/ask` with `{"query": "..."}`

The API uses `config/vercel.yaml`, the ONNX MiniLM model in `models/minilm-onnx/`, and the prebuilt vectors in `data/vercel/`.

## 6. Deploy to Vercel

1. Push the repository to GitHub (the public repo is `rajeshkuk0-sudo/Dhairya-IQ`).
2. In Vercel, import the repo. Vercel auto-detects `main.py` as a FastAPI app.
3. Add the environment variable `GROQ_API_KEY` in **Project Settings → Environment Variables**. Optionally add `LLM_MODEL` (defaults to `qwen/qwen3.8-27b`).
4. Deploy. `vercel.json` sets `maxDuration` to 300 seconds (Hobby limit).

The Vercel build installs `requirements.txt` only. It uses the quantized ONNX model (~22 MB) and `data/vercel/`, so no PyTorch, Chroma, or sentence-transformers are needed. `config/vercel.yaml` writes debug traces to `/tmp` because Vercel's filesystem is read-only.

## 7. Run tests

```powershell
pytest -q
```

## Project structure

```text
main.py         FastAPI entrypoint for Vercel
app/            Streamlit UI
config/         App config + prompts (config.yaml local, vercel.yaml Vercel)
public/         Single-page frontend (Vercel CDN; FastAPI serves it locally)
scripts/        Pipeline entrypoints (ingest, load, chunk, embed, index, ONNX export)
src/            Application code
tests/          Pytest suite
models/         Quantized ONNX MiniLM model for Vercel
data/           Source documents, chunks, local Chroma index, Vercel vectors
Docs/           PRD, architecture, and implementation notes
sources.md      Official source pages used by the ingestion pipeline
```

## Notes

- Facts-only. No investment advice.
- Answers use one official citation per response.
- Personal information (PAN, Aadhaar, OTP, email, phone, account numbers) is redacted before processing.
- Local Streamlit uses Chroma + sentence-transformers. Vercel uses the quantized ONNX MiniLM model + NumPy cosine search. Retrieval is equivalent at the top ranks; a lower-ranked chunk can occasionally differ due to quantization.
