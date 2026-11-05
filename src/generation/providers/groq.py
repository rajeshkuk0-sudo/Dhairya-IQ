import os

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.8-27b"


class ProviderError(RuntimeError):
    """Raised when the LLM provider cannot return a usable response."""


class GroqProvider:
    def __init__(self, cfg):
        self.cfg = cfg
        self.model = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    def complete(self, system: str, user: str) -> str:
        key = os.getenv("GROQ_API_KEY", "").strip()
        if not key:
            raise ProviderError("GROQ_API_KEY missing in .env")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.cfg.llm.temperature,
            "max_tokens": self.cfg.llm.max_tokens,
        }

        try:
            response = httpx.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.cfg.llm.timeout_s,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"Groq request failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            raise ProviderError(f"Groq returned HTTP {response.status_code}")

        try:
            return response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Groq returned an unexpected response") from exc
