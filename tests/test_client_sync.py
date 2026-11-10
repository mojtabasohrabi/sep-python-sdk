from __future__ import annotations

import json
import logging

import httpx
import pytest

from sep_sdk import (
    AmountMismatchError,
    Endpoints,
    IPNotAllowedError,
    PaymentNotCompletedError,
    RetryPolicy,
    SepClient,
    SepConfigurationError,
    SepConnectionError,
    SepHTTPError,
    SepResponseError,
    SepTimeoutError,
    SepTokenError,
    SepTransactionError,
    SepValidationError,
    TerminalError,
    TokenRequest,
    TransactionNotFoundError,
    TransactionReversedError,
    TransactionState,
    VerifyWindowExpiredError,
    generate_session_key,
    parse_callback,
)
from sep_sdk.testing import FakeSepGateway
from tests.conftest import CALLBACK_URL, NO_WAIT, TERMINAL
from tests.helpers import Script, json_response, ok_body, ok_detail

ORDER = TokenRequest(amount=12_000, res_num="order-1", redirect_url=CALLBACK_URL)


def client_for(script: Script, **options: object) -> SepClient:
    options.setdefault("retry", NO_WAIT)
    return SepClient(TERMINAL, transport=script.transport, **options)  # type: ignore[arg-type]


class TestConstruction:
    @pytest.mark.parametrize("terminal", ["", "abc", "12 34", "-5"])
    def test_terminal_must_be_numeric(self, terminal: str) -> None:
        with pytest.raises(SepConfigurationError):
            SepClient(terminal)

    def test_terminal_may_be_an_int_or_persian_digits(self) -> None:
        assert SepClient(1234).terminal_id == "1234"
        assert SepClient("۱۲۳۴").terminal_id == "1234"

    def test_repr_names_the_terminal_only(self) -> None:
        assert repr(SepClient(1234)) == "SepClient(terminal_id='1234')"

    def test_an_external_http_client_is_not_closed(self) -> None:
        http = httpx.Client()
        SepClient(TERMINAL, http_client=http).close()
        assert not http.is_closed
        http.close()

    def test_an_owned_client_is_closed(self) -> None:
        with SepClient(TERMINAL) as sep:
            http = sep._http
        assert http.is_closed


class TestCreateToken:
    def test_happy_path(self, client: SepClient, fake: FakeSepGateway) -> None:
        token = client.create_token(ORDER)
        assert token.res_num == "order-1"
        assert token.form_action == fake.endpoints.form_action_url
        assert token.get_url == f"{fake.endpoints.send_token_url}?token={token.token}"
        assert token.ipg_url is None
        assert token.get_method is False
        assert token.expires_in_minutes == 20
        assert fake.calls[0].body["TerminalId"] == TERMINAL
        assert token.token not in repr(token)

    def test_expiry_and_get_method_are_reported(self, client: SepClient) -> None:
        order = TokenRequest(
            amount=1_000,
            res_num="o",
            redirect_url=CALLBACK_URL,
            token_expiry_minutes=90,
            callback_method="GET",
        )
        token = client.create_token(order)
        assert (token.expires_in_minutes, token.get_method) == (90, True)

    def test_neo_pg_terminals_get_a_form_action_and_no_get_link(self) -> None:
        fake = FakeSepGateway(
            terminal_id=TERMINAL, neo_pg_url="https://neo-pg.sep.test/transaction/init"
        )
        with SepClient(TERMINAL, endpoints=fake.endpoints, transport=fake.transport) as sep:
            token = sep.create_token(ORDER)
        assert token.form_action == "https://neo-pg.sep.test/transaction/init"
        assert token.ipg_url == token.form_action
        assert token.get_url is None

    def test_an_insecure_ipg_header_is_refused(self) -> None:
        script = Script(
            json_response(
                {"status": 1, "token": "abcdefgh12"}, headers={"X-IPG-Url": "http://evil.test"}
            )
        )
        with pytest.raises(SepResponseError, match="https"):
            client_for(script).create_token(ORDER)

    def test_refusals_carry_the_vendor_code(self) -> None:
        script = Script(
            json_response({"status": -1, "errorCode": "5", "errorDesc": "bad <b>params</b>"})
        )
        with pytest.raises(SepTokenError) as raised:
            client_for(script).create_token(ORDER)
        assert raised.value.code == 5
        assert raised.value.description == "bad <b>params</b>"
        assert raised.value.operation == "token"
        assert "bad" not in str(raised.value)

    def test_an_unregistered_ip_is_reported_as_a_refusal(self) -> None:
        fake = FakeSepGateway(terminal_id=TERMINAL, reject_ip=True)
        with (
            SepClient(TERMINAL, endpoints=fake.endpoints, transport=fake.transport) as sep,
            pytest.raises(SepTokenError) as raised,
        ):
            sep.create_token(ORDER)
        assert raised.value.code == 8

    @pytest.mark.parametrize("token", [None, "", "short", 12345678, "has space in it"])
    def test_unusable_tokens(self, token: object) -> None:
        script = Script(json_response({"status": 1, "token": token}))
        with pytest.raises(SepResponseError, match="unusable token"):
            client_for(script).create_token(ORDER)

    def test_only_a_token_request_is_accepted(self, client: SepClient) -> None:
        with pytest.raises(SepValidationError, match="TokenRequest"):
            client.create_token({"amount": 1})  # type: ignore[arg-type]

    def test_the_request_carries_a_user_agent(self, fake: FakeSepGateway) -> None:
        script = Script(json_response({"status": 1, "token": "abcdefgh12"}))
        client_for(script).create_token(ORDER)
        assert script.requests[0].headers["user-agent"].startswith("sep-python-sdk/")
        assert json.loads(script.requests[0].content)["action"] == "token"


