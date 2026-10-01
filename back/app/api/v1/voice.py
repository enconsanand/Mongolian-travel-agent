"""Voice and translation through oyu: speak a trip request, hear a plan read aloud, read a plan in the other language.

The browser never sees the oyu key: it sends audio or text here and gets text or WAV back. Without
``OYU_API_KEY`` every endpoint answers 503 ``oyu_not_configured``.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field, model_validator

from app.oyu import TTS_MAX_CHARS, OyuClient, OyuError, configured_oyu

router = APIRouter()

# The body-size middleware caps the request at 10 MB; a spoken trip request is a few hundred KB
MAX_AUDIO_BYTES = 8 * 1024 * 1024
_AUDIO_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3", "audio/ogg"}

_ERROR_STATUS = {
    "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
    "refused": status.HTTP_422_UNPROCESSABLE_CONTENT,
    "unavailable": status.HTTP_502_BAD_GATEWAY,
    "bad_response": status.HTTP_502_BAD_GATEWAY,
}


def _oyu(client: Annotated[OyuClient | None, Depends(configured_oyu)]) -> OyuClient:
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "oyu_not_configured"})
    return client


Oyu = Annotated[OyuClient, Depends(_oyu)]


def _failed(exc: OyuError) -> HTTPException:
    return HTTPException(_ERROR_STATUS[exc.code], detail={"code": f"oyu_{exc.code}"})


class TranscriptOut(BaseModel):
    text: str


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=TTS_MAX_CHARS)


class TranslateIn(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=40)
    source: Literal["mn", "en"]
    target: Literal["mn", "en"]

    @model_validator(mode="after")
    def _short_texts(self) -> "TranslateIn":
        if any(len(text) > 2000 for text in self.texts):
            raise ValueError("each text must be at most 2000 characters")
        return self


class TranslateOut(BaseModel):
    texts: list[str]


@router.post("/voice/transcribe", tags=["Voice"])
def transcribe(file: UploadFile, oyu: Oyu) -> TranscriptOut:
    """Anir: a spoken trip request (WAV, MP3 or OGG) as Mongolian text."""
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _AUDIO_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail={"code": "unsupported_audio"})
    audio = file.file.read(MAX_AUDIO_BYTES + 1)
    if not audio:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail={"code": "empty_audio"})
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail={"code": "audio_too_large"})
    try:
        text = oyu.transcribe(audio, filename=file.filename or "speech.wav", content_type=content_type)
    except OyuError as exc:
        raise _failed(exc) from exc
    return TranscriptOut(text=text)


@router.post("/voice/speak", tags=["Voice"], response_class=Response)
def speak(body: SpeakIn, oyu: Oyu) -> Response:
    """tsuurAI: Mongolian text read aloud, as WAV. Longer text is split by the caller."""
    try:
        audio = oyu.speak(body.text.strip())
    except OyuError as exc:
        raise _failed(exc) from exc
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "private, max-age=86400"})


@router.post("/translate", tags=["Voice"])
def translate(body: TranslateIn, oyu: Oyu) -> TranslateOut:
    """Orchu: texts in one language, in the same order, in the other."""
    try:
        return TranslateOut(texts=oyu.translate_many(body.texts, source=body.source, target=body.target))
    except OyuError as exc:
        raise _failed(exc) from exc
