"""A small client for oyu's speech and translation endpoints (https://dev.oyu.so/api.html).

One key covers every oyu endpoint; it stays on the server, and the browser reaches these through our own API.
"""

from functools import lru_cache

import httpx

OYU_API = "https://api.oyu.so"
ANIR_MODEL = "v4"


class OyuError(Exception):
    """``code`` is ``not_configured`` (no key), ``unavailable`` (oyu down or slow) or ``refused`` (bad input)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class OyuClient:
    def __init__(self, *, api_key: str, transport: httpx.BaseTransport | None = None, timeout: float = 60.0) -> None:
        self._client = httpx.Client(
            base_url=OYU_API,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )

    def transcribe(self, audio: bytes, *, filename: str, content_type: str) -> str:
        """Anir: Mongolian speech in a WAV, MP3 or OGG file, as text."""
        data = self._post(
            "/v1/audio/transcriptions",
            files={"file": (filename, audio, content_type)},
            data={"model": ANIR_MODEL},
        )
        return str(data.get("text", "")).strip()

    def translate(self, text: str, *, source: str, target: str) -> str:
        """Orchu: Mongolian ↔ English."""
        if not text.strip() or source == target:
            return text
        data = self._post("/v1/translations", json={"text": text, "source": source, "target": target})
        return str(data.get("translation", "")).strip() or text

    def _post(self, path: str, **kwargs) -> dict:
        try:
            resp = self._client.post(path, **kwargs)
        except httpx.HTTPError as exc:
            raise OyuError("unavailable", f"oyu {path}: {exc}") from exc
        if resp.status_code >= 500 or resp.status_code == 429:
            raise OyuError("unavailable", f"oyu {path} {resp.status_code}")
        if resp.status_code >= 400:
            raise OyuError("refused", f"oyu {path} {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()
        except ValueError as exc:
            raise OyuError("unavailable", f"oyu {path}: not JSON") from exc


def configured_client() -> OyuClient:
    """The client for the configured key (a FastAPI dependency; tests override it)."""
    return _configured()


@lru_cache
def _configured() -> OyuClient:
    from app.core.config import settings

    if not settings.OYU_API_KEY:
        raise OyuError("not_configured", "set OYU_API_KEY to use oyu speech and translation")
    return OyuClient(api_key=settings.OYU_API_KEY, timeout=settings.LLM_TIMEOUT_SECONDS)