class TestVerifyAndReverse:
    def paid(self, client: SepClient, fake: FakeSepGateway, session_key: str | None = None) -> str:
        order = TokenRequest(
            amount=12_000, res_num="o", redirect_url=CALLBACK_URL, session_key=session_key
        )
        token = client.create_token(order)
        return fake.complete_payment(token.token)["RefNum"]

    def test_verify(self, client: SepClient, fake: FakeSepGateway) -> None:
        ref = self.paid(client, fake)
        result = client.verify_transaction(ref)
        assert result.amount == 12_000
        assert result.ref_num == ref
        assert not result.is_duplicate
        assert result.detail.trace_date is not None
        assert result.detail.terminal_number == int(TERMINAL)
        assert "621986" not in repr(result)

    def test_a_repeated_verify_is_flagged_as_a_duplicate(
        self, client: SepClient, fake: FakeSepGateway
    ) -> None:
        ref = self.paid(client, fake)
        client.verify_transaction(ref)
        assert client.verify_transaction(ref).is_duplicate

    def test_reverse_then_verify(self, client: SepClient, fake: FakeSepGateway) -> None:
        ref = self.paid(client, fake)
        client.verify_transaction(ref)
        assert not client.reverse_transaction(ref).is_duplicate
        assert client.reverse_transaction(ref).is_duplicate
        with pytest.raises(TransactionReversedError):
            client.verify_transaction(ref)

    def test_session_key_binding(self, client: SepClient, fake: FakeSepGateway) -> None:
        key = generate_session_key()
        ref = self.paid(client, fake, session_key=key)
        with pytest.raises(TransactionNotFoundError):
            client.verify_transaction(ref)
        with pytest.raises(TransactionNotFoundError):
            client.verify_transaction(ref, session_key="1" if key != "1" else "2")
        assert client.verify_transaction(ref, session_key=key).amount == 12_000

    def test_unknown_receipt(self, client: SepClient) -> None:
        with pytest.raises(TransactionNotFoundError) as raised:
            client.verify_transaction("nope")
        assert raised.value.result_code == -2
        assert raised.value.code == -2

    def test_expired_window(self, client: SepClient, fake: FakeSepGateway) -> None:
        ref = self.paid(client, fake)
        fake.expire(ref)
        with pytest.raises(VerifyWindowExpiredError):
            client.verify_transaction(ref)

    def test_wrong_terminal_on_the_gateway_side(self, fake: FakeSepGateway) -> None:
        with (
            SepClient("999", endpoints=fake.endpoints, transport=fake.transport) as other,
            pytest.raises(TerminalError),
        ):
            other.verify_transaction("x")

    @pytest.mark.parametrize(
        ("code", "error"),
        [
            (-104, TerminalError),
            (-105, TerminalError),
            (-106, IPNotAllowedError),
            (-2, TransactionNotFoundError),
            (5, TransactionReversedError),
            (-6, VerifyWindowExpiredError),
            (-777, SepTransactionError),
        ],
    )
    def test_every_failing_code_maps_to_its_exception(
        self, code: int, error: type[Exception]
    ) -> None:
        script = Script(
            json_response({"ResultCode": code, "ResultDescription": "d", "Success": False})
        )
        with pytest.raises(error) as raised:
            client_for(script).verify_transaction("ref-1")
        assert type(raised.value) is error
        assert raised.value.description == "d"  # type: ignore[attr-defined]

    def test_a_failing_code_in_an_http_error_body_is_still_mapped(self) -> None:
        script = Script(json_response({"ResultCode": -106, "ResultDescription": "ip"}, status=403))
        with pytest.raises(IPNotAllowedError):
            client_for(script).verify_transaction("ref-1")

    def test_http_errors_without_a_result_code(self) -> None:
        for body in ({"message": "nope"}, ["list"]):
            script = Script(json_response(body, status=403))
            with pytest.raises(SepHTTPError) as raised:
                client_for(script).verify_transaction("ref-1")
            assert raised.value.status_code == 403

    def test_http_errors_on_the_token_call_are_plain(self) -> None:
        script = Script(json_response({"ResultCode": -2}, status=400))
        with pytest.raises(SepHTTPError):
            client_for(script).create_token(ORDER)

    def test_non_json_bodies(self) -> None:
        script = Script(httpx.Response(200, text="<html>maintenance</html>"))
        with pytest.raises(SepResponseError, match="JSON"):
            client_for(script).verify_transaction("ref-1")
        script = Script(httpx.Response(502, text="<html>bad gateway</html>"))
        with pytest.raises(SepHTTPError):
            client_for(script, retry=RetryPolicy.none()).verify_transaction("ref-1")

    def test_a_boolean_is_not_a_result_code(self) -> None:
        with pytest.raises(SepResponseError, match="ResultCode"):
            client_for(Script(json_response({"ResultCode": True}))).verify_transaction("ref-1")

    def test_a_json_array_is_not_an_answer(self) -> None:
        script = Script(json_response([1, 2]))
        with pytest.raises(SepResponseError, match="object"):
            client_for(script).verify_transaction("ref-1")

    @pytest.mark.parametrize(
        "body",
        [
            {"Success": True},
            {"ResultCode": 0},
            {"ResultCode": 0, "TransactionDetail": "x"},
            ok_body(TransactionDetail=ok_detail(OrginalAmount=0)),
            ok_body(TransactionDetail=ok_detail(OrginalAmount="abc")),
            ok_body(TransactionDetail=ok_detail(TerminalNumber=None)),
            ok_body(TransactionDetail=ok_detail(RefNum="")),
            ok_body(TransactionDetail=ok_detail(RefNum=5)),
        ],
    )
    def test_incomplete_answers_are_rejected(self, body: dict[str, object]) -> None:
        with pytest.raises(SepResponseError):
            client_for(Script(json_response(body))).verify_transaction("ref-1")

    def test_detail_quirks_are_tolerated(self) -> None:
        detail = ok_detail(OriginalAmount=7, StraceDate="garbage")
        del detail["OrginalAmount"]
        del detail["AffectiveAmount"]
        body = ok_body(
            TransactionDetail={
                " RefNum ": "ref-1",
                **{k: v for k, v in detail.items() if k != "RefNum"},
            }
        )
        result = client_for(Script(json_response(body))).verify_transaction("ref-1")
        assert result.amount == 7
        assert result.detail.affective_amount == 7
        assert result.detail.trace_date is None

    def test_trace_date_that_is_not_text(self) -> None:
        body = ok_body(TransactionDetail=ok_detail(StraceDate=20190916))
        assert (
            client_for(Script(json_response(body))).verify_transaction("r").detail.trace_date
            is None
        )

    def test_a_blank_receipt_is_refused_locally(self, client: SepClient) -> None:
        for bad in ("", "  ", None):
            with pytest.raises(SepValidationError):
                client.verify_transaction(bad)  # type: ignore[arg-type]


