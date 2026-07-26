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
