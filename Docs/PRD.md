# PRD — Groww Mutual Fund FAQ Assistant (RAG Prototype)

**Version:** 1.0
**Status:** Draft
**Source:** `Docs/Problemstatement.txt`
**Owner:** Rajesh
**Last Updated:** 2026-11-01

---

## 1. Overview

Build a small, working **FAQ assistant for HDFC mutual fund schemes** using only official public pages (Groww scheme/AMC pages, plus SEBI/AMFI where relevant). The assistant answers **factual** queries — expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and how to download statements — and attaches **exactly one clear source link** to every answer. It must **refuse opinionated or portfolio-advice questions** politely.

The prototype must be a **demonstrable RAG pipeline**, exposing and persisting the output of each stage (loading → chunking → embedding → retrieval → generation) so the retrieval quality and citations can be inspected live.

**One-liner:** Facts-only mutual fund FAQ chatbot over a small curated corpus, with explicit, inspectable RAG stages and mandatory citations.

---

## 2. Problem Statement

Retail users comparing mutual fund schemes and support/content teams answering repetitive MF questions need fast, trustworthy answers about scheme facts (expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, statement downloads). Today these answers are scattered across long scheme pages, and generic LLM answers risk hallucination or turning into investment advice.

We need a RAG assistant that answers **only** from official public sources, cites a source in every answer, and refuses advice-seeking questions.

---

## 3. Goals & Non-Goals

### Goals
- Answer a defined set of factual MF queries accurately for the HDFC AMC + 4 schemes.
- Every answer includes **one** citation link to an official public page.
- Refuse advice/opinion questions with a polite, facts-only message + an educational link.
- Make all RAG stages **explicitly stored and viewable** (data, chunks, embeddings metadata, retrieved chunks, final prompt/answer).
- Keep answers **≤ 3 sentences**, with a `Last updated from sources:` line.
- Be **config-driven** (embedding model, vector DB, chunking strategy, LLM provider/model changeable without code edits).

### Non-Goals
- No investment advice, recommendations, or buy/sell guidance.
- No return computation, performance comparison, or ranking of schemes.
- No PII collection or storage (PAN, Aadhaar, account no., OTP, email, phone).
- No third-party blogs/news as sources; no app back-end screenshots.
- No authentication, user accounts, or persistence of chat history across sessions (demo scope).
- Not production-scale: small corpus (~5 pages) is acceptable.

---

## 4. Target Users

| User | Need |
|---|---|
| Retail investor comparing schemes | Quick factual answers with a trustworthy source link |
| Support / content team | Reduce repetitive MF FAQ responses; consistent, citable answers |
| Evaluator (demo) | Inspect each RAG stage's inputs/outputs to judge retrieval quality |

---

## 5. Scope

### 5.1 Corpus (Data to scrape & store)
| # | Type | Scheme | URL |
|---|---|---|---|
| 1 | AMC overview | HDFC Mutual Fund | https://groww.in/mutual-funds/amc/hdfc-mutual-funds |
| 2 | Large Cap | HDFC Large Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 3 | Flexi Cap | HDFC Flexi Cap Direct Plan Growth | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 4 | ELSS (tax saver) | HDFC ELSS Tax Saver Fund Direct Plan Growth | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 5 | Mid Cap | HDFC Mid Cap Fund Direct Growth | https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth |

**Source list deliverable:** 15–25 official URLs total (the 5 above + supporting SEBI/AMFI/AMC factsheet/statement-download pages used to answer statement/benchmark/riskometer questions). Maintained in `sources.md` (or `sources.csv`) with URL, page type, scheme, and what fact it supports.

### 5.2 Supported Query Intents (factual only)
- Expense ratio (TER) of a scheme
- Exit load (and exit load period)
- Minimum SIP / minimum lumpsum amount
- ELSS lock-in period
- Riskometer / risk level
- Benchmark index
- How to download capital-gains / account statement
- Fund category / plan details (Direct vs Regular, Growth vs IDCW)

### 5.3 Refusal Intents (advice/opinion)
- "Should I buy/sell/switch/hold?"
- "Which fund is better / will give more returns?"
- "Is this good for me?" / portfolio or allocation advice
- Any request for return comparisons or predictions

**Refusal behavior:** polite, facts-only message, no recommendation, plus one relevant **educational** link (e.g., SEBI investor education page).

### 5.4 Out of Scope
- Other AMCs / schemes outside the 5 listed.
- Live NAV/price feeds, transactions, KYC, portfolio import.
- Multi-turn conversational memory beyond current session context (stretch, optional).