class TestVerifyCallback:
    def callback_for(
        self, client: SepClient, fake: FakeSepGateway, *, paid: int | None = None
    ) -> object:
        token = client.create_token(ORDER)
        return parse_callback(fake.complete_payment(token.token, paid_amount=paid))

    def test_a_good_payment(self, client: SepClient, fake: FakeSepGateway) -> None:
        callback = self.callback_for(client, fake)
        result = client.verify_callback(callback, expected_amount=12_000)  # type: ignore[arg-type]
        assert result.amount == 12_000

    @pytest.mark.parametrize(
        "state",
        [
            TransactionState.CANCELED_BY_USER,
            TransactionState.FAILED,
            TransactionState.SESSION_IS_NULL,
        ],
    )
    def test_unpaid_callbacks_are_not_verified(
        self, client: SepClient, fake: FakeSepGateway, state: TransactionState
    ) -> None:
        token = client.create_token(ORDER)
        callback = parse_callback(fake.end_payment(token.token, state))
        calls_before = len(fake.calls)
        with pytest.raises(PaymentNotCompletedError) as raised:
            client.verify_callback(callback, expected_amount=12_000)
        assert raised.value.state is state
        assert len(fake.calls) == calls_before

    def test_a_callback_for_another_terminal(self, client: SepClient, fake: FakeSepGateway) -> None:
        token = client.create_token(ORDER)
        callback = parse_callback({**fake.complete_payment(token.token), "TerminalId": "999"})
        with pytest.raises(SepValidationError, match="terminal"):
            client.verify_callback(callback, expected_amount=12_000)

    def test_a_callback_without_a_terminal_is_allowed(
        self, client: SepClient, fake: FakeSepGateway
    ) -> None:
        token = client.create_token(ORDER)
        fields = fake.complete_payment(token.token)
        fields.pop("TerminalId")
        fields.pop("MID")
        assert client.verify_callback(parse_callback(fields), expected_amount=12_000)

    def test_the_expected_amount_must_be_sane(
        self, client: SepClient, fake: FakeSepGateway
    ) -> None:
        callback = self.callback_for(client, fake)
        with pytest.raises(SepValidationError):
            client.verify_callback(callback, expected_amount=0)  # type: ignore[arg-type]

    def test_an_amount_mismatch(self, client: SepClient, fake: FakeSepGateway) -> None:
        callback = self.callback_for(client, fake, paid=1_000)
        with pytest.raises(AmountMismatchError) as raised:
            client.verify_callback(callback, expected_amount=12_000)  # type: ignore[arg-type]
        assert (raised.value.expected, raised.value.actual, raised.value.reversed) == (
            12_000,
            1_000,
            False,
        )

    def test_an_amount_mismatch_can_reverse_itself(
        self, client: SepClient, fake: FakeSepGateway
    ) -> None:
        callback = self.callback_for(client, fake, paid=1_000)
        with pytest.raises(AmountMismatchError) as raised:
            client.verify_callback(callback, expected_amount=12_000, reverse_on_mismatch=True)  # type: ignore[arg-type]
        assert raised.value.reversed is True
        assert [c.operation for c in fake.calls][-2:] == ["verify", "reverse"]

    def test_a_failed_reversal_is_reported_not_hidden(
        self, client: SepClient, fake: FakeSepGateway, caplog: pytest.LogCaptureFixture
    ) -> None:
        callback = self.callback_for(client, fake, paid=1_000)
        fake.fail_next(operation="reverse", status_code=403)
        with (
            caplog.at_level(logging.ERROR, logger="sep_sdk"),
            pytest.raises(AmountMismatchError) as raised,
        ):
            client.verify_callback(callback, expected_amount=12_000, reverse_on_mismatch=True)  # type: ignore[arg-type]
        assert raised.value.reversed is False
        assert "could not reverse" in caplog.text

    def test_the_gateway_answering_for_another_receipt(self) -> None:
        callback = parse_callback({"State": "OK", "RefNum": "ref-1", "TerminalId": TERMINAL})
        body = ok_body(TransactionDetail=ok_detail(RefNum="ref-OTHER"))
        with pytest.raises(SepResponseError, match="different receipt"):
            client_for(Script(json_response(body))).verify_callback(
                callback, expected_amount=12_000
            )

    def test_the_gateway_answering_for_another_terminal(self) -> None:
        callback = parse_callback({"State": "OK", "RefNum": "ref-1"})
        body = ok_body(TransactionDetail=ok_detail(TerminalNumber=999))
        with pytest.raises(SepResponseError, match="different terminal"):
            client_for(Script(json_response(body))).verify_callback(
                callback, expected_amount=12_000
            )


