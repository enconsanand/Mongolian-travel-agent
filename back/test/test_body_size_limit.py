"""Tests for BodySizeLimitMiddleware: declared Content-Length and chunked bodies."""

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middlewares.body_size_limit import BodySizeLimitMiddleware

LIMIT = 1024


def _make_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_body_size=LIMIT)

    @app.post("/echo")
    async def echo(request: Request) -> dict:
        body = await request.body()
        return {"size": len(body)}

    return TestClient(app)


def test_small_body_allowed():
    client = _make_client()
    response = client.post("/echo", content=b"x" * 10)
    assert response.status_code == 200
    assert response.json() == {"size": 10}


def test_body_at_exact_limit_allowed():
    client = _make_client()
    response = client.post("/echo", content=b"x" * LIMIT)
    assert response.status_code == 200
    assert response.json() == {"size": LIMIT}


def test_declared_content_length_over_limit_rejected():
    client = _make_client()
    response = client.post("/echo", content=b"x" * (LIMIT + 1))
    assert response.status_code == 413


def test_chunked_body_over_limit_rejected():
    # A generator body is sent with Transfer-Encoding: chunked (no Content-Length),
    # which previously bypassed the header-based size check entirely.
    client = _make_client()

    def chunks():
        for _ in range(20):
            yield b"x" * 128  # 2560 bytes total

    response = client.post("/echo", content=chunks())
    assert response.status_code == 413


def test_chunked_body_under_limit_allowed():
    client = _make_client()

    def chunks():
        yield b"x" * 100
        yield b"y" * 100

    response = client.post("/echo", content=chunks())
    assert response.status_code == 200
    assert response.json() == {"size": 200}


def test_full_app_rejects_oversized_chunked_body(client):
    """The real middleware stack rejects a chunked body exceeding the default 10MB cap."""

    def chunks():
        for _ in range(11):
            yield b"x" * (1024 * 1024)  # 11MB total, no Content-Length

    response = client.post(
        "/api/v1/auth/login",
        content=chunks(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 413
