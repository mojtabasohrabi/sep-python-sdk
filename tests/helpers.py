"""Scripted transports for the cases the happy-path fake does not cover."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

TERMINAL = "12345678"


def ok_detail(**overrides: Any) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "RRN": "14226761817",
        "RefNum": "ref-1",
        "MaskedPan": "621986****8080",
        "HashedPan": "b96a",
        "TerminalNumber": int(TERMINAL),
        "OrginalAmount": 12_000,
        "AffectiveAmount": 12_000,
        "StraceDate": "2019-09-16 18:11:06",
        "StraceNo": "100428",
    }
    detail.update(overrides)
    return detail


def ok_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "TransactionDetail": ok_detail(),
        "ResultCode": 0,
        "ResultDescription": "ok",
        "Success": True,
    }
    body.update(overrides)
    return body


class Script:
    """A transport that plays back responses (or raises exceptions) in order."""

    def __init__(
        self, *steps: httpx.Response | Exception | Callable[[httpx.Request], httpx.Response]
    ) -> None:
        self._steps = list(steps)
        self.requests: list[httpx.Request] = []

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self._steps.pop(0) if len(self._steps) > 1 else self._steps[0]
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(request)
        return step


def json_response(
    body: Any, status: int = 200, headers: dict[str, str] | None = None
) -> httpx.Response:
    return httpx.Response(status, json=body, headers=headers)
