from __future__ import annotations

import logging

import httpx
import pytest

from sep_sdk import (
    AmountMismatchError,
    AsyncSepClient,
    PaymentNotCompletedError,
    RetryPolicy,
    SepConnectionError,
    SepHTTPError,
    SepTimeoutError,
    TokenRequest,
    TransactionNotFoundError,
    TransactionState,
    parse_callback,
)
from sep_sdk.testing import FakeSepGateway
from tests.conftest import CALLBACK_URL, NO_WAIT, TERMINAL
from tests.helpers import Script, json_response, ok_body

ORDER = TokenRequest(amount=12_000, res_num="order-1", redirect_url=CALLBACK_URL)


def client_for(script: Script, **options: object) -> AsyncSepClient:
    options.setdefault("retry", NO_WAIT)
    return AsyncSepClient(TERMINAL, transport=script.transport, **options)  # type: ignore[arg-type]


async def test_the_whole_flow(aclient: AsyncSepClient, fake: FakeSepGateway) -> None:
    token = await aclient.create_token(ORDER)
    fields = fake.complete_payment(token.token)
    result = await aclient.verify_callback(parse_callback(fields), expected_amount=12_000)
    assert result.amount == 12_000
    assert (await aclient.verify_transaction(result.ref_num)).is_duplicate
    assert not (await aclient.reverse_transaction(result.ref_num)).is_duplicate


async def test_unpaid_callbacks_are_refused(aclient: AsyncSepClient, fake: FakeSepGateway) -> None:
    token = await aclient.create_token(ORDER)
    callback = parse_callback(fake.end_payment(token.token, TransactionState.FAILED))
    with pytest.raises(PaymentNotCompletedError):
        await aclient.verify_callback(callback, expected_amount=12_000)


async def test_unknown_receipts(aclient: AsyncSepClient) -> None:
    with pytest.raises(TransactionNotFoundError):
        await aclient.verify_transaction("nope")


async def test_mismatch_and_automatic_reversal(
    aclient: AsyncSepClient, fake: FakeSepGateway
) -> None:
    token = await aclient.create_token(ORDER)
    callback = parse_callback(fake.complete_payment(token.token, paid_amount=1))
    with pytest.raises(AmountMismatchError) as raised:
        await aclient.verify_callback(callback, expected_amount=12_000)
    assert raised.value.reversed is False

    token = await aclient.create_token(ORDER)
    callback = parse_callback(fake.complete_payment(token.token, paid_amount=1))
    with pytest.raises(AmountMismatchError) as raised:
        await aclient.verify_callback(callback, expected_amount=12_000, reverse_on_mismatch=True)
    assert raised.value.reversed is True


async def test_a_failed_reversal_is_reported(
    aclient: AsyncSepClient, fake: FakeSepGateway, caplog: pytest.LogCaptureFixture
) -> None:
    token = await aclient.create_token(ORDER)
    callback = parse_callback(fake.complete_payment(token.token, paid_amount=1))
    fake.fail_next(operation="reverse", status_code=403)
    with (
        caplog.at_level(logging.ERROR, logger="sep_sdk"),
        pytest.raises(AmountMismatchError) as raised,
    ):
        await aclient.verify_callback(callback, expected_amount=12_000, reverse_on_mismatch=True)
    assert raised.value.reversed is False
    assert "could not reverse" in caplog.text


async def test_retries_lost_verify_calls() -> None:
    script = Script(httpx.ReadTimeout("slow"), json_response({}, 503), json_response(ok_body()))
    async with client_for(script) as sep:
        assert (await sep.verify_transaction("ref-1")).amount == 12_000
    assert len(script.requests) == 3


async def test_error_types_after_the_last_attempt() -> None:
    async with client_for(Script(httpx.ReadTimeout("slow"))) as sep:
        with pytest.raises(SepTimeoutError):
            await sep.verify_transaction("ref-1")
    async with client_for(Script(httpx.ConnectError("refused"))) as sep:
        with pytest.raises(SepConnectionError):
            await sep.verify_transaction("ref-1")
    async with client_for(Script(json_response({}, 503))) as sep:
        with pytest.raises(SepHTTPError):
            await sep.create_token(ORDER)


async def test_tokens_are_not_repeated_after_a_read_timeout() -> None:
    script = Script(httpx.ReadTimeout("slow"))
    async with client_for(script) as sep:
        with pytest.raises(SepTimeoutError):
            await sep.create_token(ORDER)
    assert len(script.requests) == 1


async def test_backoff_really_sleeps(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr("sep_sdk.async_client.asyncio.sleep", fake_sleep)
    script = Script(httpx.ReadTimeout("slow"), json_response(ok_body()))
    async with client_for(script, retry=RetryPolicy(backoff_factor=0.25)) as sep:
        await sep.verify_transaction("ref-1")
    assert slept == [0.25]


async def test_endpoint_fallback(fake: FakeSepGateway) -> None:
    fake.spelling = "transcation"
    async with AsyncSepClient(TERMINAL, endpoints=fake.endpoints, transport=fake.transport) as sep:
        ref = fake.complete_payment((await sep.create_token(ORDER)).token)["RefNum"]
        assert (await sep.verify_transaction(ref)).amount == 12_000


async def test_an_external_http_client_stays_open() -> None:
    http = httpx.AsyncClient()
    await AsyncSepClient(TERMINAL, http_client=http).aclose()
    assert not http.is_closed
    await http.aclose()


async def test_an_owned_client_is_closed() -> None:
    async with AsyncSepClient(TERMINAL) as sep:
        http = sep._http
    assert http.is_closed
