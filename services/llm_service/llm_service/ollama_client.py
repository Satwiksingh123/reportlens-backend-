"""Minimal Ollama HTTP client.

Kept tiny and dependency-light on purpose. Raises OllamaUnavailable when the server
can't be reached so callers can fall back to a deterministic explanation.
"""

import httpx


class OllamaUnavailable(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b",
                 timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, system: str, prompt: str, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
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
        try:
            httpx.get(f"{self.base_url}/api/tags", timeout=2.0).raise_for_status()
            return True
        except httpx.HTTPError:
            return False