---

## 6. Functional Requirements

### FR-1 Ingestion / Data Loading
- Scrape the 5 in-scope pages; extract main content (exclude nav/footer/ads).
- Persist raw HTML and cleaned text per page under `data/raw/` and `data/clean/` with metadata: `url`, `scheme`, `page_type`, `fetched_at`, `content_hash`.
- Re-runs must be idempotent and skip unchanged content (hash check).
- Respect robots/ToS; use a descriptive user-agent; rate-limit requests.

### FR-2 Chunking (AI-assisted strategy selection)
- A **chunking agent** inspects the cleaned document type and selects a strategy, e.g.:
  - Structured key-value/fact blocks (expense ratio, exit load) → **section/heading-aware chunking** (preferred for MF pages).
  - Narrative/FAQ text → **recursive character splitting** with overlap.
  - Tables → **row/record-preserving chunks** (keep header + row together).
- The chosen strategy + parameters (`chunk_size`, `chunk_overlap`, splitter type) are **recorded per document** and saved to `data/chunks/` (JSON/JSONL) with `chunk_id`, `doc_id`, `url`, `scheme`, `text`, `token_count`, `section_title`.
- Rationale for the chosen strategy is logged (agent decision trace) for demo visibility.

### FR-3 Embedding
- Embedding model: **`sentence-transformers/all-MiniLM-L6-v2`** (default; configurable).
- Compute and persist embeddings to `data/embeddings/` (parquet/npz) plus a manifest (`chunk_id → vector index`, model name, dim, timestamp).
- Must be **reproducible**: same model + same chunks → same vectors.

### FR-4 Vector Store
- Vector DB: **ChromaDB** (default; configurable).
- Collection naming includes embedding model + corpus version to avoid stale-mix contamination.
- Persist collection under `data/chroma/`; support rebuild from scratch via a single command.
- Store metadata on each vector: `chunk_id`, `url`, `scheme`, `page_type`, `section_title`, `fetched_at`.

### FR-5 Retrieval
- Use the **same embedding model** and **same vector DB** as ingestion (enforced via shared config).
- Default: top-k similarity search (k configurable, default 4) with optional metadata filter by scheme.
- Persist retrieval traces to `data/retrieval/` per query: query, k, filters, returned `chunk_id`s, scores, source URLs.
- Retrieval must prefer the **exact fact** (e.g., "expense ratio") over semantically similar but different facts; ranking/rerank options should be configurable (stretch: cross-encoder rerank).

### FR-6 Generation (LLM)
- Provider: **Groq API** (default). Model ID set via `.env`/config (problem statement references `qwen/qwen3.8-27b`; final model ID must be the current valid Groq model ID at implementation time — configurable, no hardcoding).
- Also support alternate providers via config interfaces: **Gemini, OpenAI, Anthropic, Mistral** (adapter pattern; at least one alternate working is a stretch goal).
- Prompt rules (system prompt):
  - Answer using **only** retrieved context from official sources.
  - **≤ 3 sentences**, factual, no advice, no performance claims.
  - Include **exactly one** citation link (from retrieved metadata, never invented).
  - If the answer is not present in context, say so and give the closest official link — do **not** guess.
  - Append `Last updated from sources: <date>` from source `fetched_at`.
- Persist generation trace to `data/generation/`: assembled prompt, retrieved chunk IDs, model, params, raw response, final answer, citation URL.

### FR-7 Guardrails (Intent Classification)
- Classify each query as `FACTUAL` | `ADVICE/OPINION` | `OUT_OF_SCOPE` | `PII_RISK`.
- **ADVICE/OPINION** → refuse with facts-only message + educational link.
- **OUT_OF_SCOPE** (scheme not in corpus) → politely state coverage limits + AMC link.
- **PII_RISK** (query contains PAN/Aadhaar/account/OTP/email/phone patterns) → do not store, do not echo; respond with privacy-safe notice.
- No PII is written to logs/traces; redact before persistence.

### FR-8 UI (Tiny Demo)
- Welcome line + **3 example questions** (clickable) + note: **"Facts-only. No investment advice."**
- Each answer shows the **citation link** and `Last updated from sources:` line.
- A **"RAG stages" / debug panel** (tab or expander) to view: cleaned doc text, chunks, embedding manifest info, retrieved chunks with scores, final prompt, and raw LLM output.
- Show disclaimer snippet in the UI (see §10).

---

## 7. Configuration Requirements

