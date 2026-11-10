import importlib.metadata
import logging
from pathlib import Path

import httpx
import pytest

import sep_sdk
from sep_sdk import SepClient, SepConnectionError, SepHTTPError, TokenRequest, TransactionState
from sep_sdk.testing import FakeSepGateway
from tests.conftest import CALLBACK_URL, NO_WAIT, TERMINAL

ORDER = TokenRequest(amount=12_000, res_num="order-1", redirect_url=CALLBACK_URL)


def test_callback_fields_look_like_the_banks() -> None:
    fake = FakeSepGateway(terminal_id=TERMINAL)
    with SepClient(TERMINAL, endpoints=fake.endpoints, transport=fake.transport) as sep:
        token = sep.create_token(ORDER)
    paid = fake.complete_payment(token.token)
    assert paid["State"] == "OK"
    assert paid["Status"] == "2"
    assert paid["ResNum"] == "order-1"
    assert paid["Token"] == token.token
    cancelled = fake.end_payment(token.token)
    assert cancelled["State"] == "CanceledByUser"
    assert cancelled["RefNum"] == ""
    assert fake.end_payment(token.token, TransactionState.SESSION_IS_NULL)["Status"] == "4"


def test_unknown_tokens_are_a_test_bug() -> None:
    with pytest.raises(KeyError, match="Unknown token"):
        FakeSepGateway().complete_payment("nope")


def test_the_fake_refuses_a_foreign_terminal() -> None:
    fake = FakeSepGateway(terminal_id="1")
    with (
        SepClient("2", endpoints=fake.endpoints, transport=fake.transport) as sep,
        pytest.raises(sep_sdk.SepTokenError) as raised,
    ):
        sep.create_token(ORDER)
    assert raised.value.code == 12


def test_unknown_paths_404() -> None:
    fake = FakeSepGateway()
    response = httpx.Client(transport=fake.transport).post("https://fake.sep.test/other", json={})
    assert response.status_code == 404


def test_both_spellings_can_answer() -> None:
    fake = FakeSepGateway(terminal_id=TERMINAL, spelling="both")
    with SepClient(TERMINAL, endpoints=fake.endpoints, transport=fake.transport) as sep:
        ref = fake.complete_payment(sep.create_token(ORDER).token)["RefNum"]
        assert sep.verify_transaction(ref).amount == 12_000
    assert len([c for c in fake.calls if c.operation == "verify"]) == 1


def test_injected_failures_are_consumed_in_order() -> None:
    fake = FakeSepGateway(terminal_id=TERMINAL)
    with SepClient(
        TERMINAL, endpoints=fake.endpoints, transport=fake.transport, retry=NO_WAIT
    ) as sep:
        fake.fail_next(operation="token", status_code=500)
        with pytest.raises(SepHTTPError):
            sep.create_token(ORDER)
        fake.drop_next()
        fake.drop_next(operation="verify")
        token = sep.create_token(ORDER)  # the unscoped drop is retried: connect errors are safe
        ref = fake.complete_payment(token.token)["RefNum"]
        assert sep.verify_transaction(ref).amount == 12_000


def test_a_dropped_call_surfaces_as_a_connection_error() -> None:
    fake = FakeSepGateway(terminal_id=TERMINAL)
    with SepClient(
        TERMINAL, endpoints=fake.endpoints, transport=fake.transport, retry=NO_WAIT
    ) as sep:
        for _ in range(3):
            fake.drop_next(operation="token")
        with pytest.raises(SepConnectionError):
            sep.create_token(ORDER)


def test_public_api_is_importable_and_listed() -> None:
    for name in sep_sdk.__all__:
        assert hasattr(sep_sdk, name), name


def test_the_version_matches_the_installed_metadata() -> None:
    try:
        installed = importlib.metadata.version("sep-python-sdk")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("package is not installed")
    assert installed == sep_sdk.__version__


def test_the_client_can_render_the_redirect_form() -> None:
    fake = FakeSepGateway(terminal_id=TERMINAL)
    with SepClient(TERMINAL, endpoints=fake.endpoints, transport=fake.transport) as sep:
        token = sep.create_token(ORDER)
        page = sep.render_redirect_form(token, language="fa", nonce="n")
    assert token.token in page
    assert 'nonce="n"' in page
    assert 'dir="rtl"' in page


def test_the_package_is_marked_typed() -> None:
    assert (Path(sep_sdk.__file__).parent / "py.typed").is_file()


def test_the_library_stays_silent_by_default() -> None:
    handlers = logging.getLogger("sep_sdk").handlers
    assert any(isinstance(h, logging.NullHandler) for h in handlers)
