"""Strip contact and card details from what users and tools send to an external model.

Bookings never need them in a prompt: contacts are revealed by the booking flow after payment, and payment
details never pass through the model at all.
"""

import re
from dataclasses import replace

from app.llm.types import Message

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
# Mongolian numbers: 8 digits starting 5-9, optional +976 prefix
_PHONE = re.compile(r"(?<!\d)(?:\+?976[ -]?)?[5-9]\d{3}[ -]?\d{4}(?!\d)")


def redact(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _CARD.sub("[number]", text)
    return _PHONE.sub("[phone]", text)


def redact_message(message: Message) -> Message:
    if message.role in ("user", "tool") and message.content:
        return replace(message, content=redact(message.content))
    return message
