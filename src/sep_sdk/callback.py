"""Reading the request Saman sends to your ``redirect_url``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sep_sdk.enums import TransactionState, TransactionStatus
from sep_sdk.responses import CallbackData


def parse_callback(params: Mapping[str, object]) -> CallbackData:
    """Turn the callback's form fields or query string into :class:`CallbackData`.

    ``params`` can be anything mapping-like: ``request.POST``, ``request.args``,
    ``await request.form()``, a plain dict, or ``parse_qs`` output (lists are
    flattened to their first value). Parameter names are matched case-insensitively
    because web frameworks differ; values are never executed or evaluated.

    This function **does not trust** its input and makes no network call. See
    :meth:`SepClient.verify_callback` for the step that actually proves payment.
    """
    folded = {str(key).casefold(): value for key, value in params.items()}

    def text(name: str) -> str:
        value = folded.get(name.casefold())
        if isinstance(value, Sequence) and not isinstance(value, str | bytes):
            value = value[0] if value else ""
        return "" if value is None else str(value).strip()

    state_raw = text("State")
    return CallbackData(
        state=TransactionState.from_wire(state_raw),
        state_raw=state_raw,
        status=TransactionStatus.from_wire(text("Status")),
        ref_num=text("RefNum"),
        res_num=text("ResNum"),
        terminal_id=text("TerminalId") or text("MID"),
        trace_no=text("TraceNo"),
        rrn=text("RRN"),
        amount=_integer(text("Amount")),
        wage=_integer(text("Wage")),
        affective_amount=_integer(text("AffectiveAmount")),
        token=text("Token"),
        secure_pan=text("SecurePan"),
        hashed_card_number=text("HashedCardNumber"),
        raw={str(key): str(value) for key, value in params.items()},
    )


def _integer(value: str) -> int | None:
    cleaned = value.replace(",", "")
    return int(cleaned) if cleaned.isascii() and cleaned.isdigit() else None
