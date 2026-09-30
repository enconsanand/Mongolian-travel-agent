"""Minimal compact JWS with exactly one algorithm: ES256 (ECDSA P-256, SHA-256).

Pinning the algorithm here, instead of reading it from the token, rules out ``alg: none`` and HS256-with-a-public-
key attacks. The signature is the raw 64-byte ``r || s`` form (RFC 7518 §3.4), which is also what the browser's
WebCrypto ``ECDSA`` returns, so a mandate the user signs in the browser verifies here unchanged.
"""

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

from app.ap2.errors import MandateError

ALG = "ES256"
_COORD = 32  # bytes per P-256 coordinate / signature half

Json = dict[str, Any]


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (ValueError, TypeError) as exc:
        raise MandateError("malformed", "bad base64url") from exc


def sha256_b64url(text: str) -> str:
    """base64url(SHA-256(ascii bytes)): how AP2 binds a mandate to a checkout JWT, and our mandate id hash."""
    return b64url(hashlib.sha256(text.encode("ascii")).digest())


def _json_segment(value: Json) -> str:
    return b64url(json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8"))


# ----------------------------------------------------------------------------- keys


def generate_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def public_jwk(key: ec.EllipticCurvePrivateKey | ec.EllipticCurvePublicKey, kid: str | None = None) -> Json:
    pub = key.public_key() if isinstance(key, ec.EllipticCurvePrivateKey) else key
    numbers = pub.public_numbers()
    jwk: Json = {
        "kty": "EC",
        "crv": "P-256",
        "x": b64url(numbers.x.to_bytes(_COORD, "big")),
        "y": b64url(numbers.y.to_bytes(_COORD, "big")),
    }
    if kid:
        jwk["kid"] = kid
    return jwk


def load_public_jwk(jwk: Json) -> ec.EllipticCurvePublicKey:
    """Accept only an EC P-256 public key (a JWK carrying ``d`` is a private key sent by mistake: refuse it)."""
    if not isinstance(jwk, dict) or jwk.get("kty") != "EC" or jwk.get("crv") != "P-256" or "d" in jwk:
        raise MandateError("bad_key", "expected an EC P-256 public JWK")
    try:
        x = int.from_bytes(b64url_decode(jwk["x"]), "big")
        y = int.from_bytes(b64url_decode(jwk["y"]), "big")
        return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    except (KeyError, ValueError) as exc:
        raise MandateError("bad_key", "JWK coordinates are missing or not on P-256") from exc


def jwk_thumbprint(jwk: Json) -> str:
    """RFC 7638 thumbprint: a stable key id computed from the key itself."""
    canonical = json.dumps({k: jwk[k] for k in ("crv", "kty", "x", "y")}, separators=(",", ":"), sort_keys=True)
    return sha256_b64url(canonical)


# ----------------------------------------------------------------------------- sign / verify


def sign(payload: Json, key: ec.EllipticCurvePrivateKey, *, kid: str, typ: str) -> str:
    """Compact JWS over ``payload`` with ES256. ECDSA is randomized, so signing twice gives different tokens."""
    signing_input = f"{_json_segment({'alg': ALG, 'kid': kid, 'typ': typ})}.{_json_segment(payload)}"
    r, s = decode_dss_signature(key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256())))
    return f"{signing_input}.{b64url(r.to_bytes(_COORD, 'big') + s.to_bytes(_COORD, 'big'))}"


def decode_unverified(token: str) -> tuple[Json, Json]:
    """Header and payload without checking the signature. Only for picking the key to verify with."""
    parts = token.split(".")
    if len(parts) != 3:
        raise MandateError("malformed", "a compact JWS has three parts")
    try:
        header, payload = (json.loads(b64url_decode(p)) for p in parts[:2])
    except json.JSONDecodeError as exc:
        raise MandateError("malformed", "header or payload is not JSON") from exc
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise MandateError("malformed", "header and payload must be JSON objects")
    return header, payload


def verify(token: str, jwk: Json) -> tuple[Json, Json]:
    """Check an ES256 compact JWS against ``jwk``; return (header, payload)."""
    header, payload = decode_unverified(token)
    if header.get("alg") != ALG:
        raise MandateError("wrong_alg", f"only {ALG} is accepted, got {header.get('alg')!r}")
    signature = b64url_decode(token.rsplit(".", 1)[1])
    if len(signature) != 2 * _COORD:
        raise MandateError("bad_signature", "ES256 signature must be 64 bytes (r || s)")
    der = encode_dss_signature(int.from_bytes(signature[:_COORD], "big"), int.from_bytes(signature[_COORD:], "big"))
    signing_input = token.rsplit(".", 1)[0].encode("ascii")
    try:
        load_public_jwk(jwk).verify(der, signing_input, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise MandateError("bad_signature", "signature does not match the key") from exc
    return header, payload
