"""What you send to the gateway: the token request and its settlement lines."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from sep_sdk.constants import (
    MAX_ALLOWED_CARDS,
    MAX_EXTRA_DATA_ITEMS,
    MAX_EXTRA_DATA_LENGTH,
    MAX_REDIRECT_URL_LENGTH,
    MAX_REDIRECT_URL_LENGTH_GET,
    MAX_SETTLEMENT_ITEMS,
    MAX_TOKEN_EXPIRY_MINUTES,
    MIN_TOKEN_EXPIRY_MINUTES,
    NO_PURCHASE_ID,
    PURCHASE_ID_LENGTH,
)
from sep_sdk.errors import SepValidationError
from sep_sdk.validation import (
    normalize_card_hash,
    normalize_cell_number,
    normalize_iban,
    require_http_url,
    require_int,
    require_text,
    to_ascii_digits,
)

CallbackMethod = Literal["POST", "GET"]


@dataclass(frozen=True, slots=True, kw_only=True)
class SettlementItem:
    """One destination of a multi-account (``MultiSettle``) or government payment.

    ``purchase_id`` is the 30-digit government identifier. Leave it ``None`` for an
    ordinary line; in a government request it is filled with thirty zeros for you.
    """

    iban: str
    amount: int
    purchase_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "iban", normalize_iban(self.iban))
        require_int("settlement amount", self.amount, minimum=1)
        if self.purchase_id is not None:
            digits = to_ascii_digits(require_text("purchase_id", self.purchase_id))
            if len(digits) != PURCHASE_ID_LENGTH or not digits.isdigit():
                raise SepValidationError(f"purchase_id must be {PURCHASE_ID_LENGTH} digits.")
            object.__setattr__(self, "purchase_id", digits)


@dataclass(frozen=True, slots=True, kw_only=True)
class TokenRequest:
    """Everything the guide lets you send when asking for a payment token.

    Required: ``amount`` (rials), ``res_num`` (your unique order id) and
    ``redirect_url`` (your callback). Everything else is optional.

    ``amount`` is in **rials** and an integer. ``res_num`` should be unique per
    attempt: it is the only handle you will have if the customer paid and your
    server never heard back.
    """

    amount: int
    res_num: str
    redirect_url: str
    wage: int | None = None
    cell_number: str | int | None = None
    token_expiry_minutes: int | None = None
    #: MD5 digests (see :func:`sep_sdk.hash_card_number`) of the only cards allowed to pay.
    allowed_cards: Sequence[str] = ()
    #: Up to four free-form strings (50 chars each), visible only in Saman's report panel.
    extra_data: Sequence[str] = ()
    #: ``TxnRandomSessionKey``: ties the later verify call to this payment.
    session_key: str | None = None
    #: Multi-account settlement lines (at most nine).
    settlement: Sequence[SettlementItem] = ()
    #: A government purchase: the first settlement line must carry the government IBAN
    #: and its 30-digit purchase id. Requires the terminal to be enabled for it.
    government: bool = False
    #: How Saman returns the customer: ``POST`` (default) or ``GET`` with a query string.
    callback_method: CallbackMethod = "POST"

    def __post_init__(self) -> None:
        require_int("amount", self.amount, minimum=1)
        require_text("res_num", self.res_num)
        limit = (
            MAX_REDIRECT_URL_LENGTH_GET
            if self.callback_method == "GET"
            else MAX_REDIRECT_URL_LENGTH
        )
        require_http_url("redirect_url", self.redirect_url, max_length=limit)
        if self.callback_method not in {"POST", "GET"}:
            raise SepValidationError("callback_method must be 'POST' or 'GET'.")
        if self.wage is not None:
            require_int("wage", self.wage, minimum=0)
        if self.cell_number is not None:
            object.__setattr__(self, "cell_number", normalize_cell_number(self.cell_number))
        if self.token_expiry_minutes is not None:
            require_int(
                "token_expiry_minutes",
                self.token_expiry_minutes,
                minimum=MIN_TOKEN_EXPIRY_MINUTES,
                maximum=MAX_TOKEN_EXPIRY_MINUTES,
            )
        if self.session_key is not None:
            require_text("session_key", self.session_key)
        self._normalize_cards()
        self._normalize_extra_data()
        self._normalize_settlement()

    def _normalize_cards(self) -> None:
        cards = tuple(
            normalize_card_hash(card) for card in _as_sequence("allowed_cards", self.allowed_cards)
        )
        if len(cards) > MAX_ALLOWED_CARDS:
            raise SepValidationError(f"allowed_cards accepts at most {MAX_ALLOWED_CARDS} cards.")
        object.__setattr__(self, "allowed_cards", cards)

    def _normalize_extra_data(self) -> None:
        extra = tuple(
            require_text("extra_data item", item, max_length=MAX_EXTRA_DATA_LENGTH)
            for item in _as_sequence("extra_data", self.extra_data)
        )
        if len(extra) > MAX_EXTRA_DATA_ITEMS:
            raise SepValidationError(f"extra_data accepts at most {MAX_EXTRA_DATA_ITEMS} items.")
        object.__setattr__(self, "extra_data", extra)

    def _normalize_settlement(self) -> None:
        lines = tuple(_as_sequence("settlement", self.settlement))
        if len(lines) > MAX_SETTLEMENT_ITEMS:
            raise SepValidationError(f"settlement accepts at most {MAX_SETTLEMENT_ITEMS} lines.")
        if not all(isinstance(line, SettlementItem) for line in lines):
            raise SepValidationError("settlement items must be SettlementItem instances.")
        if self.government:
            if not lines:
                raise SepValidationError("A government payment needs at least one settlement line.")
            if lines[0].purchase_id is None or set(lines[0].purchase_id) == {"0"}:
                raise SepValidationError(
                    "The first settlement line of a government payment needs its 30-digit "
                    "government purchase_id."
                )
        object.__setattr__(self, "settlement", lines)

    def to_payload(self, terminal_id: str) -> dict[str, Any]:
        """The JSON body of the token request, exactly as the guide names the fields."""
        payload: dict[str, Any] = {
            "action": "token",
            "TerminalId": terminal_id,
            "Amount": self.amount,
            "ResNum": self.res_num,
            "RedirectUrl": self.redirect_url,
        }
        if self.wage is not None:
            payload["Wage"] = self.wage
        if self.cell_number is not None:
            payload["CellNumber"] = self.cell_number
        if self.token_expiry_minutes is not None:
            payload["TokenExpiryInMin"] = self.token_expiry_minutes
        if self.allowed_cards:
            payload["HashedCardNumber"] = "|".join(self.allowed_cards)
        for index, item in enumerate(self.extra_data, start=1):
            payload[f"ResNum{index}"] = item
        if self.session_key is not None:
            payload["TxnRandomSessionKey"] = self.session_key
        if self.government:
            payload["TranType"] = "Government"
        if self.settlement:
            payload["SettlementIbanInfo"] = [
                {
                    "IBAN": line.iban,
                    "Amount": line.amount,
                    "PurchaseId": line.purchase_id
                    if line.purchase_id is not None
                    else (NO_PURCHASE_ID if self.government else None),
                }
                for line in self.settlement
            ]
            for entry in payload["SettlementIbanInfo"]:
                if entry["PurchaseId"] is None:
                    del entry["PurchaseId"]
        return payload


def _as_sequence(name: str, value: object) -> Sequence[Any]:
    """Refuse a bare ``str`` where a list of strings is meant (it would iterate characters)."""
    if isinstance(value, str | bytes) or not isinstance(value, Sequence):
        raise SepValidationError(f"{name} must be a list or tuple.")
    return value
