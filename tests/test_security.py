import hashlib

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


def test_generated_keys_are_random_hex() -> None:
    first, second = generate_session_key(), generate_session_key()
    assert first != second
    assert len(first) == 32
    int(first, 16)


def test_derived_keys_are_stable_and_scoped() -> None:
    key = derive_session_key("server-secret", "order-1")
    assert key == derive_session_key(b"server-secret", "order-1")
    assert key != derive_session_key("server-secret", "order-2")
    assert key != derive_session_key("other-secret", "order-1")
    assert len(key) == 32


def test_derived_keys_need_a_secret() -> None:
    with pytest.raises(SepValidationError, match="secret"):
        derive_session_key("", "order-1")
