"""oyu.so services besides the chat model: Anir (speech-to-text) and Orchu (Mongolian ↔ English translation)."""

from app.modules.oyu.client import OyuClient, OyuError, configured_client

__all__ = ["OyuClient", "OyuError", "configured_client"]
