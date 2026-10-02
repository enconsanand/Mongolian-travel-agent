"""oyu speech and translation API (https://dev.oyu.so): Anir STT, tsuurAI TTS, Orchu MT.

One bearer key (``OYU_API_KEY``) covers every endpoint. Without a key ``configured_oyu()`` returns ``None`` and
the HTTP layer answers 503, so the rest of the app runs as before.
"""

import threading
from collections import OrderedDict
from collections.abc import Hashable, Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

import httpx

if TYPE_CHECKING:
    from app.core.config import Settings

OyuErrorCode = Literal["unavailable", "rate_limited", "refused", "bad_response"]
Language = Literal["mn", "en"]

# tsuurAI rejects longer text; callers split before this
TTS_MAX_CHARS = 800
# Orchu takes one text per call; a plan's summary and day notes go out a few at a time
_TRANSLATE_WORKERS = 4


class _Lru:
    """Bounded memo of replies: the same plan read aloud or translated twice spends credit once."""

    def __init__(self, size: int) -> None:
        self._items: OrderedDict[Hashable, object] = OrderedDict()
        self._size = size
        self._lock = threading.Lock()

    def get(self, key: Hashable) -> object | None:
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key: Hashable, value: object) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self._size:
                self._items.popitem(last=False)


class OyuError(Exception):
    def __init__(self, code: OyuErrorCode, message: str = "") -> None:
        super().__init__(message or code)
        self.code: OyuErrorCode = code


class OyuClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.oyu.so",
        voice: str = "mbspeech",
        stt_model: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
            transport=transport,
        )
        self.voice = voice
        self._stt_model = stt_model
        self._audio = _Lru(128)
        self._translations = _Lru(1024)

    def transcribe(self, audio: bytes, *, filename: str = "speech.wav", content_type: str = "audio/wav") -> str:
        """Anir: Mongolian speech (WAV/MP3/OGG) to text."""
        data = {"model": self._stt_model} if self._stt_model else None
        body = self._json(
            self._post("/v1/audio/transcriptions", files={"file": (filename, audio, content_type)}, data=data)
        )
        return _text_field(body, "text")

    def speak(self, text: str, *, voice: str | None = None) -> bytes:
        """tsuurAI: Mongolian text (at most ``TTS_MAX_CHARS``) to WAV audio."""
        if len(text) > TTS_MAX_CHARS:
            raise OyuError("refused", f"text is {len(text)} characters; tsuurAI takes at most {TTS_MAX_CHARS}")
        key = (voice or self.voice, text)
        cached = self._audio.get(key)
        if isinstance(cached, bytes):
            return cached
        response = self._post("/v1/audio/speech", json={"text": text, "voice": key[0]})
        if not response.content:
            raise OyuError("bad_response", "tsuurAI returned no audio")
        self._audio.put(key, response.content)
        return response.content

    def translate(self, text: str, *, source: Language, target: Language) -> str:
        """Orchu: Mongolian ↔ English. Blank text and same-language requests come back unchanged."""
        if source == target or not text.strip():
            return text
        key = (source, target, text)
        cached = self._translations.get(key)
        if isinstance(cached, str):
            return cached
        body = self._json(self._post("/v1/translations", json={"text": text, "source": source, "target": target}))
        translation = _text_field(body, "translation")
        self._translations.put(key, translation)
        return translation

    def translate_many(self, texts: Sequence[str], *, source: Language, target: Language) -> list[str]:
        """Each text on its own call, in order; any failure fails the whole batch."""
        with ThreadPoolExecutor(max_workers=_TRANSLATE_WORKERS) as pool:
            return list(pool.map(lambda text: self.translate(text, source=source, target=target), texts))

    def _post(self, path: str, **kwargs) -> httpx.Response:
        try:
            response = self._client.post(path, **kwargs)
        except httpx.HTTPError as exc:
            raise OyuError("unavailable", f"{path}: {exc.__class__.__name__}") from exc
        if response.status_code == 429:
            raise OyuError("rate_limited", f"{path}: 429")
        if response.status_code >= 500:
            raise OyuError("unavailable", f"{path}: {response.status_code}")
        if response.status_code >= 400:
            raise OyuError("refused", f"{path}: {response.status_code} {response.text[:200]}")
        return response

    @staticmethod
    def _json(response: httpx.Response) -> dict:
        try:
            body = response.json()
        except ValueError as exc:
            raise OyuError("bad_response", "reply is not JSON") from exc
        if not isinstance(body, dict):
            raise OyuError("bad_response", "reply is not a JSON object")
        return body


def _text_field(body: dict, field: str) -> str:
    value = body.get(field)
    if not isinstance(value, str):
        raise OyuError("bad_response", f"reply has no {field!r} string")
    return value.strip()


def build_oyu(settings: "Settings") -> OyuClient | None:
    if not settings.OYU_API_KEY:
        return None
    return OyuClient(
        api_key=settings.OYU_API_KEY,
        base_url=settings.OYU_BASE_URL,
        voice=settings.OYU_TTS_VOICE,
        stt_model=settings.OYU_STT_MODEL,
        timeout=settings.OYU_TIMEOUT_SECONDS,
    )


def configured_oyu() -> OyuClient | None:
    """The client chosen by settings, or ``None`` without a key (a FastAPI dependency; tests override it)."""
    return _configured()


@lru_cache
def _configured() -> OyuClient | None:
    from app.core.config import settings

    return build_oyu(settings)
