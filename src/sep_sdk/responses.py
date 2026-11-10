"""What comes back from the gateway, as immutable, typed values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from sep_sdk.enums import ResultCode, TransactionState, TransactionStatus


@dataclass(frozen=True, slots=True)
class Token:
    """A payment token and everything needed to send the customer to the bank.

    Prefer :func:`sep_sdk.render_redirect_form` (a POST form) for the hand-off: it
    works for every terminal. :attr:`get_url` is the simple link form and exists only
    for classic terminals; terminals moved to ``neo-pg`` get :attr:`ipg_url` and must
    use the form.
    """

    token: str
    res_num: str
    #: Where the HTML form posts the token (the ``X-IPG-Url`` header on ``neo-pg``).
    form_action: str
    #: ``https://…/SendToken?token=…`` for classic terminals; ``None`` on ``neo-pg``.
    get_url: str | None
    #: The ``X-IPG-Url`` header Saman sent, when the terminal is on ``neo-pg``.
    ipg_url: str | None
    #: Whether Saman will return the customer by ``GET`` (query string) instead of ``POST``.
    get_method: bool
    expires_in_minutes: int

    def __repr__(self) -> str:
        # The token is a one-time payment handle; keep it out of logs and tracebacks.
        return (
            f"Token(res_num={self.res_num!r}, token='***', "
            f"expires_in_minutes={self.expires_in_minutes})"
        )


@dataclass(frozen=True, slots=True)
class CallbackData:
    """The parameters Saman sends to your ``redirect_url``, parsed but **not trusted**.

    Anyone can send your callback URL any parameters. Use this to learn *which* order
    to check and whether the customer even tried; the only proof of payment is
    :meth:`SepClient.verify_transaction` (or :meth:`SepClient.verify_callback`).
    """

    state: TransactionState
    state_raw: str
    status: TransactionStatus | None
    ref_num: str
    res_num: str
    terminal_id: str
    trace_no: str
    rrn: str
    amount: int | None
    wage: int | None
    affective_amount: int | None
    token: str
    #: Masked card number, e.g. ``621986****8080``. Hidden from ``repr``.
    secure_pan: str = field(repr=False)
    #: SHA-256 of the card number. Hidden from ``repr``.
    hashed_card_number: str = field(repr=False)
    raw: Mapping[str, str] = field(repr=False)

    @property
    def is_ok(self) -> bool:
        """``State`` is ``OK``, a receipt exists, and ``Status`` (if sent) agrees."""
        return (
            self.state.is_ok and bool(self.ref_num) and self.status in (None, TransactionStatus.OK)
        )


@dataclass(frozen=True, slots=True)
class TransactionDetail:
    """The ``TransactionDetail`` block of a verify or reverse answer."""

    ref_num: str
    rrn: str
    masked_pan: str = field(repr=False)
    hashed_pan: str = field(repr=False)
    terminal_number: int
    #: The amount sent to the gateway (``OrginalAmount`` in Saman's spelling).
    original_amount: int
    #: The amount actually deducted from the card (differs on discount terminals).
    affective_amount: int
    #: ``StraceDate`` parsed; Saman does not state a timezone, so it is naive.
    trace_date: datetime | None
    trace_no: str


@dataclass(frozen=True, slots=True)
class TransactionResult:
    """The outcome of a successful verify or reverse call."""

    detail: TransactionDetail
    result_code: ResultCode | int
    description: str
    #: ``True`` when Saman answered "duplicate request" (``2``): the same call had
    #: already been processed, typically because an earlier reply was lost.
    is_duplicate: bool

    @property
    def ref_num(self) -> str:
        return self.detail.ref_num

    @property
    def amount(self) -> int:
        """The amount to compare with your order total (``original_amount``)."""
        return self.detail.original_amount
