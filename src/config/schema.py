from pydantic import BaseModel, Field
from typing import Literal


class CorpusCfg(BaseModel):
    version: str
    sources_file: str


class EmbeddingCfg(BaseModel):
    model: str
    device: str = "cpu"
    batch_size: int = 32


class VectorDbCfg(BaseModel):
    type: Literal["chroma"] = "chroma"
    persist_dir: str
    collection: str
    distance: Literal["cosine", "l2", "ip"] = "cosine"


class ChunkingCfg(BaseModel):
    strategy: Literal["auto", "section", "recursive", "table"] = "auto"
    chunk_size: int = 800
    chunk_overlap: int = 120


class RetrievalCfg(BaseModel):
    top_k: int = 4


class LLMCfg(BaseModel):
    provider: Literal["groq", "gemini", "openai", "anthropic", "mistral"] = "groq"
    temperature: float = 0.2
    max_tokens: int = 300
    timeout_s: int = 30


class GuardrailsCfg(BaseModel):
    enabled: bool = True
    pii_patterns_file: str


class PathsCfg(BaseModel):
    raw: str
    clean: str
    chunks: str
    embeddings: str
    retrieval: str
    generation: str
    runs: str


class UICfg(BaseModel):
    title: str
    example_questions: list[str] = Field(min_length=1)
    disclaimer: str


class AppConfig(BaseModel):
    corpus: CorpusCfg
    embedding: EmbeddingCfg
    vector_db: VectorDbCfg
    chunking: ChunkingCfg
    retrieval: RetrievalCfg
    llm: LLMCfg
    guardrails: GuardrailsCfg
    paths: PathsCfg
    ui: UICfg
