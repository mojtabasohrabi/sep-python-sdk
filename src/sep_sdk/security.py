"""Helpers for the two values the guide asks you to handle carefully."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from sep_sdk.errors import SepValidationError
from sep_sdk.validation import require_text, to_ascii_digits

_CARD_PATTERN = re.compile(r"\d{16}")


def hash_card_number(card_number: str) -> str:
    """The MD5 digest (upper-case hex) Saman expects in ``allowed_cards``.

    The guide requires an *irreversible* hash and forbids storing the card number.
    This function never logs or stores its input; call it, keep only the digest.
    MD5 is mandated by the protocol, not chosen here.
    """
    digits = to_ascii_digits(re.sub(r"[\s-]", "", require_text("card_number", card_number)))
    if _CARD_PATTERN.fullmatch(digits) is None:
        raise SepValidationError("card_number must be 16 digits.")
    return hashlib.md5(digits.encode("ascii"), usedforsecurity=False).hexdigest().upper()


def generate_session_key() -> str:
    """A fresh random ``TxnRandomSessionKey`` (32 hex characters).

    Store it with the order, pass it as ``session_key`` when you create the token,
    and again when you verify. Saman then refuses a receipt that was not issued for
    that session, so one customer's receipt cannot be replayed on another order.
    """
    return secrets.token_hex(16)


def derive_session_key(secret: str | bytes, res_num: str) -> str:
    """A ``TxnRandomSessionKey`` computed from a server secret and the order id.

    Use this instead of :func:`generate_session_key` when you would rather not
    store a key per order: recompute it at verify time from the same two inputs.
    Rotating ``secret`` between token and verify makes that payment unverifiable.
    """
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not key:
        raise SepValidationError("secret must not be empty.")
    message = f"sep-session:{require_text('res_num', res_num)}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()[:32]
