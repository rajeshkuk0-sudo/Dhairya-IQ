# Dhairya-IQ

Dhairya-IQ is a facts-only RAG (Retrieval-Augmented Generation) chatbot that answers questions about selected HDFC Mutual Fund schemes using official Groww/AMC, SEBI, and AMFI pages. It refuses investment advice and personal-information requests.

## Requirements

- Windows (commands below use PowerShell)
- Python 3.11 or newer (tested with Python 3.13)
- A free Groq API key: <https://console.groq.com/keys>

## 1. Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

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

This repository includes `data/raw`, `data/clean`, `data/chunks`, and `data/chroma`, so you can run the app immediately. Rebuild only if those are missing or you change the sources/config:

```powershell
python scripts/ingest.py
python scripts/load_docs.py
python scripts/chunk.py
python scripts/embed.py
python scripts/index.py --reset
```

The following generated folders are intentionally excluded from Git and are recreated by the commands above:

| Excluded folder | Rebuilt by |
|---|---|
| `data/embeddings/` | `python scripts/embed.py` |
| `data/load/` | `python scripts/load_docs.py` |
| `data/chroma/` | `python scripts/index.py --reset` (or re-clone this repo, which includes it) |
| `data/retrieval/` | created automatically when you ask a question |
| `data/generation/` | created automatically when you ask a question |
| `data/runs/` | created automatically when the app runs |

## 4. Run the app

```powershell
python -m streamlit run app\streamlit_app.py
```

Open the Local URL shown in the terminal, usually <http://localhost:8501>. Hard-refresh with `Ctrl+Shift+R` after CSS changes.

## 5. Run tests

```powershell
pytest -q
```

## Project structure

```text
app/            Streamlit UI
config/         App config + prompts
scripts/        Pipeline entrypoints (ingest, load, chunk, embed, index)
src/            Application code
tests/          Pytest suite
data/           Source documents, chunks, embeddings, vector index
Docs/           PRD, architecture, and implementation notes
sources.md      Official source pages used by the ingestion pipeline
```

## Notes

- Facts-only. No investment advice.
- Answers use one official citation per response.
- Personal information (PAN, Aadhaar, OTP, email, phone, account numbers) is redacted before processing.
