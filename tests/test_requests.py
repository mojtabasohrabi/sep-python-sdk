import pytest

from sep_sdk import (
    NO_PURCHASE_ID,
    SepValidationError,
    SettlementItem,
    TokenRequest,
    hash_card_number,
)

CALLBACK = "https://shop.example/callback"
IBAN_A = "IR062960000000100324200001"
IBAN_B = "IR" + "2" * 24
GOV_ID = "1" * 30


def request(**overrides: object) -> TokenRequest:
    fields: dict[str, object] = {"amount": 12_000, "res_num": "order-1", "redirect_url": CALLBACK}
    fields.update(overrides)
    return TokenRequest(**fields)  # type: ignore[arg-type]


def test_minimal_payload_matches_the_guide() -> None:
    assert request().to_payload("0000") == {
        "action": "token",
        "TerminalId": "0000",
        "Amount": 12_000,
        "ResNum": "order-1",
        "RedirectUrl": CALLBACK,
    }


def test_optional_fields_are_named_as_in_the_guide() -> None:
    cards = [hash_card_number("6037991234567890"), hash_card_number("6219861234567890")]
    payload = request(
        wage=500,
        cell_number="09120000000",
        token_expiry_minutes=60,
        allowed_cards=cards,
        extra_data=["a", "b"],
        session_key="key-1",
    ).to_payload("0000")
    assert payload["Wage"] == 500
    assert payload["CellNumber"] == "9120000000"
    assert payload["TokenExpiryInMin"] == 60
    assert payload["HashedCardNumber"] == "|".join(cards)
    assert (payload["ResNum1"], payload["ResNum2"]) == ("a", "b")
    assert payload["TxnRandomSessionKey"] == "key-1"
    assert "TranType" not in payload


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": 0},
        {"amount": True},
        {"amount": 10.5},
        {"res_num": ""},
        {"redirect_url": "not-a-url"},
        {"redirect_url": "https://a.test/" + "x" * 2100},
        {"wage": -1},
        {"cell_number": "12"},
        {"token_expiry_minutes": 19},
        {"token_expiry_minutes": 3601},
        {"session_key": ""},
        {"allowed_cards": "abc"},
        {"allowed_cards": ["not-a-hash"]},
        {"allowed_cards": ["A" * 32] * 11},
        {"extra_data": "abc"},
        {"extra_data": ["x" * 51]},
        {"extra_data": ["a"] * 5},
        {"settlement": "abc"},
        {"settlement": [{"iban": IBAN_A, "amount": 1}]},
        {"callback_method": "PUT"},
    ],
)
def test_invalid_requests_are_refused_locally(overrides: dict[str, object]) -> None:
    with pytest.raises(SepValidationError):
        request(**overrides)


def test_get_callbacks_have_a_shorter_url_limit() -> None:
    long_url = "https://shop.example/" + "x" * 1600
    assert request(redirect_url=long_url).redirect_url == long_url
    with pytest.raises(SepValidationError, match="at most 1538"):
        request(redirect_url=long_url, callback_method="GET")


def test_multi_settle_payload() -> None:
    lines = [SettlementItem(iban=IBAN_A, amount=7_000), SettlementItem(iban=IBAN_B, amount=5_000)]
    payload = request(settlement=lines).to_payload("0000")
    assert payload["SettlementIbanInfo"] == [
        {"IBAN": IBAN_A, "Amount": 7_000},
        {"IBAN": IBAN_B, "Amount": 5_000},
    ]
    assert "TranType" not in payload


def test_multi_settle_keeps_explicit_purchase_ids() -> None:
    line = SettlementItem(iban=IBAN_A, amount=12_000, purchase_id=GOV_ID)
    payload = request(settlement=[line]).to_payload("0000")
    assert payload["SettlementIbanInfo"][0]["PurchaseId"] == GOV_ID


def test_government_payload_pads_ordinary_lines_with_zeros() -> None:
    lines = [
        SettlementItem(iban=IBAN_A, amount=7_000, purchase_id=GOV_ID),
        SettlementItem(iban=IBAN_B, amount=5_000),
    ]
    payload = request(settlement=lines, government=True).to_payload("0000")
    assert payload["TranType"] == "Government"
    assert [line["PurchaseId"] for line in payload["SettlementIbanInfo"]] == [
        GOV_ID,
        NO_PURCHASE_ID,
    ]


def test_government_payment_rules() -> None:
    with pytest.raises(SepValidationError, match="at least one"):
        request(government=True)
    with pytest.raises(SepValidationError, match="first settlement line"):
        request(government=True, settlement=[SettlementItem(iban=IBAN_A, amount=1)])
    with pytest.raises(SepValidationError, match="first settlement line"):
        request(
            government=True,
            settlement=[SettlementItem(iban=IBAN_A, amount=1, purchase_id=NO_PURCHASE_ID)],
        )


def test_settlement_is_limited_to_nine_lines() -> None:
    lines = [SettlementItem(iban=IBAN_A, amount=1)] * 10
    with pytest.raises(SepValidationError, match="at most 9"):
        request(settlement=lines)


@pytest.mark.parametrize(
    "fields",
    [
        {"iban": "nope", "amount": 1},
        {"iban": IBAN_A, "amount": 0},
        {"iban": IBAN_A, "amount": 1, "purchase_id": "123"},
        {"iban": IBAN_A, "amount": 1, "purchase_id": "x" * 30},
    ],
)
def test_settlement_item_validation(fields: dict[str, object]) -> None:
    with pytest.raises(SepValidationError):
        SettlementItem(**fields)  # type: ignore[arg-type]


def test_purchase_id_accepts_persian_digits() -> None:
    item = SettlementItem(iban=IBAN_A, amount=1, purchase_id="۱" * 30)
    assert item.purchase_id == "1" * 30


def test_requests_are_immutable() -> None:
    with pytest.raises(AttributeError):
        request().amount = 5  # type: ignore[misc]