class TestResilience:
    def test_a_lost_verify_is_retried(self) -> None:
        script = Script(httpx.ReadTimeout("slow"), json_response(ok_body()))
        assert client_for(script).verify_transaction("ref-1").amount == 12_000
        assert len(script.requests) == 2

    def test_5xx_on_verify_is_retried(self) -> None:
        script = Script(json_response({}, 503), json_response({}, 502), json_response(ok_body()))
        assert client_for(script).verify_transaction("ref-1").amount == 12_000
        assert len(script.requests) == 3

    def test_retries_are_bounded(self) -> None:
        script = Script(json_response({}, 503))
        with pytest.raises(SepHTTPError) as raised:
            client_for(script).verify_transaction("ref-1")
        assert raised.value.status_code == 503
        assert len(script.requests) == 3

    def test_exhausted_transport_retries_raise_a_typed_error(self) -> None:
        script = Script(httpx.ReadTimeout("slow"))
        with pytest.raises(SepTimeoutError):
            client_for(script).verify_transaction("ref-1")
        assert len(script.requests) == 3

    def test_connection_failures_are_typed(self) -> None:
        script = Script(httpx.ConnectError("refused"))
        with pytest.raises(SepConnectionError):
            client_for(script).verify_transaction("ref-1")

    def test_a_token_is_not_repeated_after_the_bank_may_have_seen_it(self) -> None:
        script = Script(httpx.ReadTimeout("slow"))
        with pytest.raises(SepTimeoutError):
            client_for(script).create_token(ORDER)
        assert len(script.requests) == 1
        script = Script(json_response({}, 503))
        with pytest.raises(SepHTTPError):
            client_for(script).create_token(ORDER)
        assert len(script.requests) == 1

    def test_a_token_is_retried_when_the_connection_never_opened(self) -> None:
        script = Script(
            httpx.ConnectError("refused"), json_response({"status": 1, "token": "abcdefgh12"})
        )
        assert client_for(script).create_token(ORDER).token == "abcdefgh12"
        assert len(script.requests) == 2

    def test_real_backoff_sleeps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        slept: list[float] = []
        monkeypatch.setattr("sep_sdk.client.time.sleep", slept.append)
        script = Script(
            httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow"), json_response(ok_body())
        )
        client_for(script, retry=RetryPolicy(backoff_factor=0.5)).verify_transaction("ref-1")
        assert slept == [0.5, 1.0]

    def test_no_retry_policy(self) -> None:
        script = Script(httpx.ReadTimeout("slow"))
        with pytest.raises(SepTimeoutError):
            client_for(script, retry=RetryPolicy.none()).verify_transaction("ref-1")
        assert len(script.requests) == 1


