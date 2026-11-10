"""The synchronous client."""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Any

import httpx

from sep_sdk._base import DEFAULT_TIMEOUT, ClientBase
from sep_sdk.endpoints import Endpoints
from sep_sdk.errors import SepError
from sep_sdk.requests import TokenRequest
from sep_sdk.responses import CallbackData, Token, TransactionResult
from sep_sdk.retry import RetryPolicy

logger = logging.getLogger("sep_sdk")


class SepClient(ClientBase):
    """Talk to the Saman online gateway from synchronous code.

    ::

        with SepClient(terminal_id="12345678") as sep:
            token = sep.create_token(TokenRequest(amount=100_000, res_num="order-1", ...))

    The client owns a connection pool; use it as a context manager or call
    :meth:`close`. Pass ``http_client`` to supply your own :class:`httpx.Client`
    (proxies, mTLS, instrumentation); it is then yours to close.
    """

    def __init__(
        self,
        terminal_id: str | int,
        *,
        endpoints: Endpoints | None = None,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        retry: RetryPolicy | None = None,
        endpoint_fallback: bool = True,
        transport: httpx.BaseTransport | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            terminal_id, endpoints=endpoints, retry=retry, endpoint_fallback=endpoint_fallback
        )
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout, transport=transport)

    def __enter__(self) -> SepClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the connection pool (a client you passed in is left open)."""
        if self._owns_client:
            self._http.close()

    # --- the four calls of the guide -------------------------------------

    def create_token(self, request: TokenRequest) -> Token:
        """Ask for a payment token for one order (guide step 1)."""
        response = self._post("token", self._token_payload(request))
        return self._finish_token(request, response)

    def verify_transaction(
        self, ref_num: str, *, session_key: str | int | None = None
    ) -> TransactionResult:
        """Confirm a receipt with the gateway (guide step 9). Do this within 30 minutes."""
        response = self._post("verify", self._reference_payload(ref_num, session_key))
        return self._finish_transaction(response, "verify")

    def reverse_transaction(
        self, ref_num: str, *, session_key: str | int | None = None
    ) -> TransactionResult:
        """Ask for the money back, up to 50 minutes after a verified payment (guide step 10)."""
        response = self._post("reverse", self._reference_payload(ref_num, session_key))
        return self._finish_transaction(response, "reverse")

    def verify_callback(
        self,
        callback: CallbackData,
        *,
        expected_amount: int,
        session_key: str | int | None = None,
        reverse_on_mismatch: bool = False,
    ) -> TransactionResult:
        """The whole safe check in one call; returns only if the money is really there.

        1. refuses a callback whose ``State`` is not ``OK`` (``PaymentNotCompletedError``);
        2. verifies the receipt with the gateway;
        3. checks the receipt, the terminal and that the gateway took ``expected_amount``
           rials (``AmountMismatchError`` otherwise, after an optional reversal).

        ``expected_amount`` must come from *your* order record, never from the request.
        Marking the order paid, and refusing a receipt you have already used, is up to
        you: record ``result.ref_num`` under a unique constraint.
        """
        self._ready_to_verify(callback, expected_amount)
        result = self.verify_transaction(callback.ref_num, session_key=session_key)
        self._check_result(callback, result)
        if result.amount != expected_amount:
            reversed_ = False
            if reverse_on_mismatch:
                try:
                    self.reverse_transaction(callback.ref_num, session_key=session_key)
                    reversed_ = True
                except SepError:
                    logger.exception("sep_sdk: could not reverse a mismatched payment")
            raise self._amount_mismatch(expected_amount, result.amount, was_reversed=reversed_)
        return result

    # --- transport --------------------------------------------------------

    def _post(self, operation: str, payload: dict[str, Any]) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            url = self._url(operation)
            logger.debug("sep_sdk: %s attempt %d", operation, attempt)
            try:
                response = self._http.post(url, json=payload, headers=self._headers)
            except httpx.TransportError as error:
                if attempt < self.retry.max_attempts and self._may_retry_exception(
                    error, operation
                ):
                    self._pause(attempt, operation)
                    continue
                raise self._transport_error(error, operation) from error
            if response.status_code == 404 and self._switch_to_fallback(operation):
                attempt -= 1
                continue
            if attempt < self.retry.max_attempts and self._may_retry_status(
                response.status_code, operation
            ):
                self._pause(attempt, operation)
                continue
            return response

    def _pause(self, attempt: int, operation: str) -> None:
        delay = self.retry.delay(attempt)
        logger.warning(
            "sep_sdk: %s failed (attempt %d); retrying in %.1fs", operation, attempt, delay
        )
        if delay:
            time.sleep(delay)
