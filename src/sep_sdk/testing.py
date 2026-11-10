"""An in-memory Saman gateway for your own tests: no network, no terminal, no IP list.

::

    fake = FakeSepGateway(terminal_id="12345678")
    sep = SepClient("12345678", endpoints=fake.endpoints, transport=fake.transport)

    token = sep.create_token(TokenRequest(amount=100_000, res_num="order-1", redirect_url=...))
    params = fake.complete_payment(token.token)       # what the bank would POST back
    callback = parse_callback(params)
    result = sep.verify_callback(callback, expected_amount=100_000)

The fake follows the guide, not Saman's private behaviour, so treat it as a way to
exercise *your* code paths (success, cancellation, outages, amount tampering), and
still run one real small payment before going live.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from sep_sdk.constants import MAX_SESSION_KEY
from sep_sdk.endpoints import Endpoints
from sep_sdk.enums import ResultCode, TransactionState, TransactionStatus

Spelling = Literal["transaction", "transcation", "both"]

_STATUS_FOR_STATE = {
    TransactionState.OK: TransactionStatus.OK,
    TransactionState.CANCELED_BY_USER: TransactionStatus.CANCELED_BY_USER,
    TransactionState.FAILED: TransactionStatus.FAILED,
    TransactionState.SESSION_IS_NULL: TransactionStatus.SESSION_IS_NULL,
    TransactionState.INVALID_PARAMETERS: TransactionStatus.INVALID_PARAMETERS,
    TransactionState.MERCHANT_IP_ADDRESS_IS_INVALID: (
        TransactionStatus.MERCHANT_IP_ADDRESS_IS_INVALID
    ),
    TransactionState.TOKEN_NOT_FOUND: TransactionStatus.TOKEN_NOT_FOUND,
    TransactionState.TOKEN_REQUIRED: TransactionStatus.TOKEN_REQUIRED,
    TransactionState.TERMINAL_NOT_FOUND: TransactionStatus.TERMINAL_NOT_FOUND,
    TransactionState.MULTISETTLE_POLICY_ERRORS: TransactionStatus.MULTISETTLE_POLICY_ERRORS,
}


@dataclass(slots=True)
class _Session:
    res_num: str
    amount: int
    redirect_url: str
    session_key: int | None
    ref_num: str = ""
    paid_amount: int = 0
    verified: bool = False
    reversed: bool = False
    expired: bool = False


@dataclass(slots=True)
class RecordedCall:
    """One request the fake received, for assertions."""

    operation: str
    url: str
    body: dict[str, Any]


@dataclass(slots=True)
class _Failure:
    operation: str | None
    status_code: int | None
    drop: bool


@dataclass(slots=True)
class FakeSepGateway:
    """Simulates token, verify and reverse, and the bank's redirect parameters."""

    terminal_id: str = "12345678"
    #: Which verify/reverse path spelling answers; the other one gets a 404.
    spelling: Spelling = "transaction"
    #: Send the ``X-IPG-Url`` header, like a terminal that moved to ``neo-pg``.
    neo_pg_url: str | None = None
    #: Refuse token requests as an unregistered server IP would (``MerchantIpAddressIsInvalid``).
    reject_ip: bool = False
    calls: list[RecordedCall] = field(default_factory=list)
    _sessions: dict[str, _Session] = field(default_factory=dict)
    _by_ref: dict[str, _Session] = field(default_factory=dict)
    _failures: list[_Failure] = field(default_factory=list)

    @property
    def endpoints(self) -> Endpoints:
        """Endpoints that point at this fake. Pass them to the client."""
        base = "https://fake.sep.test"
        return Endpoints(
            token_url=f"{base}/onlinepg/onlinepg",
            form_action_url=f"{base}/OnlinePG/OnlinePG",
            send_token_url=f"{base}/OnlinePG/SendToken",
            verify_url=f"{base}/ipg/VerifyTransaction",
            reverse_url=f"{base}/ipg/ReverseTransaction",
            verify_fallback_url=f"{base}/ipg/VerifyTranscation",
            reverse_fallback_url=f"{base}/ipg/ReverseTranscation",
        )

    @property
    def transport(self) -> httpx.MockTransport:
        """A transport for :class:`SepClient` and :class:`AsyncSepClient` alike."""
        return httpx.MockTransport(self._handle)

    # --- scripting the world ---------------------------------------------

    def complete_payment(self, token: str, *, paid_amount: int | None = None) -> dict[str, str]:
        """The customer pays. Returns the form fields the bank would POST to your callback.

        ``paid_amount`` lets a test simulate a tampered or partial payment.
        """
        session = self._session(token)
        session.ref_num = "REF" + secrets.token_hex(12)
        session.paid_amount = session.amount if paid_amount is None else paid_amount
        self._by_ref[session.ref_num] = session
        return self._callback_fields(token, session, TransactionState.OK)

    def end_payment(
        self, token: str, state: TransactionState = TransactionState.CANCELED_BY_USER
    ) -> dict[str, str]:
        """The customer does not pay (cancel, failure, timeout). Returns the callback fields."""
        session = self._session(token)
        return self._callback_fields(token, session, state)

    def expire(self, ref_num: str) -> None:
        """Pretend 30 minutes passed without a verify: the next verify answers ``-6``."""
        self._by_ref[ref_num].expired = True

    def fail_next(self, *, status_code: int = 503, operation: str | None = None) -> None:
        """Answer the next matching call with an HTTP error."""
        self._failures.append(_Failure(operation, status_code, drop=False))

    def drop_next(self, *, operation: str | None = None) -> None:
        """Lose the next matching call: the client sees a connection error."""
        self._failures.append(_Failure(operation, None, drop=True))

    # --- the fake server --------------------------------------------------

    def _handle(self, request: httpx.Request) -> httpx.Response:
        operation = self._operation(request.url.path)
        body: dict[str, Any] = json.loads(request.content or b"{}")
        self.calls.append(RecordedCall(operation, str(request.url), body))

        failure = self._take_failure(operation)
        if failure is not None:
            if failure.drop:
                raise httpx.ConnectError("fake: connection dropped", request=request)
            return httpx.Response(failure.status_code or 503, json={"error": "injected"})
        if operation == "unknown" or not self._path_allowed(operation, request.url.path):
            return httpx.Response(404, json={"error": "not found"})
        key = body.get("TxnRandomSessionKey")
        if key is not None and (type(key) is not int or not 0 < key <= MAX_SESSION_KEY):
            return httpx.Response(
                400,
                json={"ModelState": {"model.TxnRandomSessionKey": ["An error has occurred."]}},
            )
        if operation == "token":
            return self._token(body)
        return self._transaction(operation, body)

    def _operation(self, path: str) -> str:
        lowered = path.lower()
        if lowered.endswith("/onlinepg"):
            return "token"
        for name in ("verify", "reverse"):
            if lowered.endswith((f"/{name}transaction", f"/{name}transcation")):
                return name
        return "unknown"

    def _path_allowed(self, operation: str, path: str) -> bool:
        if operation == "token" or self.spelling == "both":
            return True
        legacy = path.lower().endswith("transcation")
        return legacy == (self.spelling == "transcation")

    def _take_failure(self, operation: str) -> _Failure | None:
        for index, failure in enumerate(self._failures):
            if failure.operation in (None, operation):
                return self._failures.pop(index)
        return None

    def _token(self, body: dict[str, Any]) -> httpx.Response:
        if self.reject_ip:
            return httpx.Response(
                200, json={"status": -1, "errorCode": "8", "errorDesc": "merchant ip is invalid"}
            )
        if str(body.get("TerminalId")) != self.terminal_id:
            return httpx.Response(
                200, json={"status": -1, "errorCode": "12", "errorDesc": "terminal not found"}
            )
        token = secrets.token_hex(16)
        self._sessions[token] = _Session(
            res_num=str(body.get("ResNum", "")),
            amount=int(body.get("Amount", 0)),
            redirect_url=str(body.get("RedirectUrl", "")),
            session_key=body.get("TxnRandomSessionKey"),
        )
        headers = {"X-IPG-Url": self.neo_pg_url} if self.neo_pg_url else {}
        return httpx.Response(200, json={"status": 1, "token": token}, headers=headers)

    def _transaction(self, operation: str, body: dict[str, Any]) -> httpx.Response:
        session = self._by_ref.get(str(body.get("RefNum")))
        if str(body.get("TerminalNumber")) != self.terminal_id:
            return self._result(ResultCode.TERMINAL_NOT_FOUND)
        if session is None or (
            session.session_key is not None
            and body.get("TxnRandomSessionKey") != session.session_key
        ):
            return self._result(ResultCode.TRANSACTION_NOT_FOUND)
        return self._reverse(session) if operation == "reverse" else self._verify(session)

    def _reverse(self, session: _Session) -> httpx.Response:
        if session.reversed:
            return self._result(ResultCode.DUPLICATE_REQUEST, session)
        session.reversed = True
        return self._result(ResultCode.SUCCESS, session)

    def _verify(self, session: _Session) -> httpx.Response:
        if session.reversed:
            return self._result(ResultCode.TRANSACTION_REVERSED)
        if session.expired and not session.verified:
            return self._result(ResultCode.VERIFY_WINDOW_EXPIRED)
        duplicate = session.verified
        session.verified = True
        return self._result(
            ResultCode.DUPLICATE_REQUEST if duplicate else ResultCode.SUCCESS, session
        )

    def _result(self, code: ResultCode, session: _Session | None = None) -> httpx.Response:
        body: dict[str, Any] = {
            "ResultCode": int(code),
            "ResultDescription": code.message("en"),
            "Success": code is ResultCode.SUCCESS,
        }
        if session is not None:
            body["TransactionDetail"] = {
                "RRN": "14226761817",
                "RefNum": session.ref_num,
                "MaskedPan": "621986****8080",
                "HashedPan": "b96a14400c3a59249e87c300ecc06e5920327e70220213b5bbb7d7b2410f7e0d",
                "TerminalNumber": int(self.terminal_id),
                "OrginalAmount": session.paid_amount,
                "AffectiveAmount": session.paid_amount,
                "StraceDate": "2026-01-01 12:00:00",
                "StraceNo": "100428",
            }
        return httpx.Response(200, json=body)

    def _session(self, token: str) -> _Session:
        try:
            return self._sessions[token]
        except KeyError:
            raise KeyError("Unknown token: create it with the client first.") from None

    def _callback_fields(
        self, token: str, session: _Session, state: TransactionState
    ) -> dict[str, str]:
        ok = state is TransactionState.OK
        return {
            "MID": self.terminal_id,
            "TerminalId": self.terminal_id,
            "State": state.value,
            "Status": str(int(_STATUS_FOR_STATE[state])),
            "RRN": "14226761817" if ok else "",
            "RefNum": session.ref_num if ok else "",
            "ResNum": session.res_num,
            "TraceNo": "100428" if ok else "",
            "Amount": str(session.paid_amount if ok else session.amount),
            "SecurePan": "621986****8080" if ok else "",
            "Token": token,
        }
