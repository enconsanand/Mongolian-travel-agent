"""oyu speech and translation: the client's wire format and error mapping, and the HTTP endpoints over it."""

import json

import httpx
import pytest

from app.main import app
from app.oyu import OyuClient, OyuError, configured_oyu

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt "


class Recorder:
    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def oyu(recorder: Recorder, **kwargs) -> OyuClient:
    return OyuClient(api_key="oyu_test", transport=httpx.MockTransport(recorder), **kwargs)


@pytest.fixture
def use_oyu():
    def install(client: OyuClient | None) -> None:
        app.dependency_overrides[configured_oyu] = lambda: client

    yield install
    app.dependency_overrides.pop(configured_oyu, None)


# --- client ---


def test_transcribe_uploads_multipart_with_the_key():
    rec = Recorder(httpx.Response(200, json={"text": " Хөвсгөл рүү 3 хоног "}))
    text = oyu(rec, stt_model="v4").transcribe(WAV)

    req = rec.requests[0]
    assert str(req.url) == "https://api.oyu.so/v1/audio/transcriptions"
    assert req.headers["authorization"] == "Bearer oyu_test"
    assert req.headers["content-type"].startswith("multipart/form-data")
    assert WAV in req.content and b'name="model"' in req.content
    assert text == "Хөвсгөл рүү 3 хоног"


def test_speak_posts_text_and_voice_and_memoizes():
    rec = Recorder(httpx.Response(200, content=b"wav-bytes"))
    client = oyu(rec)

    assert client.speak("Сайн байна уу") == b"wav-bytes"
    assert client.speak("Сайн байна уу") == b"wav-bytes"
    assert len(rec.requests) == 1
    assert json.loads(rec.requests[0].content) == {"text": "Сайн байна уу", "voice": "mbspeech"}


def test_speak_refuses_text_over_the_tsuurai_limit_without_calling():
    rec = Recorder()
    with pytest.raises(OyuError) as err:
        oyu(rec).speak("а" * 801)
    assert err.value.code == "refused"
    assert rec.requests == []


def test_translate_many_keeps_order_and_skips_blank_and_same_language():
    def reply(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(200, json={"translation": f"EN:{body['text']}"})

    client = OyuClient(api_key="k", transport=httpx.MockTransport(reply))
    assert client.translate_many(["нэг", "", "хоёр"], source="mn", target="en") == ["EN:нэг", "", "EN:хоёр"]
    assert client.translate("same", source="en", target="en") == "same"


@pytest.mark.parametrize(
    ("response", "code"),
    [
        (httpx.Response(429), "rate_limited"),
        (httpx.Response(503), "unavailable"),
        (httpx.Response(400, text="bad"), "refused"),
        (httpx.Response(200, json={"other": 1}), "bad_response"),
        (httpx.ConnectTimeout("slow"), "unavailable"),
    ],
)
def test_errors_are_mapped(response, code):
    with pytest.raises(OyuError) as err:
        oyu(Recorder(response)).translate("сайн", source="mn", target="en")
    assert err.value.code == code


# --- HTTP ---


def test_endpoints_answer_503_without_a_key(client, use_oyu):
    use_oyu(None)
    response = client.post("/api/v1/translate", json={"texts": ["сайн"], "source": "mn", "target": "en"})
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "oyu_not_configured"


def test_transcribe_endpoint_returns_text(client, use_oyu):
    use_oyu(oyu(Recorder(httpx.Response(200, json={"text": "Говь руу явмаар байна"}))))
    response = client.post("/api/v1/voice/transcribe", files={"file": ("speech.wav", WAV, "audio/wav")})
    assert response.status_code == 200
    assert response.json() == {"text": "Говь руу явмаар байна"}


def test_transcribe_rejects_other_media(client, use_oyu):
    use_oyu(oyu(Recorder()))
    response = client.post("/api/v1/voice/transcribe", files={"file": ("a.webm", b"x", "audio/webm")})
    assert response.status_code == 415


def test_speak_endpoint_returns_wav(client, use_oyu):
    use_oyu(oyu(Recorder(httpx.Response(200, content=b"wav-bytes"))))
    response = client.post("/api/v1/voice/speak", json={"text": "Сайн байна уу"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == b"wav-bytes"


def test_upstream_rate_limit_is_passed_on(client, use_oyu):
    use_oyu(oyu(Recorder(httpx.Response(429))))
    response = client.post("/api/v1/voice/speak", json={"text": "Сайн"})
    assert response.status_code == 429
    assert response.json()["detail"]["code"] == "oyu_rate_limited"


def test_translate_endpoint(client, use_oyu):
    use_oyu(oyu(Recorder(httpx.Response(200, json={"translation": "A 3-day trip"}))))
    response = client.post("/api/v1/translate", json={"texts": ["3 өдрийн аялал"], "source": "mn", "target": "en"})
    assert response.status_code == 200
    assert response.json() == {"texts": ["A 3-day trip"]}
