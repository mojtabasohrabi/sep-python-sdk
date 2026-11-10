"""The whole payment flow, offline, against the in-memory fake gateway.

Run it with ``python examples/offline_demo.py``. Nothing leaves your machine.
"""

from sep_sdk import SepClient, TokenRequest, parse_callback, render_redirect_form
from sep_sdk.testing import FakeSepGateway

TERMINAL_ID = "12345678"
ORDER_TOTAL_RIALS = 150_000


def main() -> None:
    fake = FakeSepGateway(terminal_id=TERMINAL_ID)

    with SepClient(TERMINAL_ID, endpoints=fake.endpoints, transport=fake.transport) as sep:
        # 1. Ask for a token for one order.
        token = sep.create_token(
            TokenRequest(
                amount=ORDER_TOTAL_RIALS,
                res_num="order-1001",
                redirect_url="https://shop.example/payments/callback",
            )
        )
        print("token created:", token)

        # 2. Send the customer to the bank (serve this page from your own site).
        page = render_redirect_form(token, language="fa")
        print("redirect page is", len(page), "bytes of HTML")

        # 3. The customer pays; the bank posts these fields to your callback URL.
        posted_by_the_bank = fake.complete_payment(token.token)

        # 4. Parse, then verify. Never mark an order paid from the callback alone.
        callback = parse_callback(posted_by_the_bank)
        result = sep.verify_callback(callback, expected_amount=ORDER_TOTAL_RIALS)
        print("paid! receipt:", result.ref_num, "amount:", result.amount)


if __name__ == "__main__":
    main()
