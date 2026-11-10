"""When and how long to wait before asking the gateway again."""

from __future__ import annotations

from dataclasses import dataclass

from sep_sdk.errors import SepConfigurationError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Exponential backoff for failed calls.

    ``verify`` and ``reverse`` are idempotent on Saman's side (a repeat is answered
    "duplicate request"), so they are retried on timeouts, resets and 5xx answers.
    Token creation is **not** retried after the request may have reached the bank,
    because that could create two payment sessions for one order; it is retried only
    when the connection could not even be opened.
    """

    max_attempts: int = 3
    backoff_factor: float = 0.5
    max_backoff: float = 8.0
    retry_statuses: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise SepConfigurationError("max_attempts must be at least 1.")
        if self.backoff_factor < 0 or self.max_backoff < 0:
            raise SepConfigurationError("backoff values must not be negative.")

    @classmethod
    def none(cls) -> RetryPolicy:
        """Make every call exactly once."""
        return cls(max_attempts=1)

    def delay(self, failed_attempts: int) -> float:
        """Seconds to wait after the given number of failed attempts (``>= 1``)."""
        return float(min(self.max_backoff, self.backoff_factor * (2 ** (failed_attempts - 1))))
