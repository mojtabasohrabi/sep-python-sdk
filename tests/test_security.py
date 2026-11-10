import hashlib
import hmac
from unittest.mock import Mock

import pytest

from sep_sdk import SepValidationError, derive_session_key, generate_session_key, hash_card_number


def test_card_hash_is_upper_md5_of_digits() -> None:
    expected = hashlib.md5(b"6037991234567890", usedforsecurity=False).hexdigest().upper()
    assert hash_card_number("6037 9912-3456 7890") == expected
    assert hash_card_number("۶۰۳۷۹۹۱۲۳۴۵۶۷۸۹۰") == expected


@pytest.mark.parametrize("value", ["123", "abcd" * 4, "6037991234567890123"])
def test_card_hash_needs_sixteen_digits(value: str) -> None:
    with pytest.raises(SepValidationError, match="16 digits"):
        hash_card_number(value)


def test_generated_keys_are_random_decimal_int64_values() -> None:
    first, second = generate_session_key(), generate_session_key()
    assert first != second
    assert first.isascii()
    assert first.isdecimal()
    assert 0 < int(first) < 2**63


def test_derived_keys_are_stable_and_scoped() -> None:
    key = derive_session_key("server-secret", "order-1")
    assert key == derive_session_key(b"server-secret", "order-1")
    assert key != derive_session_key("server-secret", "order-2")
    assert key != derive_session_key("other-secret", "order-1")
    assert key.isascii()
    assert key.isdecimal()
    assert 0 < int(key) < 2**63


def test_a_namespace_preserves_the_existing_application_key() -> None:
    digest = hmac.new(b"server-secret", b"saman-session:order-1", hashlib.sha256).digest()
    expected = str((int.from_bytes(digest[:8], "big") >> 1) or 1)
    assert derive_session_key("server-secret", "order-1", namespace="saman-session") == expected
    assert expected != derive_session_key("server-secret", "order-1")


@pytest.mark.parametrize(("byte", "expected"), [(0, "1"), (255, str(2**63 - 1))])
def test_derived_key_bounds(byte: int, expected: str, monkeypatch: pytest.MonkeyPatch) -> None:
    digest = Mock()
    digest.digest.return_value = bytes([byte]) * 32
    monkeypatch.setattr("sep_sdk.security.hmac.new", Mock(return_value=digest))
    assert derive_session_key("secret", "order") == expected


def test_an_empty_namespace_is_refused() -> None:
    with pytest.raises(SepValidationError, match="namespace"):
        derive_session_key("secret", "order", namespace="")


def test_derived_keys_need_a_secret() -> None:
    with pytest.raises(SepValidationError, match="secret"):
        derive_session_key("", "order-1")
