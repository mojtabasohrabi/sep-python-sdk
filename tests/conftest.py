from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest

from sep_sdk import AsyncSepClient, RetryPolicy, SepClient
from sep_sdk.testing import FakeSepGateway

TERMINAL = "12345678"
CALLBACK_URL = "https://shop.example/payments/callback"
NO_WAIT = RetryPolicy(max_attempts=3, backoff_factor=0)


@pytest.fixture
def fake() -> FakeSepGateway:
    return FakeSepGateway(terminal_id=TERMINAL)


@pytest.fixture
def client(fake: FakeSepGateway) -> Iterator[SepClient]:
    with SepClient(
        TERMINAL, endpoints=fake.endpoints, transport=fake.transport, retry=NO_WAIT
    ) as sep:
        yield sep


@pytest.fixture
async def aclient(fake: FakeSepGateway) -> AsyncIterator[AsyncSepClient]:
    async with AsyncSepClient(
        TERMINAL, endpoints=fake.endpoints, transport=fake.transport, retry=NO_WAIT
    ) as sep:
        yield sep
