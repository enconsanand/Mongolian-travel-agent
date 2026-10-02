"""Speech and translation through oyu: Anir turns Mongolian speech into text for the trip chat, Orchu translates.

The oyu key stays on the server; the page sends its recording or text here.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.modules.oyu import OyuClient, OyuError, configured_client

router = APIRouter()

MAX_AUDIO_BYTES = 8 * 1024 * 1024
AUDIO_TYPES = {"audio/wav", "audio/x-wav", "audio/wave", "audio/mpeg", "audio/mp3", "audio/ogg"}


def _client() -> OyuClient:
    try:
        return configured_client()
    except OyuError as exc:
        raise _error(exc) from exc


Oyu = Annotated[OyuClient, Depends(_client)]


def _error(exc: OyuError) -> HTTPException:
    code = {
        "not_configured": status.HTTP_503_SERVICE_UNAVAILABLE,
        "unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
        "refused": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(exc.code, status.HTTP_503_SERVICE_UNAVAILABLE)
    return HTTPException(code, detail={"code": exc.code})


class TranslationIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    source: Literal["mn", "en"]
    target: Literal["mn", "en"]


@router.post("/speech/transcriptions", tags=["Speech"])
def transcribe(oyu: Oyu, file: Annotated[UploadFile, File()]) -> dict[str, str]:
    """Anir: a short Mongolian recording (WAV, MP3 or OGG) as text."""
    content_type = (file.content_type or "").split(";")[0].strip()
    if content_type not in AUDIO_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail={"code": "unsupported_audio"})
    audio = file.file.read(MAX_AUDIO_BYTES + 1)
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail={"code": "audio_too_long"})
    try:
        text = oyu.transcribe(audio, filename=file.filename or "speech.wav", content_type=content_type)
    except OyuError as exc:
        raise _error(exc) from exc
    return {"text": text}


@router.post("/translations", tags=["Speech"])
def translate(body: TranslationIn, oyu: Oyu) -> dict[str, str]:
    """Orchu: Mongolian ↔ English."""
    try:
        return {"translation": oyu.translate(body.text, source=body.source, target=body.target)}
    except OyuError as exc:
        raise _error(exc) from exc
