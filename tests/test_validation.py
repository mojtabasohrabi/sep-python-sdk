import pytest

from sep_sdk import SepValidationError, iban_checksum_ok
from sep_sdk.validation import (
    normalize_card_hash,
    normalize_cell_number,
    normalize_iban,
    require_http_url,
    require_int,
    require_text,
    to_ascii_digits,
)

VALID_IBAN = "IR062960000000100324200001"


def test_digits_are_translated() -> None:
    assert to_ascii_digits("۰۹۱۲٣") == "09123"


@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_require_int_rejects_non_integers(value: object) -> None:
    with pytest.raises(SepValidationError, match="integer"):
        require_int("n", value)


def test_require_int_bounds() -> None:
    assert require_int("n", 5, minimum=1, maximum=5) == 5
    with pytest.raises(SepValidationError, match="at least"):
        require_int("n", 0, minimum=1)
    with pytest.raises(SepValidationError, match="at most"):
        require_int("n", 6, maximum=5)


@pytest.mark.parametrize(
    ("value", "message"),
    [(5, "string"), ("   ", "empty"), ("a\nb", "control"), ("abcdef", "at most")],
)
def test_require_text_rejections(value: object, message: str) -> None:
    with pytest.raises(SepValidationError, match=message):
        require_text("t", value, max_length=5)


def test_require_text_accepts_plain_text() -> None:
    assert require_text("t", "abc", max_length=5) == "abc"


@pytest.mark.parametrize(
    "url", ["ftp://x.test/a", "https:///nohost", "/relative", "https://a.test/a b"]
)
def test_require_http_url_rejects(url: str) -> None:
    with pytest.raises(SepValidationError, match="absolute"):
        require_http_url("u", url, max_length=100)


def test_require_http_url_accepts_and_bounds() -> None:
    assert require_http_url("u", "http://a.test/x", max_length=100)
    with pytest.raises(SepValidationError, match="at most"):
        require_http_url("u", "https://a.test/" + "x" * 100, max_length=50)


@pytest.mark.parametrize(
    "value",
    [
        "09123456789",
        "9123456789",
        "+989123456789",
        "00989123456789",
        "0912 345-6789",
        "۰۹۱۲۳۴۵۶۷۸۹",
        9123456789,
    ],
)
def test_cell_numbers_are_normalized(value: str | int) -> None:
    assert normalize_cell_number(value) == "9123456789"


@pytest.mark.parametrize("value", ["12345", "08123456789", True, 1.5, None, "abc"])
def test_bad_cell_numbers(value: object) -> None:
    with pytest.raises(SepValidationError):
        normalize_cell_number(value)


def test_iban_normalization_and_checksum() -> None:
    assert normalize_iban(" ir06 2960 0000 0010 0324 2000 01 ") == VALID_IBAN
    assert iban_checksum_ok(VALID_IBAN)
    assert not iban_checksum_ok("IR" + "1" * 24)
    for bad in ("DE89370400440532013000", "IR123", 5):
        with pytest.raises(SepValidationError):
            normalize_iban(bad)


def test_card_hash_normalization() -> None:
    assert (
        normalize_card_hash("ba0206cadcab97f06aae34ad3fdf1168")
        == "BA0206CADCAB97F06AAE34AD3FDF1168"
    )
    with pytest.raises(SepValidationError, match="MD5"):
        normalize_card_hash("6037991234567890")
