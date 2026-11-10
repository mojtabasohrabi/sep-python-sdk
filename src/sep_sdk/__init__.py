"""sep-python-sdk: an unofficial, typed Python SDK for the Saman Electronic Payment gateway.

Not affiliated with or endorsed by Saman Electronic Payment (SEP).
"""

from __future__ import annotations

import logging

from sep_sdk._version import __version__
from sep_sdk.async_client import AsyncSepClient
from sep_sdk.callback import parse_callback
from sep_sdk.client import SepClient
from sep_sdk.constants import NO_PURCHASE_ID
from sep_sdk.endpoints import Endpoints
from sep_sdk.enums import Language, ResultCode, TransactionState, TransactionStatus
from sep_sdk.errors import (
    AmountMismatchError,
    IPNotAllowedError,
    PaymentNotCompletedError,
    SepAPIError,
    SepConfigurationError,
    SepConnectionError,
    SepError,
    SepHTTPError,
    SepResponseError,
    SepTimeoutError,
    SepTokenError,
    SepTransactionError,
    SepTransportError,
    SepValidationError,
    TerminalError,
    TransactionNotFoundError,
    TransactionReversedError,
    VerifyWindowExpiredError,
)
from sep_sdk.redirect import build_send_token_url, redirect_form_fields, render_redirect_form
from sep_sdk.requests import CallbackMethod, SettlementItem, TokenRequest
from sep_sdk.responses import CallbackData, Token, TransactionDetail, TransactionResult
from sep_sdk.retry import RetryPolicy
from sep_sdk.security import derive_session_key, generate_session_key, hash_card_number
from sep_sdk.validation import iban_checksum_ok

logging.getLogger("sep_sdk").addHandler(logging.NullHandler())

__all__ = [
    "NO_PURCHASE_ID",
    "AmountMismatchError",
    "AsyncSepClient",
    "CallbackData",
    "CallbackMethod",
    "Endpoints",
    "IPNotAllowedError",
    "Language",
    "PaymentNotCompletedError",
    "ResultCode",
    "RetryPolicy",
    "SepAPIError",
    "SepClient",
    "SepConfigurationError",
    "SepConnectionError",
    "SepError",
    "SepHTTPError",
    "SepResponseError",
    "SepTimeoutError",
    "SepTokenError",
    "SepTransactionError",
    "SepTransportError",
    "SepValidationError",
    "SettlementItem",
    "TerminalError",
    "Token",
    "TokenRequest",
    "TransactionDetail",
    "TransactionNotFoundError",
    "TransactionResult",
    "TransactionReversedError",
    "TransactionState",
    "TransactionStatus",
    "VerifyWindowExpiredError",
    "__version__",
    "build_send_token_url",
    "derive_session_key",
    "generate_session_key",
    "hash_card_number",
    "iban_checksum_ok",
    "parse_callback",
    "redirect_form_fields",
    "render_redirect_form",
]