All changeable knobs live in a single config file (`config.yaml` or `config.py` + `.env` for secrets):

| Key | Default | Notes |
|---|---|---|
| `embedding.model` | `sentence-transformers/all-MiniLM-L6-v2` | Must match between ingestion & retrieval |
| `embedding.device` | `cpu` | |
| `vector_db.type` | `chroma` | |
| `vector_db.persist_dir` | `data/chroma` | |
| `vector_db.collection` | `mf_faq_{model_slug}` | Version-aware |
| `chunking.strategy` | `auto` (agent-decided) | Override: `section` / `recursive` / `table` |
| `chunking.chunk_size` | `800` | tokens/chars per config |
| `chunking.chunk_overlap` | `120` | |
| `retrieval.top_k` | `4` | |
| `retrieval.rerank` | `false` | |
| `llm.provider` | `groq` | `groq` / `gemini` / `openai` / `anthropic` / `mistral` |
| `llm.model` | `<from .env, e.g. qwen/qwen3.8-27b>` | Configurable, no hardcode |
| `llm.temperature` | `0.2` | Low for factual |
| `llm.max_tokens` | `300` | Enforce ≤3 sentences |
| `guardrails.enabled` | `true` | |
| `paths.data_*` | `data/raw|clean|chunks|embeddings|retrieval|generation` | |
| `GROQ_API_KEY` | — | `.env` only, never committed |

**Rule:** Ingestion and retrieval must read the **same config object** so embedding model and vector DB can never diverge silently.

---

## 8. Phased Implementation Plan

The build is delivered **phase-wise**, each phase producing persisted, demo-visible artifacts.

### Phase 0 — Setup & Scaffolding
- Repo structure, config loader (`.env` + `config.yaml`), logging, `data/` folders.
- Source list file started (`sources.md`).
- **Exit:** config loads; API key read from `.env`; `data/` tree created.

### Phase 1 — Data Loading
- Scraper for the 5 pages → `data/raw/`, cleaned text → `data/clean/`, metadata JSON.
- **Exit:** 5 documents stored with URL/scheme/fetched_at; re-run idempotent.

### Phase 2 — Data Chunking (AI-assisted strategy)
- Chunking agent inspects doc → picks strategy + params → writes `data/chunks/*.jsonl` + decision log.
- **Exit:** chunks for all docs with metadata; strategy rationale viewable.

### Phase 3 — Data Embedding
- Embed chunks with all-MiniLM-L6-v2 → `data/embeddings/` + manifest.
- **Exit:** vectors reproducible; manifest maps chunk_id → vector index.

### Phase 4 — Vector DB (Chroma)
- Upsert chunks+embeddings+metadata into Chroma; rebuild command.
- **Exit:** collection queryable; counts match chunk count; rebuild-from-scratch works.

### Phase 5 — Retrieval
- Top-k retriever using same config; persist `data/retrieval/` traces.
- **Exit:** sample queries return the correct fact chunk with source URL.

### Phase 6 — Generation & Guardrails
- Groq LLM (config model) + refusal classifier + citation enforcement + `Last updated` line.
- Persist `data/generation/` traces (prompt, context, raw + final answer).
- **Exit:** all 7 factual intents answered with 1 citation; advice queries refused; answers ≤3 sentences.

### Phase 7 — UI & Demo Assets
- Streamlit UI (welcome + 3 examples + disclaimer + RAG-stage debug panel).
- Produce deliverable files (source list, sample Q&A, disclaimer snippet, README).
- **Exit:** end-to-end demo runs locally; deliverables complete.

### Phase 8 — Hardening (optional/stretch)
- Alternate provider adapter (Gemini/OpenAI/Anthropic/Mistral), rerank, better table handling, eval harness.

---

## 9. Deliverables

| # | Deliverable | Location |
|---|---|---|
| 1 | Working prototype (app) or ≤3-min demo video | `app/` (Streamlit) + `demo.mp4` if needed |
| 2 | Source list (15–25 official URLs) | `sources.md` / `sources.csv` |
| 3 | README (setup, scope = AMC + schemes, known limits) | `README.md` |
| 4 | Sample Q&A file (5–10 queries + answers + links) | `sample_qa.md` |
| 5 | Disclaimer snippet used in UI | `README.md` + in-app |
| 6 | RAG stage artifacts (data, chunks, embeddings manifest, retrieval & generation traces) | `data/` |

---

## 10. Disclaimer Snippet (UI)

