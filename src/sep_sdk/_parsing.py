"""Turning the gateway's JSON into typed values or precise exceptions.

Pure functions only: no I/O, so the sync and async clients share them and they can
be tested exhaustively without a network.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import httpx

from sep_sdk.constants import DEFAULT_TOKEN_EXPIRY_MINUTES, IPG_URL_HEADER
from sep_sdk.endpoints import Endpoints
from sep_sdk.enums import ResultCode
from sep_sdk.errors import (
    IPNotAllowedError,
    SepHTTPError,
    SepResponseError,
    SepTokenError,
    SepTransactionError,
    TerminalError,
    TransactionNotFoundError,
    TransactionReversedError,
    VerifyWindowExpiredError,
)
from sep_sdk.redirect import build_send_token_url
from sep_sdk.requests import TokenRequest
from sep_sdk.responses import Token, TransactionDetail, TransactionResult

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9._~+/=-]{8,512}")
_TRANSACTION_ERRORS: dict[ResultCode, type[SepTransactionError]] = {
    ResultCode.TRANSACTION_NOT_FOUND: TransactionNotFoundError,
    ResultCode.VERIFY_WINDOW_EXPIRED: VerifyWindowExpiredError,
    ResultCode.TRANSACTION_REVERSED: TransactionReversedError,
    ResultCode.TERMINAL_INACTIVE: TerminalError,
    ResultCode.TERMINAL_NOT_FOUND: TerminalError,
    ResultCode.IP_NOT_ALLOWED: IPNotAllowedError,
}


def json_object(response: httpx.Response, operation: str) -> dict[str, Any]:
    """The JSON body as a dict, or :class:`SepResponseError`."""
    try:
        body = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SepResponseError(f"{operation}: the gateway did not answer with JSON.") from None
    if not isinstance(body, dict):
        raise SepResponseError(f"{operation}: expected a JSON object.")
    return {str(key).strip(): value for key, value in body.items()}


def error_for_http_status(
    response: httpx.Response, operation: str
) -> SepHTTPError | SepTransactionError:
    """The best exception for a non-2xx answer.

    A body that carries a ``ResultCode`` (Saman sometimes does this with a 4xx) is
    mapped to the same exceptions as a 200 answer; anything else is :class:`SepHTTPError`.
    """
    if operation != "token":
        try:
            body = json_object(response, operation)
        except SepResponseError:
            body = {}
        code = _integer(body.get("ResultCode"))
        if code is not None:
            return transaction_error(code, str(body.get("ResultDescription", "")), operation)
    return SepHTTPError(
        f"{operation}: the gateway answered HTTP {response.status_code}.",
        status_code=response.status_code,
    )


def parse_token(
    request: TokenRequest, body: Mapping[str, Any], headers: Mapping[str, str], endpoints: Endpoints
) -> Token:
    """Interpret a token response (``status`` 1 with a ``token``, or -1 with an error)."""
    if _integer(body.get("status")) != 1:
        code = _integer(body.get("errorCode"))
        description = str(body.get("errorDesc", ""))
        raise SepTokenError(
            f"token: the gateway refused the request (errorCode={code}).",
            code=code,
            description=description,
            operation="token",
        )
    token = body.get("token")
    if not isinstance(token, str) or _TOKEN_PATTERN.fullmatch(token) is None:
        raise SepResponseError("token: the gateway returned an unusable token.")

    ipg_url = headers.get(IPG_URL_HEADER) or None
    if ipg_url is not None and not ipg_url.startswith("https://"):
        raise SepResponseError(f"token: the {IPG_URL_HEADER} header is not an https URL.")
    return Token(
        token=token,
        res_num=request.res_num,
        form_action=ipg_url or endpoints.form_action_url,
        get_url=None if ipg_url else build_send_token_url(token, base_url=endpoints.send_token_url),
        ipg_url=ipg_url,
        get_method=request.callback_method == "GET",
        expires_in_minutes=request.token_expiry_minutes or DEFAULT_TOKEN_EXPIRY_MINUTES,
    )


def parse_transaction(body: Mapping[str, Any], operation: str) -> TransactionResult:
    """Interpret a verify or reverse answer, raising on any non-success code."""
    code = _integer(body.get("ResultCode"))
    if code is None:
        raise SepResponseError(f"{operation}: the answer has no ResultCode.")
    if code not in {ResultCode.SUCCESS, ResultCode.DUPLICATE_REQUEST}:
        raise transaction_error(code, str(body.get("ResultDescription", "")), operation)

    detail = body.get("TransactionDetail")
    if not isinstance(detail, Mapping):
        raise SepResponseError(f"{operation}: the answer has no TransactionDetail.")
    return TransactionResult(
        detail=_detail(detail, operation),
        result_code=ResultCode.from_wire(code),
        description=str(body.get("ResultDescription", "")),
        is_duplicate=code == ResultCode.DUPLICATE_REQUEST,
    )


def transaction_error(code: int, description: str, operation: str) -> SepTransactionError:
    """Map a failing ``ResultCode`` to the most specific exception."""
    known = ResultCode.from_wire(code)
    error_type = (
        _TRANSACTION_ERRORS.get(known, SepTransactionError)
        if isinstance(known, ResultCode)
        else SepTransactionError
    )
    message = f"{operation}: the gateway refused the request (ResultCode={code})."
    return error_type(message, result_code=known, description=description, operation=operation)


def _detail(detail: Mapping[str, Any], operation: str) -> TransactionDetail:
    fields = {str(key).strip(): value for key, value in detail.items()}
    original = _integer(fields.get("OrginalAmount", fields.get("OriginalAmount")))
    terminal = _integer(fields.get("TerminalNumber"))
    ref_num = fields.get("RefNum")
    if (
        original is None
        or original <= 0
        or terminal is None
        or not isinstance(ref_num, str)
        or not ref_num
    ):
        raise SepResponseError(f"{operation}: TransactionDetail is incomplete.")
    affective = _integer(fields.get("AffectiveAmount"))
    return TransactionDetail(
        ref_num=ref_num,
        rrn=str(fields.get("RRN", "")),
        masked_pan=str(fields.get("MaskedPan", "")),
        hashed_pan=str(fields.get("HashedPan", "")),
        terminal_number=terminal,
        original_amount=original,
        affective_amount=original if affective is None else affective,
        trace_date=_trace_date(fields.get("StraceDate")),
        trace_no=str(fields.get("StraceNo", "")),
    )


def _trace_date(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"-?\d{1,18}", value.strip()):
        return int(value.strip())
    return None