class TestEndpointFallback:
    def test_the_other_spelling_is_tried_once_on_404(self, fake: FakeSepGateway) -> None:
        fake.spelling = "transcation"
        with SepClient(
            TERMINAL, endpoints=fake.endpoints, transport=fake.transport, retry=NO_WAIT
        ) as sep:
            token = sep.create_token(ORDER)
            ref = fake.complete_payment(token.token)["RefNum"]
            assert sep.verify_transaction(ref).amount == 12_000
            sep.verify_transaction(ref)
        urls = [c.url for c in fake.calls if c.operation == "verify"]
        assert [u.rsplit("/", 1)[1] for u in urls] == [
            "VerifyTransaction",
            "VerifyTranscation",
            "VerifyTranscation",
        ]

    def test_reverse_has_its_own_fallback(self, fake: FakeSepGateway) -> None:
        fake.spelling = "transcation"
        with SepClient(
            TERMINAL, endpoints=fake.endpoints, transport=fake.transport, retry=NO_WAIT
        ) as sep:
            ref = fake.complete_payment(sep.create_token(ORDER).token)["RefNum"]
            sep.verify_transaction(ref)
            assert sep.reverse_transaction(ref)

    def test_a_real_404_is_reported_after_the_one_fallback(self) -> None:
        script = Script(json_response({}, 404))
        with pytest.raises(SepHTTPError) as raised:
            client_for(script).verify_transaction("ref-1")
        assert raised.value.status_code == 404
        assert len(script.requests) == 2

    def test_fallback_can_be_disabled(self) -> None:
        script = Script(json_response({}, 404))
        with pytest.raises(SepHTTPError):
            client_for(script, endpoint_fallback=False).verify_transaction("ref-1")
        assert len(script.requests) == 1

    def test_the_token_call_has_no_alternate(self) -> None:
        script = Script(json_response({}, 404))
        with pytest.raises(SepHTTPError):
            client_for(script, endpoints=Endpoints.legacy()).create_token(ORDER)
        assert len(script.requests) == 1