> **Facts-only. No investment advice.** Answers are generated from official public sources (AMC/Groww, SEBI/AMFI) and include a source link. We do not provide buy/sell recommendations or compare returns. Always verify on the official scheme page before investing.

---

## 11. Constraints & Compliance

- **Public sources only** — Groww scheme/AMC pages + SEBI/AMFI official pages. No app back-end screenshots, no third-party blogs.
- **No PII** — never accept, echo, log, or store PAN, Aadhaar, account numbers, OTPs, emails, phone numbers. Redact if detected.
- **No performance claims** — no computing/comparing returns; link to official factsheet if asked.
- **Transparency** — ≤3 sentences per answer; include `Last updated from sources: <date>`.
- **Citation integrity** — citation must come from retrieved metadata; the LLM must never invent a URL. Provide `https://` links only.
- **Secrets** — API keys only in `.env`; `.env` git-ignored.

---

## 12. Acceptance Criteria (Definition of Done)

- [ ] All 5 in-scope pages ingested; cleaned text + metadata persisted.
- [ ] Chunking strategy chosen per doc, params + rationale recorded.
- [ ] Embeddings created with `all-MiniLM-L6-v2`; manifest present.
- [ ] ChromaDB populated and rebuildable from config in one command.
- [ ] Retrieval uses identical embedding model + vector DB as ingestion (verified by config/assertion).
- [ ] Each of the 7 factual intents returns a correct answer with **exactly one** official citation.
- [ ] Advice/opinion queries are refused politely with an educational link.
- [ ] PII-like inputs are not stored or echoed.
- [ ] Answers ≤3 sentences and include `Last updated from sources:`.
- [ ] UI shows welcome line, 3 example questions, and the disclaimer note.
- [ ] RAG-stage debug view exposes docs, chunks, retrieval scores, prompt, and raw LLM output.
- [ ] All 6 deliverables present (prototype, sources, README, sample Q&A, disclaimer, stage artifacts).

---

## 13. Non-Functional Requirements

- **Performance:** end-to-end answer latency ≤ 8s on CPU for a small corpus (embedding precomputed).
- **Reproducibility:** fixed seed/model/versions; config snapshot saved per run.
- **Observability:** every query yields a trace saved under `data/retrieval/` and `data/generation/`.
- **Portability:** runs locally on Windows; Python 3.10+; requirements pinned.
- **Cost:** minimal — Groq free tier; embeddings on CPU.
- **Maintainability:** provider/model/DB/chunking swappable via config without code changes.

---

## 14. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Groww pages change layout / block scraping | Ingestion breaks | Store raw HTML snapshot; easy selectors; graceful failure + manual fallback |
| Facts not present in 5 pages (e.g., statement download) | Missing answer | Add supporting SEBI/AMFI/AMC URLs to reach 15–25 sources |
| LLM hallucinates a citation | Trust loss | Citation taken only from retrieved metadata; validate URL in context |
| Embedding/DB model mismatch between ingest & retrieve | Bad retrieval | Shared config object + startup assertion |
| Advice question slips through classifier | Compliance | Conservative rules + keyword/few-shot classifier + refusal fallback |
| Model ID `qwen/qwen3.8-27b` invalid/renamed on Groq | Generation fails | Model ID from `.env`; config validation with clear error |
| PII leaked into logs | Privacy breach | Redaction layer before any persistence |

---

## 15. Success Metrics (Demo)

- Factual accuracy on sample set ≥ 90% (correct fact + valid official citation).
- Refusal precision on advice queries = 100% (no advice given).
- Citation validity = 100% (link exists in retrieved source set).
- 100% of queries produce complete, viewable RAG-stage traces.

---

## 16. Open Questions

1. Final Groq model ID (the statement's `qwen/qwen3.8-27b` may be stale) — confirm at implementation.
2. Should the 15–25 source list be **Groww-only** or include SEBI/AMFI factsheet pages? (Assumption: include official SEBI/AMFI for statement/benchmark facts.)
3. UI framework: Streamlit (assumed) vs Gradio — confirm.
4. Is multi-turn memory in scope for the demo, or single-turn only? (Assumption: single-turn + optional session context.)
5. Freshness policy: how often to re-scrape / what "Last updated" cutoff is acceptable.

---

## 17. Assumptions

- Python + Streamlit, local execution, Chroma persistent client.
- Facts like expense ratio/exit load/min SIP/lock-in/riskometer/benchmark are present on the in-scope scheme pages.
- "How to download statement" guidance comes from official AMC/SEBI/AMFI pages added to the source list.
- Groq free-tier key available via `.env`.
