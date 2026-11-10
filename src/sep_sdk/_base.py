"""Everything the sync and async clients share: configuration and pure decisions.

Nothing in this module performs I/O. The two client classes add only "send this
request and give me the response", so the rules live in exactly one place.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Final

import httpx

from sep_sdk._parsing import (
    error_for_http_status,
    json_object,
    parse_token,
    parse_transaction,
)
from sep_sdk._version import __version__
from sep_sdk.endpoints import Endpoints
from sep_sdk.enums import Language
from sep_sdk.errors import (
    AmountMismatchError,
    PaymentNotCompletedError,
    SepConfigurationError,
    SepConnectionError,
    SepResponseError,
    SepTimeoutError,
    SepTransportError,
    SepValidationError,
)
from sep_sdk.redirect import render_redirect_form
from sep_sdk.requests import TokenRequest
from sep_sdk.responses import CallbackData, Token, TransactionResult
from sep_sdk.retry import RetryPolicy
from sep_sdk.validation import require_int, to_ascii_digits

logger = logging.getLogger("sep_sdk")

DEFAULT_TIMEOUT: Final = httpx.Timeout(20.0, connect=5.0)
#: Operations that are safe to repeat: Saman answers a repeat with "duplicate request".
IDEMPOTENT_OPERATIONS: Final = frozenset({"verify", "reverse"})


class ClientBase:
    """Configuration, request building and response interpretation."""

    USER_AGENT: ClassVar[str] = f"sep-python-sdk/{__version__}"

    def __init__(
        self,
        terminal_id: str | int,
        *,
        endpoints: Endpoints | None,
        retry: RetryPolicy | None,
        endpoint_fallback: bool,
    ) -> None:
        digits = to_ascii_digits(str(terminal_id).strip())
        if not digits.isascii() or not digits.isdigit():
            raise SepConfigurationError("terminal_id must be the numeric terminal number.")
        self.terminal_id: Final = digits
        self.endpoints = endpoints or Endpoints()
        self.retry = retry or RetryPolicy()
        self._urls = {
            "token": self.endpoints.token_url,
            "verify": self.endpoints.verify_url,
            "reverse": self.endpoints.reverse_url,
        }
        self._fallbacks: dict[str, str | None] = {
            "verify": self.endpoints.verify_fallback_url if endpoint_fallback else None,
            "reverse": self.endpoints.reverse_fallback_url if endpoint_fallback else None,
        }
        self._headers = {"Accept": "application/json", "User-Agent": self.USER_AGENT}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(terminal_id={self.terminal_id!r})"

    # --- request building -------------------------------------------------

    def _token_payload(self, request: TokenRequest) -> dict[str, Any]:
        if not isinstance(request, TokenRequest):
            raise SepValidationError("create_token() needs a TokenRequest.")
        return request.to_payload(self.terminal_id)

    def _reference_payload(self, ref_num: str, session_key: str | None) -> dict[str, Any]:
        if not isinstance(ref_num, str) or not ref_num.strip():
            raise SepValidationError("ref_num must be the receipt string from the callback.")
        payload: dict[str, Any] = {"RefNum": ref_num, "TerminalNumber": int(self.terminal_id)}
        if session_key is not None:
            payload["TxnRandomSessionKey"] = session_key
        return payload

    # --- endpoint selection ----------------------------------------------

    def _url(self, operation: str) -> str:
        return self._urls[operation]

    def _switch_to_fallback(self, operation: str) -> bool:
        """Swap to the alternate spelling once; ``True`` if there was one to try."""
        fallback = self._fallbacks.get(operation)
        if fallback is None:
            return False
        logger.warning("sep_sdk: %s answered 404; trying %s", operation, fallback)
        self._urls[operation] = fallback
        self._fallbacks[operation] = None
        return True

    # --- retry decisions --------------------------------------------------

    def _may_retry_exception(self, error: httpx.TransportError, operation: str) -> bool:
        """A connection that never opened is always safe to retry; the rest only if idempotent."""
        if isinstance(error, httpx.ConnectError | httpx.ConnectTimeout):
            return True
        return operation in IDEMPOTENT_OPERATIONS

    def _may_retry_status(self, status_code: int, operation: str) -> bool:
        return operation in IDEMPOTENT_OPERATIONS and status_code in self.retry.retry_statuses

    @staticmethod
    def _transport_error(error: httpx.TransportError, operation: str) -> SepTransportError:
        if isinstance(error, httpx.TimeoutException):
            return SepTimeoutError(f"{operation}: the gateway did not answer in time.")
        return SepConnectionError(
            f"{operation}: could not talk to the gateway ({type(error).__name__})."
        )

    # --- response interpretation -----------------------------------------

    def _body(self, response: httpx.Response, operation: str) -> dict[str, Any]:
        if not response.is_success:
            raise error_for_http_status(response, operation)
        return json_object(response, operation)

    def _finish_token(self, request: TokenRequest, response: httpx.Response) -> Token:
        body = self._body(response, "token")
        return parse_token(request, body, response.headers, self.endpoints)

    def _finish_transaction(self, response: httpx.Response, operation: str) -> TransactionResult:
        return parse_transaction(self._body(response, operation), operation)

    # --- callback verification -------------------------------------------

    def _ready_to_verify(self, callback: CallbackData, expected_amount: int) -> None:
        require_int("expected_amount", expected_amount, minimum=1)
        if not callback.is_ok:
            raise PaymentNotCompletedError(
                f"The payment was not completed: {callback.state.message('en')}",
                state=callback.state,
            )
        if callback.terminal_id and callback.terminal_id != self.terminal_id:
            raise SepValidationError("The callback belongs to a different terminal.")

    def _check_result(self, callback: CallbackData, result: TransactionResult) -> None:
        if result.ref_num != callback.ref_num:
            raise SepResponseError("verify: the gateway answered for a different receipt.")
        if result.detail.terminal_number != int(self.terminal_id):
            raise SepResponseError("verify: the gateway answered for a different terminal.")

    @staticmethod
    def _amount_mismatch(expected: int, actual: int, *, was_reversed: bool) -> AmountMismatchError:
        return AmountMismatchError(
            f"The gateway took {actual} rials but the order is {expected}.",
            expected=expected,
            actual=actual,
            was_reversed=was_reversed,
        )

    @staticmethod
    def render_redirect_form(
        token: Token, *, language: Language = "en", nonce: str | None = None
    ) -> str:
        """See :func:`sep_sdk.render_redirect_form`."""
        return render_redirect_form(token, language=language, nonce=nonce)
