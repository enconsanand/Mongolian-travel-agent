"""Booking: holds, the merchant-signed checkout and the saga that books every night or none.

Deterministic, no LLM. Acts as the AP2 Merchant: signs ``checkout_jwt`` and verifies the Checkout Mandate.
"""
