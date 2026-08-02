"""Minimal Ollama HTTP client.

Kept tiny and dependency-light on purpose. Raises OllamaUnavailable when the server
can't be reached so callers can fall back to a deterministic explanation.
"""

import httpx


class OllamaUnavailable(RuntimeError):
    pass


class OllamaClient:
    # A biomarker explanation only needs a few sentences. Left unbounded, the model happily
    # writes a couple of paragraphs, and on CPU generation time scales directly with tokens
    # produced - so the cap is most of the difference between a snappy answer and a slow
    # one. Sized with headroom above the ~120-token replies the prompts actually want, so it
    # trims rambling rather than truncating a normal answer mid-sentence.
    DEFAULT_MAX_TOKENS = 220

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b",
                 timeout: float = 120.0, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

    def generate(self, system: str, prompt: str, temperature: float = 0.2,
                 max_tokens: int | None = None) -> str:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or self.max_tokens,
            },
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate", json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            raise OllamaUnavailable(str(exc)) from exc
        return resp.json().get("response", "").strip()

    def is_available(self) -> bool:
        """True only if the server is up AND the configured model is actually present.

        Checking the model matters: a running Ollama with the model not pulled would
        otherwise pass this check, then fail on every single biomarker's generate() call -
        turning one fast up-front check into N slow failures before the caller falls back.
        """
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
        except (httpx.HTTPError, ValueError):
            return False
        # Ollama reports names tag-qualified ("qwen2.5:3b"); accept an untagged config
        # value ("qwen2.5") as matching any tag of that model.
        wanted = self.model
        return any(n == wanted or n.split(":")[0] == wanted.split(":")[0] for n in names)
