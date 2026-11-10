"""Small, strict validators used by the request models.

Everything raises :class:`SepValidationError` with a message naming the field, so
a mistake is reported at construction time rather than as a vague gateway error.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from sep_sdk.constants import MAX_SESSION_KEY
from sep_sdk.errors import SepValidationError

_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_CELL_PATTERN = re.compile(r"(?:\+98|0098|98|0)?(9\d{9})")
_IBAN_PATTERN = re.compile(r"IR\d{24}")
_HEX32_PATTERN = re.compile(r"[0-9A-Fa-f]{32}")
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


def to_ascii_digits(value: str) -> str:
    """Replace Persian and Arabic-Indic digits with ASCII digits."""
    return value.translate(_DIGIT_TRANSLATION)


def require_int(
    name: str, value: object, *, minimum: int | None = None, maximum: int | None = None
) -> int:
    """An ``int`` (``bool`` is refused) inside optional bounds."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise SepValidationError(f"{name} must be an integer, got {type(value).__name__}.")
    if minimum is not None and value < minimum:
        raise SepValidationError(f"{name} must be at least {minimum}, got {value}.")
    if maximum is not None and value > maximum:
        raise SepValidationError(f"{name} must be at most {maximum}, got {value}.")
    return value


def require_text(name: str, value: object, *, max_length: int | None = None) -> str:
    """A non-empty string without control characters."""
    if not isinstance(value, str):
        raise SepValidationError(f"{name} must be a string, got {type(value).__name__}.")
    if not value.strip():
        raise SepValidationError(f"{name} must not be empty.")
    if _CONTROL_CHARACTERS.search(value):
        raise SepValidationError(f"{name} must not contain control characters.")
    if max_length is not None and len(value) > max_length:
        raise SepValidationError(f"{name} must be at most {max_length} characters.")
    return value


def normalize_session_key(value: object) -> int:
    """SEP expects a positive Int64; decimal text is accepted by the Python API."""
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,19}", value):
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= MAX_SESSION_KEY:
        raise SepValidationError("session_key must be a positive signed 64-bit integer.")
    return value


def require_http_url(name: str, value: object, *, max_length: int) -> str:
    """An ``http(s)`` URL with a host, no whitespace and a bounded length."""
    url = require_text(name, value, max_length=max_length)
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname or any(c.isspace() for c in url):
        raise SepValidationError(f"{name} must be an absolute http(s) URL.")
    return url


def normalize_cell_number(value: object) -> str:
    """An Iranian mobile number in the ``9xxxxxxxxx`` form the guide's examples use.

    Accepts ``09123456789``, ``+989123456789``, ``9123456789`` and Persian digits.
    """
    if isinstance(value, bool) or not isinstance(value, str | int):
        raise SepValidationError("cell_number must be a string or an integer.")
    cleaned = to_ascii_digits(re.sub(r"[\s-]", "", str(value)))
    match = _CELL_PATTERN.fullmatch(cleaned)
    if match is None:
        raise SepValidationError("cell_number must be an Iranian mobile number.")
    return match.group(1)


def normalize_iban(value: object) -> str:
    """An Iranian IBAN (``IR`` + 24 digits), upper-cased and without spaces."""
    text = require_text("iban", value).replace(" ", "").upper()
    if _IBAN_PATTERN.fullmatch(text) is None:
        raise SepValidationError("iban must look like IR followed by 24 digits.")
    return text


def iban_checksum_ok(iban: str) -> bool:
    """ISO 13616 mod-97 check. Exposed for callers who want it; not enforced."""
    text = normalize_iban(iban)
    rearranged = text[4:] + text[:4]
    numeric = "".join(str(int(char, 36)) for char in rearranged)
    return int(numeric) % 97 == 1


def normalize_card_hash(value: object) -> str:
    """A 32-character MD5 hex digest, upper-cased."""
    text = require_text("allowed_cards item", value)
    if _HEX32_PATTERN.fullmatch(text) is None:
        raise SepValidationError(
            "allowed_cards items must be MD5 hashes (32 hex characters); "
            "use sep_sdk.hash_card_number() to create them."
        )
    return text.upper()
