# sep-python-sdk

**English** · [فارسی](README.fa.md)

[![CI](https://github.com/mojtabasohrabi/sep-python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/mojtabasohrabi/sep-python-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sep-python-sdk.svg)](https://pypi.org/project/sep-python-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/sep-python-sdk.svg)](https://pypi.org/project/sep-python-sdk/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Typed](https://img.shields.io/badge/typing-strict-blue.svg)](#typing)

A typed, tested Python SDK for the **Saman Electronic Payment (SEP) online payment gateway**
(`sep.shaparak.ir`): request a token, send the customer to the bank, read the callback, verify
the money and reverse it if you must. Synchronous and `asyncio` clients, no framework required.

> **Unofficial.** This project is not affiliated with, endorsed by, or supported by Saman
> Electronic Payment. It implements the public integration guide (version 3.6). "SEP" and
> "Saman" belong to their owners.

## Contents

- [Features](#features)
- [Install](#install)
- [How a payment works](#how-a-payment-works)
- [Quick start](#quick-start)
- [Guide](#guide)
  - [1. The client](#1-the-client)
  - [2. Create a token](#2-create-a-token)
  - [3. Send the customer to the bank](#3-send-the-customer-to-the-bank)
  - [4. Read the callback](#4-read-the-callback)
  - [5. Verify the payment](#5-verify-the-payment)
  - [6. Reverse a payment](#6-reverse-a-payment)
  - [7. Bind the receipt to the order (session key)](#7-bind-the-receipt-to-the-order-session-key)
  - [8. Multi-account and government payments](#8-multi-account-and-government-payments)
  - [9. Async](#9-async)
  - [10. Errors](#10-errors)
  - [11. Timeouts and retries](#11-timeouts-and-retries)
  - [12. Logging](#12-logging)
  - [13. Testing your integration offline](#13-testing-your-integration-offline)
  - [14. Go-live checklist](#14-go-live-checklist)
- [Framework examples](#framework-examples)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Typing](#typing)
- [Compatibility and versioning](#compatibility-and-versioning)
- [Contributing](#contributing) · [Security](#security) · [License](#license)

## Features

- **Complete protocol coverage** — token, redirect (POST form and GET link), callback,
  `VerifyTransaction`, `ReverseTransaction`, multi-account (`MultiSettle`) and government
  (`Government`) payments, allowed-card lists, wage, extra data, token expiry, `GetMethod`,
  `TxnRandomSessionKey`, and `neo-pg` terminals (`X-IPG-Url`).
- **Safe by construction** — `verify_callback()` refuses unpaid callbacks, checks the receipt,
  the terminal **and the amount**, and can reverse a mismatched payment for you.
- **Sync and async** — `SepClient` and `AsyncSepClient` share one implementation of every rule.
- **Strictly typed** — `py.typed`, frozen dataclasses, enums, `mypy --strict` clean.
- **Honest errors** — one exception hierarchy; every documented `ResultCode` has its own class.
- **Resilient** — exponential backoff that never repeats a call that could double-charge,
  and a one-time fallback between the two path spellings Saman uses in the wild.
- **Offline tests included** — `FakeSepGateway` simulates the bank so your tests never need a
  terminal, a whitelisted IP or a network.
- **Tiny** — one runtime dependency: [`httpx`](https://www.python-httpx.org/). Python 3.10+.
- **Bilingual** — error and state messages in English and Persian; docs in both languages.

## Install

```bash
pip install sep-python-sdk
```

You need a **terminal number** from Saman, and your server's public IP must be registered
with Saman (token and verify calls are refused otherwise).

## How a payment works

```
 your server                         customer's browser                     Saman (SEP)
     │  1. create_token(amount, order id, callback URL) ───────────────────────►│
     │◄────────────────────────────────────────────── token ────────────────────│
     │  2. page with a POST form (render_redirect_form) ─►│                     │
     │                                                    │  3. form POST ─────►│  customer pays
     │                                                    │◄── 4. redirect ─────│
     │◄─ 5. POST/GET to your callback: State, RefNum, ResNum, … ────────────────│
     │  6. verify_transaction(RefNum) ──────────────────────────────────────────►│
     │◄──────────────────── amount actually taken ───────────────────────────────│
     │  7. compare with YOUR order total → deliver the goods                     │
```

Two rules the whole SDK is built around:

1. **The callback is not proof.** Anyone can send your callback URL any parameters. Only the
   server-to-server verify call proves the money is there.
2. **Verify within 30 minutes**, or Saman reverses the payment by itself.

## Quick start

```python
from sep_sdk import SepClient, TokenRequest, parse_callback, render_redirect_form

sep = SepClient(terminal_id="12345678")

# 1. Start: one token per payment attempt. Amounts are in RIALS.
token = sep.create_token(
    TokenRequest(
        amount=150_000,
        res_num="order-1001",  # your unique order / attempt id
        redirect_url="https://shop.example/payments/callback",
    )
)

# 2. Send the customer to the bank: return this HTML from a page on your own site.
html = render_redirect_form(token, language="fa")

# 3. In your callback view, the bank posts the result. Parse it, then VERIFY it.
callback = parse_callback(request_form_or_query)            # a dict-like object
result = sep.verify_callback(callback, expected_amount=150_000)  # raises unless truly paid

# 4. Only now: mark the order paid and store result.ref_num (it must be unique).
print(result.ref_num, result.amount)
```

Try the whole flow offline, without a terminal: `python examples/offline_demo.py`.

---

## Guide

### 1. The client

```python
from sep_sdk import SepClient

with SepClient(terminal_id="12345678") as sep:   # closes the connection pool on exit
    ...
```

| Argument | Default | Meaning |
|---|---|---|
| `terminal_id` | – | Your numeric terminal number (`str` or `int`). |
| `endpoints` | production | An [`Endpoints`](#endpoints) object, to override or fake any URL. |
| `timeout` | 20 s (5 s connect) | A `float` or `httpx.Timeout`. |
| `retry` | 3 attempts | A [`RetryPolicy`](#11-timeouts-and-retries). |
| `endpoint_fallback` | `True` | Try the alternative path spelling once on HTTP 404. |
| `transport` | – | An `httpx` transport (tests, proxies). |
| `http_client` | – | Your own `httpx.Client`; you then close it. |

Create **one client per process** and reuse it; it keeps connections alive.

#### Endpoints

```python
from sep_sdk import Endpoints, SepClient

SepClient("12345678", endpoints=Endpoints.production())     # the default
SepClient("12345678", endpoints=Endpoints.legacy())         # "…Transcation" first
SepClient("12345678", endpoints=Endpoints.without_fallback())
```

### 2. Create a token

```python
from sep_sdk import TokenRequest

token = sep.create_token(
    TokenRequest(
        amount=150_000,                      # rials, integer, > 0
        res_num="order-1001",                # unique per attempt
        redirect_url="https://shop.example/payments/callback",
    )
)
token.token               # the payment token (hidden from repr())
token.expires_in_minutes  # 20 unless you changed it
```

All `TokenRequest` fields (everything but the first three is optional). Invalid values raise
`SepValidationError` **before** anything is sent.

| Field | Guide name | Notes |
|---|---|---|
| `amount` | `Amount` | Rials, integer. |
| `res_num` | `ResNum` | Your order / attempt id. Make it unique: it is your only handle if the customer paid but your server never heard back. |
| `redirect_url` | `RedirectUrl` | Your callback. `http(s)`, max 2083 characters (1538 with `callback_method="GET"`). |
| `wage` | `Wage` | Fee, for merchants who split payments. |
| `cell_number` | `CellNumber` | Customer mobile, so Saman can offer saved cards. Accepts `0912…`, `+98912…`, `912…`, Persian digits. |
| `token_expiry_minutes` | `TokenExpiryInMin` | 20 – 3600. |
| `allowed_cards` | `HashedCardNumber` | Up to 10 MD5 hashes; only those cards may pay. Use `hash_card_number()`. |
| `extra_data` | `ResNum1…4` | Up to 4 strings of ≤ 50 chars, visible only in Saman's reports. |
| `session_key` | `TxnRandomSessionKey` | See [section 7](#7-bind-the-receipt-to-the-order-session-key). |
| `settlement` | `SettlementIbanInfo` | See [section 8](#8-multi-account-and-government-payments). |
| `government` | `TranType=Government` | See section 8. |
| `callback_method` | `GetMethod` | `"POST"` (default) or `"GET"`. |

```python
from sep_sdk import hash_card_number

TokenRequest(
    amount=150_000, res_num="order-1002", redirect_url="https://shop.example/cb",
    cell_number="09123456789",
    token_expiry_minutes=60,
    allowed_cards=[hash_card_number("6037 9912 3456 7890")],  # only this card may pay
    extra_data=["invoice 2026-17", "campaign spring"],
)
```

> `hash_card_number` never stores or logs the number. The guide forbids storing card numbers:
> keep only the hash.

### 3. Send the customer to the bank

The customer's **browser** must go to Saman. Use the form, which works for every terminal:

```python
from sep_sdk import render_redirect_form

html = render_redirect_form(token, language="fa", nonce=csp_nonce_or_None)
# return it as an HTML response from a page on YOUR site
```

It renders a page that POSTs `Token` to the bank at once (and shows a button if JavaScript is
off). Every value is HTML-escaped; pass `nonce=` if your Content-Security-Policy needs one.

**Important:** Saman refuses visitors who arrive without a `Referer` from your site. Serve the
form from your own domain, don't send `Referrer-Policy: no-referrer` on that page (the form
already includes `<meta name="referrer" content="origin">`), and don't open the bank URL from a
mobile app directly: open your own page in a browser instead.

Prefer to template it yourself?

```python
from sep_sdk import redirect_form_fields

redirect_form_fields(token)   # {"Token": "…"} (+ "GetMethod": "true" for GET callbacks)
token.form_action             # where to POST it
```

A plain link also exists for classic terminals: `token.get_url`
(`https://sep.shaparak.ir/OnlinePG/SendToken?token=…`). Terminals moved to **neo-pg** return an
`X-IPG-Url` header; then `token.ipg_url` is set, `token.get_url` is `None`, and the form's
`action` already points at the new address.

### 4. Read the callback

After the payment Saman redirects the customer to your `redirect_url` carrying the result
(`POST` form fields, or a query string with `callback_method="GET"`).

```python
from sep_sdk import parse_callback

callback = parse_callback(request.POST)        # Django QueryDict, Flask request.values,
                                               # a plain dict, parse_qs(...) output…
callback.res_num      # your order id (ResNum)
callback.ref_num      # the bank's receipt (RefNum)
callback.state        # TransactionState.OK, CANCELED_BY_USER, FAILED, …
callback.is_ok        # State == OK, a receipt exists, and Status (if sent) agrees
callback.amount       # what the bank *says* it took: NOT trustworthy
callback.state.message("fa")   # a customer-friendly explanation (also "en")
```

`parse_callback` makes **no network call** and trusts nothing. Names are matched
case-insensitively; list values are flattened; the card-related fields are hidden from `repr`.

| `TransactionState` | Meaning |
|---|---|
| `OK` | The bank reports a completed payment (still: verify!). |
| `CANCELED_BY_USER` | The customer cancelled. |
| `FAILED` | Payment failed. |
| `SESSION_IS_NULL` | The customer did not respond in time. |
| `INVALID_PARAMETERS` | Parameters sent to the bank were invalid. |
| `MERCHANT_IP_ADDRESS_IS_INVALID` | Your server IP is not registered with Saman. |
| `TOKEN_NOT_FOUND` / `TOKEN_REQUIRED` | Unknown token / terminal accepts token payments only. |
| `TERMINAL_NOT_FOUND` | Unknown terminal number. |
| `MULTISETTLE_POLICY_ERRORS` | Multi-account rules were violated. |
| `UNKNOWN` | A value this SDK version does not know — treated as *not paid*. |

### 5. Verify the payment

The one call you should use:

```python
from sep_sdk import AmountMismatchError, PaymentNotCompletedError, SepError

order = orders.get(callback.res_num)           # YOUR record, found by your order id
try:
    result = sep.verify_callback(
        callback,
        expected_amount=order.total_rials,     # from your database, NEVER from the request
        session_key=order.session_key,         # if you used one
        reverse_on_mismatch=True,              # refund automatically if the amount differs
    )
except PaymentNotCompletedError as error:      # cancelled / failed: nothing to verify
    show(error.state.message("fa"))
except AmountMismatchError as error:           # the bank took another sum
    log.error("tampered payment: %s vs %s, reversed=%s", error.expected, error.actual, error.reversed)
except SepError:                               # network, gateway refusal, bad answer…
    schedule_retry_within_30_minutes(callback.ref_num)
else:
    # Receipts may be used ONCE. Store ref_num in a UNIQUE column; a duplicate = replay.
    order.mark_paid(receipt=result.ref_num)
```

`verify_callback` does, in order:

1. refuses a callback whose `State` isn't a clean `OK` (`PaymentNotCompletedError`, no network);
2. refuses a callback for another terminal;
3. calls `VerifyTransaction`;
4. checks the answer is for the **same receipt and terminal**;
5. checks the bank took exactly `expected_amount` rials (`AmountMismatchError`; with
   `reverse_on_mismatch=True` it also reverses, and `error.reversed` tells you the outcome).

Need finer control? Call the primitive yourself:

```python
result = sep.verify_transaction(callback.ref_num, session_key=order.session_key)
result.amount             # OrginalAmount: compare with YOUR total
result.detail.affective_amount   # what left the card (differs on discount terminals)
result.detail.trace_no, result.detail.rrn, result.detail.trace_date
result.is_duplicate       # True when Saman says "this request was already processed"
```

If the verify call fails because of the network, **retry**: Saman keeps the receipt valid and
answers a repeat with "duplicate request". The SDK already retries (see section 11); if it still
fails, try again within the 30-minute window — a background job that re-verifies unfinished
payments is a good idea.

### 6. Reverse a payment

```python
reversal = sep.reverse_transaction(ref_num)   # up to 50 minutes after the payment
reversal.is_duplicate                         # True if it was already reversed
```

### 7. Bind the receipt to the order (session key)

`TxnRandomSessionKey` ties the later verify call to the exact payment, so a receipt from one
(cheap) order cannot be replayed on another. Two ways to get a key:

```python
from sep_sdk import derive_session_key, generate_session_key

key = generate_session_key()                       # random; store it with the order
key = derive_session_key(SERVER_SECRET, order_id)  # or recompute it later, nothing to store
```

Pass it as `TokenRequest(session_key=key)` and again as
`verify_callback(..., session_key=key)`. If Saman rejects the extra field for your terminal,
simply don't send it. (The in-memory fake treats a missing or wrong key as "transaction not
found"; the real gateway's wording is not in the guide.)

### 8. Multi-account and government payments

Needs a terminal enabled for it by Saman.

```python
from sep_sdk import SettlementItem, TokenRequest

# Split one payment between several IBANs (at most 9 lines).
TokenRequest(
    amount=12_000, res_num="order-7", redirect_url="https://shop.example/cb",
    settlement=[
        SettlementItem(iban="IR062960000000100324200001", amount=7_000),
        SettlementItem(iban="IR000000000000000000000001", amount=5_000),
    ],
)

# Government payment: the FIRST line carries the government IBAN and its 30-digit id.
TokenRequest(
    amount=12_000, res_num="order-8", redirect_url="https://shop.example/cb",
    government=True,
    settlement=[
        SettlementItem(iban="IR062960000000100324200001", amount=7_000, purchase_id="1" * 30),
        SettlementItem(iban="IR000000000000000000000001", amount=5_000),  # padded with 30 zeros
    ],
)
```

IBANs are checked for shape (`IR` + 24 digits); `iban_checksum_ok(iban)` is available if you
also want the mod-97 check.

### 9. Async

`AsyncSepClient` has the same methods, awaited:

```python
from sep_sdk import AsyncSepClient

async with AsyncSepClient(terminal_id="12345678") as sep:
    token = await sep.create_token(request)
    result = await sep.verify_callback(callback, expected_amount=150_000)
```

### 10. Errors

Everything derives from `SepError`.

```
SepError
├── SepConfigurationError      bad terminal id / endpoints / retry policy   (also ValueError)
├── SepValidationError         request rejected locally, nothing was sent   (also ValueError)
├── SepTransportError          the outcome is unknown
│   ├── SepConnectionError
│   └── SepTimeoutError
├── SepHTTPError               unexpected HTTP status (.status_code)
├── SepResponseError           2xx but not what the guide describes
├── SepAPIError                the gateway refused (.code, .description, .operation)
│   ├── SepTokenError          token request refused (status = -1)
│   └── SepTransactionError    verify/reverse refused (.result_code)
│       ├── TransactionNotFoundError   -2
│       ├── VerifyWindowExpiredError   -6   (more than 30 minutes)
│       ├── TransactionReversedError    5
│       ├── TerminalError            -104 / -105
│       └── IPNotAllowedError        -106
├── PaymentNotCompletedError   callback says the customer did not pay (.state)
└── AmountMismatchError        the bank took another sum (.expected, .actual, .reversed)
```

`description` is text written by the gateway: log it, don't show it to customers verbatim.
For customer-facing text use `state.message("fa" | "en")` and `ResultCode.message(...)`.

### 11. Timeouts and retries

```python
import httpx
from sep_sdk import RetryPolicy, SepClient

SepClient(
    "12345678",
    timeout=httpx.Timeout(15.0, connect=3.0),
    retry=RetryPolicy(max_attempts=4, backoff_factor=0.5, max_backoff=8.0),
)
SepClient("12345678", retry=RetryPolicy.none())   # exactly one attempt
```

| Operation | Connection failed to open | Timeout / reset / 5xx / 429 |
|---|---|---|
| `verify`, `reverse` | retried | retried (Saman answers a repeat with "duplicate request") |
| `create_token` | retried | **not retried** — the bank may already have created a session |

HTTP 404 on verify/reverse triggers a one-time switch to the alternative path spelling
(`VerifyTransaction` ↔ `VerifyTranscation`), remembered for the client's lifetime.

### 12. Logging

The SDK logs under the `sep_sdk` logger (silent unless you configure it): debug for attempts,
warnings for retries and fallbacks, an error if an automatic reversal fails. Tokens, receipts,
card data and request bodies are **never** logged.

```python
import logging
logging.getLogger("sep_sdk").setLevel(logging.INFO)
```

### 13. Testing your integration offline

`FakeSepGateway` is an in-memory bank:

```python
from sep_sdk import SepClient, TokenRequest, parse_callback
from sep_sdk.testing import FakeSepGateway

fake = FakeSepGateway(terminal_id="12345678")
sep = SepClient("12345678", endpoints=fake.endpoints, transport=fake.transport)

token = sep.create_token(TokenRequest(amount=100_000, res_num="o-1", redirect_url="https://x.test/cb"))

fields = fake.complete_payment(token.token)            # what the bank would POST to you
fields = fake.complete_payment(token.token, paid_amount=1_000)  # a tampered payment
fields = fake.end_payment(token.token)                 # customer cancelled
fake.expire(ref_num)                                   # 30 minutes passed: verify → -6
fake.fail_next(status_code=503, operation="verify")    # HTTP error on the next verify
fake.drop_next()                                       # lose the next call (connection error)
FakeSepGateway(reject_ip=True)                         # server IP not registered
FakeSepGateway(neo_pg_url="https://neo-pg.sep.test/transaction/init")
FakeSepGateway(spelling="transcation")                 # exercise the endpoint fallback
fake.calls                                             # every request, for assertions
```

It follows the **guide**, not Saman's private behaviour. Treat it as a way to exercise your own
code paths, and still run one small real payment before launch. `AsyncSepClient` accepts
`transport=fake.transport` too.

### 14. Go-live checklist

- [ ] Your server's public IP is registered with Saman.
- [ ] `expected_amount` comes from your database; the callback's `Amount` is never used.
- [ ] Receipts (`RefNum`) are stored under a unique constraint; a repeat is a replay.
- [ ] Verification also runs from a background job for payments whose callback never arrived
      (look up pending orders by `res_num` and ask the customer/Saman's report panel if needed).
- [ ] The callback endpoint is reachable by the customer's browser, accepts both `POST` and
      (if you use `GET`) `GET`, is exempt from CSRF protection, and answers quickly.
- [ ] The redirect page is served from your domain without `Referrer-Policy: no-referrer`.
- [ ] A real payment of a small amount worked end to end, including a cancelled one.
- [ ] Logs contain no tokens, receipts or card data.

---

## Framework examples

Runnable-in-spirit, complete examples live in [`examples/`](examples):

- [`offline_demo.py`](examples/offline_demo.py) — the whole flow with the fake gateway (runs as is).
- [`fastapi_app.py`](examples/fastapi_app.py) — async, with `lifespan`.
- [`flask_app.py`](examples/flask_app.py) — synchronous.
- [`django_views.py`](examples/django_views.py) — with a unique receipt column.

## API reference

**Clients** — `SepClient`, `AsyncSepClient`

| Method | Returns | Purpose |
|---|---|---|
| `create_token(request)` | `Token` | Start a payment. |
| `verify_transaction(ref_num, *, session_key=None)` | `TransactionResult` | Confirm a receipt. |
| `reverse_transaction(ref_num, *, session_key=None)` | `TransactionResult` | Refund. |
| `verify_callback(callback, *, expected_amount, session_key=None, reverse_on_mismatch=False)` | `TransactionResult` | The safe, complete check. |
| `render_redirect_form(token, *, language, nonce)` | `str` | HTML hand-off page. |
| `close()` / `aclose()` | – | Release connections. |

**Functions** — `parse_callback`, `render_redirect_form`, `redirect_form_fields`,
`build_send_token_url`, `hash_card_number`, `generate_session_key`, `derive_session_key`,
`iban_checksum_ok`.

**Data** — `TokenRequest`, `SettlementItem`, `Token`, `CallbackData`, `TransactionResult`,
`TransactionDetail`, `Endpoints`, `RetryPolicy`.

**Enums** — `TransactionState`, `TransactionStatus`, `ResultCode`.

**Testing** — `sep_sdk.testing.FakeSepGateway`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `SepTokenError` with `code=8`, or callback `MerchantIpAddressIsInvalid` | Your server's IP is not registered with Saman. |
| `IPNotAllowedError` (`-106`) on verify | Same, for the verify service. |
| The bank page refuses to open | No `Referer`: serve the form from your own site (see section 3). |
| `TransactionNotFoundError` right after a real payment | Wrong `session_key`, or the receipt is not the one Saman issued. |
| `VerifyWindowExpiredError` | More than 30 minutes passed; Saman has reversed the payment. |
| `SepHTTPError` with status 404 | Endpoint path changed. Override `Endpoints`. |
| `AmountMismatchError` | The bank took another sum. Never deliver; refund (`reverse_on_mismatch=True`). |

## Typing

The package ships `py.typed` and is checked with `mypy --strict`. Models are frozen,
slotted dataclasses; state and codes are enums; unions are explicit (`ResultCode | int`
where the gateway may send a code this version does not know).

## Compatibility and versioning

Python 3.10 – 3.13. [Semantic Versioning](https://semver.org/). Built from Saman's integration
guide v3.6; a few details are not fully specified there (the exact `TxnRandomSessionKey`
semantics, the `…Transaction` vs `…Transcation` path spelling, `neo-pg` GET redirects) and are
handled defensively — please open an issue if your terminal behaves differently.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The suite runs offline with 100% line and branch
coverage; `ruff`, `mypy --strict` and `pytest` must pass.

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE).
