"""Where the gateway lives. Override any URL if Saman moves it."""

from __future__ import annotations

from dataclasses import dataclass

from sep_sdk import constants
from sep_sdk.errors import SepConfigurationError
from sep_sdk.validation import require_http_url

_MAX_URL_LENGTH = 2048


@dataclass(frozen=True, slots=True)
class Endpoints:
    """The five URLs of the gateway, plus optional fallbacks for verify and reverse.

    The defaults follow the v3.6 guide. Saman's Postman collections spell the
    verify/reverse paths ``…Transcation``; the client therefore retries the
    ``*_fallback_url`` once when the primary answers HTTP 404, and remembers the one
    that worked. Use :meth:`legacy` to make the old spelling the primary.
    """

    token_url: str = constants.TOKEN_URL
    form_action_url: str = constants.FORM_ACTION_URL
    send_token_url: str = constants.SEND_TOKEN_URL
    verify_url: str = constants.VERIFY_URL
    reverse_url: str = constants.REVERSE_URL
    verify_fallback_url: str | None = constants.LEGACY_VERIFY_URL
    reverse_fallback_url: str | None = constants.LEGACY_REVERSE_URL

    def __post_init__(self) -> None:
        for name in ("token_url", "form_action_url", "send_token_url", "verify_url", "reverse_url"):
            self._check(name, getattr(self, name))
        for name in ("verify_fallback_url", "reverse_fallback_url"):
            value = getattr(self, name)
            if value is not None:
                self._check(name, value)

    @staticmethod
    def _check(name: str, value: object) -> None:
        try:
            require_http_url(name, value, max_length=_MAX_URL_LENGTH)
        except ValueError as error:
            raise SepConfigurationError(str(error)) from None

    @classmethod
    def production(cls) -> Endpoints:
        """The documented production endpoints (the default)."""
        return cls()

    @classmethod
    def legacy(cls) -> Endpoints:
        """Use the ``…Transcation`` spelling first and the documented one as fallback."""
        return cls(
            verify_url=constants.LEGACY_VERIFY_URL,
            reverse_url=constants.LEGACY_REVERSE_URL,
            verify_fallback_url=constants.VERIFY_URL,
            reverse_fallback_url=constants.REVERSE_URL,
        )

    @classmethod
    def without_fallback(cls) -> Endpoints:
        """Production endpoints and never try another spelling."""
        return cls(verify_fallback_url=None, reverse_fallback_url=None)
