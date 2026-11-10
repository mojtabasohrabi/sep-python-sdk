"""FastAPI: start a payment and handle the bank's callback (async client).

Run with ``uvicorn examples.fastapi_app:app``. Replace ``ORDERS`` with your database.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from sep_sdk import (
    AmountMismatchError,
    AsyncSepClient,
    PaymentNotCompletedError,
    SepError,
    TokenRequest,
    derive_session_key,
    parse_callback,
    render_redirect_form,
)

TERMINAL_ID = "12345678"
SERVER_SECRET = "load-me-from-the-environment"
ORDERS: dict[str, int] = {"order-1001": 150_000}  # order id -> total in rials
PAID: set[str] = set()  # receipts already used

sep: AsyncSepClient


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    global sep
    async with AsyncSepClient(TERMINAL_ID) as sep:
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/pay/{order_id}", response_class=HTMLResponse)
async def pay(order_id: str) -> str:
    if order_id not in ORDERS:
        raise HTTPException(404)
    token = await sep.create_token(
        TokenRequest(
            amount=ORDERS[order_id],
            res_num=order_id,
            redirect_url="https://shop.example/payments/callback",
            session_key=derive_session_key(SERVER_SECRET, order_id),
        )
    )
    return render_redirect_form(token, language="fa")


# The bank POSTs form fields here. Anyone else can too: that is why we verify.
@app.post("/payments/callback")
async def callback(
    State: str = Form(""),  # noqa: N803
    RefNum: str = Form(""),  # noqa: N803
    ResNum: str = Form(""),  # noqa: N803
    TerminalId: str = Form(""),  # noqa: N803
    Status: str = Form(""),  # noqa: N803
) -> RedirectResponse:
    data = parse_callback(
        {
            "State": State,
            "RefNum": RefNum,
            "ResNum": ResNum,
            "TerminalId": TerminalId,
            "Status": Status,
        }
    )
    order_id = data.res_num
    if order_id not in ORDERS:
        return RedirectResponse("/failed", status_code=303)
    try:
        result = await sep.verify_callback(
            data,
            expected_amount=ORDERS[order_id],  # from YOUR records, never from the request
            session_key=derive_session_key(SERVER_SECRET, order_id),
            reverse_on_mismatch=True,
        )
    except (PaymentNotCompletedError, AmountMismatchError, SepError):
        return RedirectResponse("/failed", status_code=303)
    if result.ref_num in PAID:  # a receipt may be used exactly once
        return RedirectResponse("/failed", status_code=303)
    PAID.add(result.ref_num)
    return RedirectResponse("/thanks", status_code=303)
