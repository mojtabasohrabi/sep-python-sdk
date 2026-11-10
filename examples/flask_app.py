"""Flask: the same flow with the synchronous client."""

from flask import Flask, redirect, request

from sep_sdk import (
    SepClient,
    SepError,
    TokenRequest,
    derive_session_key,
    parse_callback,
    render_redirect_form,
)

TERMINAL_ID = "12345678"
SERVER_SECRET = "load-me-from-the-environment"
ORDERS = {"order-1001": 150_000}
USED_RECEIPTS: set[str] = set()

app = Flask(__name__)
sep = SepClient(TERMINAL_ID)


@app.get("/pay/<order_id>")
def pay(order_id: str) -> str:
    token = sep.create_token(
        TokenRequest(
            amount=ORDERS[order_id],
            res_num=order_id,
            redirect_url="https://shop.example/payments/callback",
            session_key=derive_session_key(SERVER_SECRET, order_id),
        )
    )
    return render_redirect_form(token, language="fa")


@app.route("/payments/callback", methods=["GET", "POST"])
def callback():  # type: ignore[no-untyped-def]
    data = parse_callback(request.values)  # form fields or query string
    order_id = data.res_num
    if order_id not in ORDERS:
        return redirect("/failed")
    try:
        result = sep.verify_callback(
            data,
            expected_amount=ORDERS[order_id],
            session_key=derive_session_key(SERVER_SECRET, order_id),
            reverse_on_mismatch=True,
        )
    except SepError:
        return redirect("/failed")
    if result.ref_num in USED_RECEIPTS:
        return redirect("/failed")
    USED_RECEIPTS.add(result.ref_num)
    return redirect("/thanks")
