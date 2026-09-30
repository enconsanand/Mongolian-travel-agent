"""Why a mandate or checkout was rejected. Codes are stable: they go into ``mandates.reject_reason`` and the API."""

from typing import Literal

RejectCode = Literal[
    "malformed",  # not a compact JWS / SD-JWT, bad base64 or JSON
    "wrong_alg",  # anything but ES256 (blocks alg=none and HS256 key confusion)
    "bad_key",  # the JWK is not an EC P-256 public key
    "bad_signature",
    "wrong_vct",  # not the mandate type this step expects
    "expired",
    "not_yet_valid",
    "hash_mismatch",  # checkout_hash / transaction_id does not match the checkout JWT
    "amount_mismatch",
    "payee_mismatch",
    "constraint_violated",  # a closed mandate outside what its open mandate allows
    "key_not_bound",  # autonomous mode: the closed mandate was not signed by the agent key in the open one
]


class MandateError(ValueError):
    """A checkout JWT or mandate failed verification. ``code`` says why; the message has the detail."""

    def __init__(self, code: RejectCode, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code: RejectCode = code
