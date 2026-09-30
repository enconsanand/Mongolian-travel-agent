"""The platform's merchant signing key (it signs every checkout as merchant of record).

Set ``MERCHANT_KEY_PEM`` (a PKCS#8 EC P-256 private key) in any shared environment. In local development without
it, a key is generated per process: fine for demos, but checkouts signed before a restart stop verifying.
"""

import logging
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app import ap2
from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def merchant_key() -> ec.EllipticCurvePrivateKey:
    if settings.MERCHANT_KEY_PEM:
        key = serialization.load_pem_private_key(settings.MERCHANT_KEY_PEM.encode(), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
            raise ValueError("MERCHANT_KEY_PEM must be an EC P-256 private key")
        return key
    logger.warning("MERCHANT_KEY_PEM is not set: using a throwaway merchant key for this process")
    return ap2.generate_key()


def merchant_kid() -> str:
    return ap2.jwk_thumbprint(ap2.public_jwk(merchant_key()))


def merchant_public_jwk() -> dict:
    return ap2.public_jwk(merchant_key(), merchant_kid())
