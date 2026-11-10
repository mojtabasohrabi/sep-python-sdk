import httpx
import pytest

from sep_sdk import AsyncSepClient, SepClient, SepValidationError, TokenRequest, parse_callback
from sep_sdk.testing import FakeSepGateway
from tests.conftest import CALLBACK_URL


@pytest.mark.parametrize("key", [1, 2**63 - 1, "123456789", str(2**63 - 1)])
def test_sync_token_verify_and_reverse_send_the_same_integer(
    client: SepClient, fake: FakeSepGateway, key: str | int
) -> None:
    token = client.create_token(
        TokenRequest(amount=12_000, res_num="order", redirect_url=CALLBACK_URL, session_key=key)
    )
    callback = parse_callback(fake.complete_payment(token.token))
    assert (
        client.verify_callback(callback, expected_amount=12_000, session_key=key).amount == 12_000
    )
    client.reverse_transaction(callback.ref_num, session_key=key)
    assert [call.operation for call in fake.calls] == ["token", "verify", "reverse"]
    for call in fake.calls:
        value = call.body["TxnRandomSessionKey"]
        assert type(value) is int
        assert value == int(key)


@pytest.mark.parametrize("key", [2**63 - 1, "123456789"])
async def test_async_token_verify_and_reverse_send_the_same_integer(
    aclient: AsyncSepClient, fake: FakeSepGateway, key: str | int
) -> None:
    token = await aclient.create_token(
        TokenRequest(amount=12_000, res_num="order", redirect_url=CALLBACK_URL, session_key=key)
    )
    callback = parse_callback(fake.complete_payment(token.token))
    result = await aclient.verify_callback(callback, expected_amount=12_000, session_key=key)
    assert result.amount == 12_000
    await aclient.reverse_transaction(callback.ref_num, session_key=key)
    assert [call.operation for call in fake.calls] == ["token", "verify", "reverse"]
    for call in fake.calls:
        value = call.body["TxnRandomSessionKey"]
        assert type(value) is int
        assert value == int(key)


@pytest.mark.parametrize("key", ["a" * 32, "not-a-number", 0, 2**63, True])
def test_invalid_keys_fail_before_any_network_call(
    client: SepClient, fake: FakeSepGateway, key: str | int
) -> None:
    with pytest.raises(SepValidationError, match="session_key"):
        TokenRequest(amount=12_000, res_num="order", redirect_url=CALLBACK_URL, session_key=key)
    with pytest.raises(SepValidationError, match="session_key"):
        client.verify_transaction("receipt", session_key=key)
    with pytest.raises(SepValidationError, match="session_key"):
        client.reverse_transaction("receipt", session_key=key)
    assert fake.calls == []


@pytest.mark.parametrize("operation", ["token", "verify", "reverse"])
@pytest.mark.parametrize("key", ["123", "a" * 32, True, 0, 2**63])
def test_fake_rejects_the_same_bad_wire_format_as_the_real_gateway(
    fake: FakeSepGateway, operation: str, key: object
) -> None:
    url = {
        "token": fake.endpoints.token_url,
        "verify": fake.endpoints.verify_url,
        "reverse": fake.endpoints.reverse_url,
    }[operation]
    with httpx.Client(transport=fake.transport) as http:
        response = http.post(url, json={"TxnRandomSessionKey": key})
    assert response.status_code == 400
    assert "model.TxnRandomSessionKey" in response.json()["ModelState"]
