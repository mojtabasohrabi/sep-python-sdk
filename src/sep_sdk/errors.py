"""Every exception this SDK raises, in one hierarchy rooted at :class:`SepError`.

Catch :class:`SepError` to handle anything; catch the narrower classes to react
differently to "the network is down" (retry later), "the bank refused" (tell the
customer) and "your request was wrong" (fix your code).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sep_sdk.enums import ResultCode, TransactionState


class SepError(Exception):
    """Base class of every error raised by this package."""


class SepConfigurationError(SepError, ValueError):
    """The client was configured with something unusable (terminal id, endpoints, retry)."""


class SepValidationError(SepError, ValueError):
    """A request was rejected locally, before anything was sent to the gateway."""


class SepTransportError(SepError):
    """The request did not complete, so the gateway's answer is unknown."""


class SepConnectionError(SepTransportError):
    """The gateway could not be reached (DNS, TLS, refused or reset connection)."""


class SepTimeoutError(SepTransportError):
    """The gateway did not answer in time."""


class SepHTTPError(SepError):
    """The gateway answered with an HTTP status this SDK cannot interpret further."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class SepResponseError(SepError):
    """The gateway answered 2xx but the body was not what the guide describes."""


class SepAPIError(SepError):
    """The gateway understood the request and refused it.

    ``code`` is the vendor's numeric code, ``description`` its free text. The text
    is written by the gateway: log it, but do not show it to customers verbatim.
    """

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        description: str = "",
        operation: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.description = description
        self.operation = operation


class SepTokenError(SepAPIError):
    """The token request was refused (``status = -1``). See ``code`` / ``description``."""


class SepTransactionError(SepAPIError):
    """Verify or reverse was refused. ``result_code`` is the vendor's ``ResultCode``."""

    def __init__(
        self,
        message: str,
        *,
        result_code: ResultCode | int,
        description: str = "",
        operation: str = "",
    ) -> None:
        super().__init__(
            message, code=int(result_code), description=description, operation=operation
        )
        self.result_code = result_code


class TransactionNotFoundError(SepTransactionError):
    """No such receipt (``-2``): wrong ``RefNum``, or a ``TxnRandomSessionKey`` mismatch."""


class VerifyWindowExpiredError(SepTransactionError):
    """More than 30 minutes passed (``-6``); Saman has reversed or will reverse the payment."""


class TransactionReversedError(SepTransactionError):
    """The transaction was reversed (``5``): the customer has been refunded."""


class TerminalError(SepTransactionError):
    """The terminal is unknown (``-105``) or inactive (``-104``)."""


class IPNotAllowedError(SepTransactionError):
    """This server's IP address is not registered with Saman (``-106``)."""


class PaymentNotCompletedError(SepError):
    """The callback says the customer did not pay, so there is nothing to verify."""

    def __init__(self, message: str, *, state: TransactionState) -> None:
        super().__init__(message)
        self.state = state


class AmountMismatchError(SepError):
    """The gateway took a different sum than the order was priced at.

    Saman's guide: the whole amount must go back to the customer and the goods
    must not be delivered. ``reversed`` tells you whether the SDK already did the
    reversal (``reverse_on_mismatch=True``) and it succeeded.
    """

    def __init__(self, message: str, *, expected: int, actual: int, was_reversed: bool) -> None:
        super().__init__(message)
        self.expected = expected
        self.actual = actual
        self.reversed = was_reversed
