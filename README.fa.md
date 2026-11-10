<div dir="rtl">

# sep-python-sdk

[English](README.md) · **فارسی**

[![CI](https://github.com/mojtabasohrabi/sep-python-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/mojtabasohrabi/sep-python-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/sep-python-sdk.svg)](https://pypi.org/project/sep-python-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/sep-python-sdk.svg)](https://pypi.org/project/sep-python-sdk/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

یک SDK تایپ‌شده و تست‌شده برای **درگاه پرداخت اینترنتی پرداخت الکترونیک سامان (SEP)**
(`sep.shaparak.ir`): دریافت توکن، هدایت مشتری به بانک، خواندن نتیجهٔ بازگشت، تأیید پول
(verify) و در صورت لزوم برگشت تراکنش (reverse). کلاینت همگام (sync) و ناهمگام (`asyncio`)،
بدون وابستگی به هیچ فریم‌ورکی.

> **غیررسمی.** این پروژه وابسته به شرکت پرداخت الکترونیک سامان نیست و از طرف آن تأیید یا
> پشتیبانی نمی‌شود. بر پایهٔ مستند فنی عمومی «راهنمای استفاده از درگاه پرداخت اینترنتی،
> نگارش ۳٫۶» نوشته شده است. «SEP» و «سامان» متعلق به صاحبان خود هستند.

## فهرست

- [امکانات](#امکانات)
- [نصب](#نصب)
- [پرداخت چگونه کار می‌کند](#پرداخت-چگونه-کار-میکند)
- [شروع سریع](#شروع-سریع)
- [راهنمای کامل](#راهنمای-کامل)
  - [۱. کلاینت](#۱-کلاینت)
  - [۲. ساخت توکن](#۲-ساخت-توکن)
  - [۳. هدایت مشتری به بانک](#۳-هدایت-مشتری-به-بانک)
  - [۴. خواندن نتیجهٔ بازگشت (callback)](#۴-خواندن-نتیجهٔ-بازگشت-callback)
  - [۵. تأیید پرداخت (verify)](#۵-تأیید-پرداخت-verify)
  - [۶. برگشت تراکنش (reverse)](#۶-برگشت-تراکنش-reverse)
  - [۷. بستن رسید به سفارش (session key)](#۷-بستن-رسید-به-سفارش-session-key)
  - [۸. پرداخت چندحسابی و دولتی](#۸-پرداخت-چندحسابی-و-دولتی)
  - [۹. حالت Async](#۹-حالت-async)
  - [۱۰. خطاها](#۱۰-خطاها)
  - [۱۱. تایم‌اوت و تلاش مجدد](#۱۱-تایماوت-و-تلاش-مجدد)
  - [۱۲. لاگ](#۱۲-لاگ)
  - [۱۳. تست آفلاین یکپارچه‌سازی](#۱۳-تست-آفلاین-یکپارچهسازی)
  - [۱۴. چک‌لیست قبل از انتشار](#۱۴-چکلیست-قبل-از-انتشار)
- [نمونه با فریم‌ورک‌ها](#نمونه-با-فریمورکها)
- [مرجع API](#مرجع-api)
- [عیب‌یابی](#عیبیابی)
- [تایپ‌ها](#تایپها)
- [سازگاری و نسخه‌گذاری](#سازگاری-و-نسخهگذاری)
- [مشارکت](#مشارکت) · [امنیت](#امنیت) · [مجوز](#مجوز)

## امکانات

- **پوشش کامل پروتکل** — توکن، هدایت (فرم POST و لینک GET)، callback، `VerifyTransaction`،
  `ReverseTransaction`، تراکنش چندحسابی (`MultiSettle`) و دولتی (`Government`)، فهرست کارت‌های
  مجاز، کارمزد (`Wage`)، داده‌های اضافه، زمان انقضای توکن، `GetMethod`،
  `TxnRandomSessionKey` و ترمینال‌های `neo-pg` (هدر `X-IPG-Url`).
- **ایمن از پایه** — `verify_callback()` callbackهای ناموفق را رد می‌کند، رسید و ترمینال
  **و مبلغ** را بررسی می‌کند و در صورت مغایرت می‌تواند خودش تراکنش را برگشت بزند.
- **Sync و Async** — `SepClient` و `AsyncSepClient` همهٔ قواعد را از یک پیاده‌سازی مشترک می‌گیرند.
- **تایپ سخت‌گیرانه** — `py.typed`، dataclassهای ثابت (frozen)، enum، و `mypy --strict` بدون خطا.
- **خطاهای دقیق** — یک سلسله‌مراتب استثنا؛ برای هر `ResultCode` مستند یک کلاس جدا.
- **مقاوم** — تلاش مجددِ نمایی که هرگز تماسی را که می‌تواند دو بار پول بگیرد تکرار نمی‌کند، و
  جایگزینی یک‌باره بین دو املای مسیر که سامان در عمل استفاده کرده است.
- **تست آفلاین همراه پکیج** — `FakeSepGateway` بانک را شبیه‌سازی می‌کند؛ تست‌های شما به
  ترمینال، IP مجاز یا اینترنت نیاز ندارند.
- **سبک** — فقط یک وابستگی زمان اجرا: [`httpx`](https://www.python-httpx.org/). پایتون ۳٫۱۰ به بالا.
- **دوزبانه** — پیام‌های خطا و وضعیت به فارسی و انگلیسی؛ مستندات به هر دو زبان.

## نصب

```bash
pip install sep-python-sdk
```

به **شمارهٔ ترمینال** از سامان نیاز دارید و باید **IP عمومی سرور** شما نزد سامان ثبت شده
باشد (در غیر این صورت درخواست‌های توکن و verify رد می‌شوند).

## پرداخت چگونه کار می‌کند

```
 سرور شما                              مرورگر مشتری                         سامان (SEP)
     │ ۱. create_token(مبلغ، شمارهٔ سفارش، آدرس بازگشت) ──────────────────────►│
     │◄──────────────────────────────────────────── توکن ──────────────────────│
     │ ۲. صفحه‌ای با فرم POST (render_redirect_form) ─►│                        │
     │                                                │ ۳. ارسال فرم ─────────►│  مشتری پرداخت می‌کند
     │                                                │◄── ۴. بازگشت ──────────│
     │◄─ ۵. POST/GET به آدرس بازگشت شما: State, RefNum, ResNum, … ──────────────│
     │ ۶. verify_transaction(RefNum) ───────────────────────────────────────────►│
     │◄────────────────────── مبلغ واقعاً کسرشده ───────────────────────────────│
     │ ۷. مقایسه با مبلغ سفارش «شما» ← تحویل کالا/خدمت                           │
```

دو قاعده که کل SDK روی آن‌ها بنا شده:

1. **callback مدرک پرداخت نیست.** هر کسی می‌تواند به آدرس بازگشت شما هر پارامتری بفرستد.
   فقط تماس سرور به سرور verify ثابت می‌کند پول واقعاً رسیده است.
2. **ظرف ۳۰ دقیقه verify کنید**، وگرنه سامان خودش تراکنش را برگشت می‌زند.

## شروع سریع

```python
from sep_sdk import SepClient, TokenRequest, parse_callback, render_redirect_form

sep = SepClient(terminal_id="12345678")

# ۱. شروع: برای هر تلاش پرداخت یک توکن. مبلغ‌ها به «ریال» هستند.
token = sep.create_token(
    TokenRequest(
        amount=150_000,
        res_num="order-1001",  # شناسهٔ یکتای سفارش/تلاش شما
        redirect_url="https://shop.example/payments/callback",
    )
)

# ۲. هدایت مشتری به بانک: این HTML را از یک صفحهٔ روی سایت خودتان برگردانید.
html = render_redirect_form(token, language="fa")

# ۳. در ویوی callback بانک نتیجه را می‌فرستد. پارس کنید، سپس «تأیید» کنید.
callback = parse_callback(request_form_or_query)                  # هر شیء dict‌مانند
result = sep.verify_callback(callback, expected_amount=150_000)   # فقط اگر واقعاً پرداخت شده باشد برمی‌گردد

# ۴. حالا سفارش را پرداخت‌شده کنید و result.ref_num را ذخیره کنید (باید یکتا باشد).
print(result.ref_num, result.amount)
```

کل جریان را بدون ترمینال و آفلاین اجرا کنید: `python examples/offline_demo.py`.

---

## راهنمای کامل

### ۱. کلاینت

```python
from sep_sdk import SepClient

with SepClient(terminal_id="12345678") as sep:   # با خروج، اتصال‌ها بسته می‌شوند
    ...
```

| آرگومان | پیش‌فرض | معنی |
|---|---|---|
| `terminal_id` | – | شمارهٔ عددی ترمینال (`str` یا `int`). |
| `endpoints` | production | شیء [`Endpoints`](#endpoints) برای تغییر یا جعل هر آدرس. |
| `timeout` | ۲۰ ثانیه (اتصال ۵ ثانیه) | `float` یا `httpx.Timeout`. |
| `retry` | ۳ تلاش | یک [`RetryPolicy`](#۱۱-تایماوت-و-تلاش-مجدد). |
| `endpoint_fallback` | `True` | با خطای HTTP 404 یک بار املای جایگزین مسیر را امتحان کن. |
| `transport` | – | ترنسپورت `httpx` (تست، پروکسی). |
| `http_client` | – | `httpx.Client` خودتان؛ بستنش با شماست. |

در هر پروسه **یک کلاینت** بسازید و دوباره استفاده کنید؛ اتصال‌ها را زنده نگه می‌دارد.

#### Endpoints

```python
from sep_sdk import Endpoints, SepClient

SepClient("12345678", endpoints=Endpoints.production())     # پیش‌فرض
SepClient("12345678", endpoints=Endpoints.legacy())         # ابتدا املای «…Transcation»
SepClient("12345678", endpoints=Endpoints.without_fallback())
```

### ۲. ساخت توکن

```python
from sep_sdk import TokenRequest

token = sep.create_token(
    TokenRequest(
        amount=150_000,                      # ریال، عدد صحیح، بزرگ‌تر از صفر
        res_num="order-1001",                # یکتا برای هر تلاش
        redirect_url="https://shop.example/payments/callback",
    )
)
token.token               # توکن پرداخت (در repr() پنهان است)
token.expires_in_minutes  # ۲۰، مگر اینکه تغییر داده باشید
```

همهٔ فیلدهای `TokenRequest` (به‌جز سه فیلد اول، بقیه اختیاری‌اند). مقدار نامعتبر **قبل از
ارسال هر چیزی** با `SepValidationError` رد می‌شود.

| فیلد | نام در مستند | توضیح |
|---|---|---|
| `amount` | `Amount` | ریال، عدد صحیح. |
| `res_num` | `ResNum` | شناسهٔ سفارش/تلاش شما. یکتا باشد: اگر مشتری پرداخت کرد اما سرور شما خبردار نشد، تنها دستگیرهٔ شماست. |
| `redirect_url` | `RedirectUrl` | آدرس بازگشت شما. `http(s)`، حداکثر ۲۰۸۳ نویسه (با `callback_method="GET"` حداکثر ۱۵۳۸). |
| `wage` | `Wage` | کارمزد، برای پذیرندگانی که تسهیم می‌کنند. |
| `cell_number` | `CellNumber` | موبایل مشتری تا سامان کارت‌های ذخیره‌شده را پیشنهاد دهد. `0912…`، `+98912…`، `912…` و ارقام فارسی پذیرفته می‌شود. |
| `token_expiry_minutes` | `TokenExpiryInMin` | ۲۰ تا ۳۶۰۰. |
| `allowed_cards` | `HashedCardNumber` | حداکثر ۱۰ هش MD5؛ فقط همین کارت‌ها می‌توانند پرداخت کنند. از `hash_card_number()` استفاده کنید. |
| `extra_data` | `ResNum1…4` | حداکثر ۴ رشتهٔ ≤ ۵۰ نویسه که فقط در گزارش‌های سامان دیده می‌شود. |
| `session_key` | `TxnRandomSessionKey` | [بخش ۷](#۷-بستن-رسید-به-سفارش-session-key). |
| `settlement` | `SettlementIbanInfo` | [بخش ۸](#۸-پرداخت-چندحسابی-و-دولتی). |
| `government` | `TranType=Government` | بخش ۸. |
| `callback_method` | `GetMethod` | `"POST"` (پیش‌فرض) یا `"GET"`. |

```python
from sep_sdk import hash_card_number

TokenRequest(
    amount=150_000, res_num="order-1002", redirect_url="https://shop.example/cb",
    cell_number="09123456789",
    token_expiry_minutes=60,
    allowed_cards=[hash_card_number("6037 9912 3456 7890")],  # فقط همین کارت
    extra_data=["فاکتور ۱۷", "کمپین بهار"],
)
```

> `hash_card_number` شمارهٔ کارت را ذخیره یا لاگ نمی‌کند. مستند سامان ذخیرهٔ شمارهٔ کارت را
> ممنوع کرده است: فقط هش را نگه دارید.

### ۳. هدایت مشتری به بانک

**مرورگر** مشتری باید به سامان برود. از فرم استفاده کنید که برای همهٔ ترمینال‌ها کار می‌کند:

```python
from sep_sdk import render_redirect_form

html = render_redirect_form(token, language="fa", nonce=csp_nonce_or_None)
# آن را به‌عنوان پاسخ HTML از یک صفحهٔ روی سایت «خودتان» برگردانید
```

صفحه‌ای می‌سازد که بلافاصله `Token` را به بانک POST می‌کند (و اگر جاوااسکریپت خاموش باشد
دکمه نشان می‌دهد). همهٔ مقدارها HTML-escape می‌شوند؛ اگر Content-Security-Policy شما nonce
می‌خواهد `nonce=` بدهید.

**مهم:** سامان بازدیدکننده‌ای را که بدون `Referer` از سایت شما آمده باشد نمی‌پذیرد. فرم را
از دامنهٔ خودتان سرو کنید، روی آن صفحه `Referrer-Policy: no-referrer` نگذارید (خود فرم
`<meta name="referrer" content="origin">` دارد) و آدرس بانک را مستقیم از داخل اپ موبایل باز
نکنید: صفحهٔ خودتان را در مرورگر باز کنید.

می‌خواهید خودتان قالب بسازید؟

```python
from sep_sdk import redirect_form_fields

redirect_form_fields(token)   # {"Token": "…"} (و برای callback از نوع GET: "GetMethod": "true")
token.form_action             # آدرسی که باید به آن POST شود
```

برای ترمینال‌های کلاسیک لینک ساده هم هست: `token.get_url`
(`https://sep.shaparak.ir/OnlinePG/SendToken?token=…`). ترمینال‌هایی که به **neo-pg** رفته‌اند
هدر `X-IPG-Url` برمی‌گردانند؛ آنگاه `token.ipg_url` مقدار دارد، `token.get_url` برابر `None`
است و `action` فرم از قبل به آدرس جدید اشاره می‌کند.

### ۴. خواندن نتیجهٔ بازگشت (callback)

پس از پرداخت، سامان مشتری را با نتیجه به `redirect_url` شما برمی‌گرداند (فیلدهای فرم `POST`،
یا query string با `callback_method="GET"`).

```python
from sep_sdk import parse_callback

callback = parse_callback(request.POST)        # QueryDict جنگو، request.values در Flask،
                                               # dict ساده، خروجی parse_qs(...) …
callback.res_num      # شمارهٔ سفارش شما (ResNum)
callback.ref_num      # رسید بانک (RefNum)
callback.state        # TransactionState.OK, CANCELED_BY_USER, FAILED, …
callback.is_ok        # State برابر OK، رسید موجود، و Status (در صورت ارسال) هم‌خوان
callback.amount       # آنچه بانک «ادعا» می‌کند: قابل اعتماد نیست
callback.state.message("fa")   # توضیح قابل‌نمایش به مشتری (و "en")
```

`parse_callback` **هیچ تماس شبکه‌ای نمی‌زند** و به هیچ چیز اعتماد نمی‌کند. نام پارامترها
بدون حساسیت به بزرگی/کوچکی حروف تطبیق داده می‌شوند، مقدارهای لیستی به اولین عضو تبدیل
می‌شوند و فیلدهای مربوط به کارت از `repr` پنهان‌اند.

| `TransactionState` | معنی |
|---|---|
| `OK` | بانک پرداخت را موفق گزارش می‌کند (باز هم: verify کنید!). |
| `CANCELED_BY_USER` | مشتری انصراف داد. |
| `FAILED` | پرداخت انجام نشد. |
| `SESSION_IS_NULL` | مشتری در مهلت مقرر پاسخی نداد. |
| `INVALID_PARAMETERS` | پارامترهای ارسالی به بانک نامعتبر بود. |
| `MERCHANT_IP_ADDRESS_IS_INVALID` | IP سرور شما نزد سامان ثبت نشده است. |
| `TOKEN_NOT_FOUND` / `TOKEN_REQUIRED` | توکن پیدا نشد / ترمینال فقط پرداخت توکنی می‌پذیرد. |
| `TERMINAL_NOT_FOUND` | شمارهٔ ترمینال ناشناخته. |
| `MULTISETTLE_POLICY_ERRORS` | قواعد چندحسابی رعایت نشده است. |
| `UNKNOWN` | مقداری که این نسخهٔ SDK نمی‌شناسد — «پرداخت‌نشده» حساب می‌شود. |

### ۵. تأیید پرداخت (verify)

تنها تماسی که باید استفاده کنید:

```python
from sep_sdk import AmountMismatchError, PaymentNotCompletedError, SepError

order = orders.get(callback.res_num)           # رکورد «شما»، با شمارهٔ سفارش خودتان
try:
    result = sep.verify_callback(
        callback,
        expected_amount=order.total_rials,     # از پایگاه‌دادهٔ شما، هرگز از درخواست
        session_key=order.session_key,         # اگر استفاده کرده‌اید
        reverse_on_mismatch=True,              # اگر مبلغ فرق داشت خودکار برگشت بزن
    )
except PaymentNotCompletedError as error:      # لغو/ناموفق: چیزی برای تأیید نیست
    show(error.state.message("fa"))
except AmountMismatchError as error:           # بانک مبلغ دیگری برداشته
    log.error("پرداخت دستکاری‌شده: %s در برابر %s، برگشت‌خورده=%s", error.expected, error.actual, error.reversed)
except SepError:                               # شبکه، رد شدن از سمت درگاه، پاسخ نامعتبر…
    schedule_retry_within_30_minutes(callback.ref_num)
else:
    # هر رسید فقط «یک بار» قابل استفاده است. ref_num را در ستون یکتا ذخیره کنید؛ تکراری = replay.
    order.mark_paid(receipt=result.ref_num)
```

`verify_callback` به ترتیب این کارها را می‌کند:

1. callbackی را که `State` آن یک `OK` تمیز نیست رد می‌کند (`PaymentNotCompletedError`، بدون شبکه)؛
2. callback مربوط به ترمینال دیگر را رد می‌کند؛
3. `VerifyTransaction` را صدا می‌زند؛
4. بررسی می‌کند پاسخ برای **همان رسید و همان ترمینال** است؛
5. بررسی می‌کند بانک دقیقاً `expected_amount` ریال برداشته (`AmountMismatchError`؛ با
   `reverse_on_mismatch=True` برگشت هم می‌زند و `error.reversed` نتیجه را نشان می‌دهد).

کنترل دقیق‌تر می‌خواهید؟ تماس پایه را مستقیم بزنید:

```python
result = sep.verify_transaction(callback.ref_num, session_key=order.session_key)
result.amount             # OrginalAmount: با مبلغ «خودتان» مقایسه کنید
result.detail.affective_amount   # آنچه از کارت کم شده (در ترمینال تخفیفی فرق می‌کند)
result.detail.trace_no, result.detail.rrn, result.detail.trace_date
result.is_duplicate       # True یعنی سامان گفت «این درخواست قبلاً انجام شده»
```

اگر تماس verify به‌خاطر شبکه خطا داد، **دوباره تلاش کنید**: سامان رسید را معتبر نگه می‌دارد و
تکرار را با «درخواست تکراری» جواب می‌دهد. SDK خودش تلاش مجدد می‌کند (بخش ۱۱)؛ اگر باز هم
نشد، در همان بازهٔ ۳۰ دقیقه دوباره امتحان کنید — یک job پس‌زمینه برای verify دوبارهٔ پرداخت‌های
ناتمام ایدهٔ خوبی است.

### ۶. برگشت تراکنش (reverse)

```python
reversal = sep.reverse_transaction(ref_num)   # تا ۵۰ دقیقه پس از پرداخت
reversal.is_duplicate                         # True یعنی قبلاً برگشت خورده
```

### ۷. بستن رسید به سفارش (session key)

`TxnRandomSessionKey` تماس verify بعدی را به همان پرداخت گره می‌زند تا رسید یک سفارش (ارزان)
روی سفارش دیگری تکرار نشود. دو راه برای داشتن کلید:

```python
from sep_sdk import derive_session_key, generate_session_key

key = generate_session_key()                       # تصادفی؛ همراه سفارش ذخیره کنید
key = derive_session_key(SERVER_SECRET, order_id)  # یا بعداً دوباره محاسبه کنید، چیزی برای ذخیره نیست
```

خروجی helperها رشتهٔ ده‌دهی است و ورودی عدد صحیح هم پذیرفته می‌شود. SDK بازهٔ
`1..2**63-1` را کنترل می‌کند و در توکن، تأیید و برگشت یک JSON number می‌فرستد.
کلید هگز، بولین، اعشاری و خارج از بازه پیش از تماس با بانک رد می‌شود.

برای انتقال کلید عددی HMAC فعلی برنامه به helper، `namespace` یکسان بدهید تا مقدار
کلید پرداخت‌های در جریان تغییر نکند. پرداخت‌های با کلید هگز نسخهٔ ۱٫۰٫۰ باید پیش از
ارتقا تطبیق داده شوند؛ کلید را خودکار از درخواست تأیید حذف نکنید.

آن را در `TokenRequest(session_key=key)` و دوباره در `verify_callback(..., session_key=key)`
بدهید. اگر سامان برای ترمینال شما این فیلد اضافه را نپذیرفت، ارسالش نکنید. (شبیه‌ساز داخلی
کلید نبودن/اشتباه را «تراکنش پیدا نشد» می‌گیرد؛ عبارت دقیق درگاه واقعی در مستند نیست.)

### ۸. پرداخت چندحسابی و دولتی

به ترمینالی نیاز دارد که سامان این قابلیت را برایش فعال کرده باشد.

```python
from sep_sdk import SettlementItem, TokenRequest

# تسهیم یک پرداخت بین چند شبا (حداکثر ۹ ردیف).
TokenRequest(
    amount=12_000, res_num="order-7", redirect_url="https://shop.example/cb",
    settlement=[
        SettlementItem(iban="IR062960000000100324200001", amount=7_000),
        SettlementItem(iban="IR000000000000000000000001", amount=5_000),
    ],
)

# پرداخت دولتی: ردیف «اول» شبای دولتی و شناسهٔ ۳۰ رقمی را دارد.
TokenRequest(
    amount=12_000, res_num="order-8", redirect_url="https://shop.example/cb",
    government=True,
    settlement=[
        SettlementItem(iban="IR062960000000100324200001", amount=7_000, purchase_id="1" * 30),
        SettlementItem(iban="IR000000000000000000000001", amount=5_000),  # با ۳۰ صفر پر می‌شود
    ],
)
```

شبا از نظر قالب (`IR` + ۲۴ رقم) بررسی می‌شود؛ اگر کنترل mod-97 هم می‌خواهید
`iban_checksum_ok(iban)` در دسترس است.

### ۹. حالت Async

`AsyncSepClient` همان متدها را دارد، با `await`:

```python
from sep_sdk import AsyncSepClient

async with AsyncSepClient(terminal_id="12345678") as sep:
    token = await sep.create_token(request)
    result = await sep.verify_callback(callback, expected_amount=150_000)
```

### ۱۰. خطاها

همه از `SepError` ارث می‌برند.

```
SepError
├── SepConfigurationError      شمارهٔ ترمینال/آدرس‌ها/سیاست تلاش مجدد نامعتبر   (و ValueError)
├── SepValidationError         درخواست محلی رد شد، چیزی ارسال نشد             (و ValueError)
├── SepTransportError          نتیجه نامعلوم است
│   ├── SepConnectionError
│   └── SepTimeoutError
├── SepHTTPError               وضعیت HTTP غیرمنتظره (.status_code)
├── SepResponseError           پاسخ ۲xx ولی مطابق مستند نیست
├── SepAPIError                درگاه درخواست را رد کرد (.code, .description, .operation)
│   ├── SepTokenError          رد شدن درخواست توکن (status = -1)
│   └── SepTransactionError    رد شدن verify/reverse (.result_code)
│       ├── TransactionNotFoundError   -2
│       ├── VerifyWindowExpiredError   -6   (بیش از ۳۰ دقیقه)
│       ├── TransactionReversedError    5
│       ├── TerminalError            -104 / -105
│       └── IPNotAllowedError        -106
├── PaymentNotCompletedError   callback می‌گوید مشتری پرداخت نکرده (.state)
└── AmountMismatchError        بانک مبلغ دیگری برداشته (.expected, .actual, .reversed)
```

`description` متنی است که خود درگاه نوشته: لاگش کنید ولی عیناً به مشتری نشان ندهید. برای متن
مناسب مشتری از `state.message("fa" | "en")` و `ResultCode.message(...)` استفاده کنید.

### ۱۱. تایم‌اوت و تلاش مجدد

```python
import httpx
from sep_sdk import RetryPolicy, SepClient

SepClient(
    "12345678",
    timeout=httpx.Timeout(15.0, connect=3.0),
    retry=RetryPolicy(max_attempts=4, backoff_factor=0.5, max_backoff=8.0),
)
SepClient("12345678", retry=RetryPolicy.none())   # دقیقاً یک تلاش
```

| عملیات | اتصال باز نشد | تایم‌اوت / قطع اتصال / 5xx / 429 |
|---|---|---|
| `verify`، `reverse` | تکرار می‌شود | تکرار می‌شود (سامان تکرار را «درخواست تکراری» جواب می‌دهد) |
| `create_token` | تکرار می‌شود | **تکرار نمی‌شود** — ممکن است بانک همان‌موقع نشست ساخته باشد |

خطای HTTP 404 روی verify/reverse یک‌بار املای جایگزین مسیر را امتحان می‌کند
(`VerifyTransaction` ↔ `VerifyTranscation`) و تا پایان عمر کلاینت یادش می‌ماند.

### ۱۲. لاگ

SDK با لاگر `sep_sdk` لاگ می‌کند (تا خودتان تنظیم نکنید ساکت است): سطح debug برای تلاش‌ها،
warning برای تلاش مجدد و جایگزینی مسیر، و error اگر برگشت خودکار شکست بخورد. توکن، رسید،
اطلاعات کارت و بدنهٔ درخواست‌ها **هرگز** لاگ نمی‌شوند.

```python
import logging
logging.getLogger("sep_sdk").setLevel(logging.INFO)
```

### ۱۳. تست آفلاین یکپارچه‌سازی

`FakeSepGateway` یک بانک درون‌حافظه‌ای است:

```python
from sep_sdk import SepClient, TokenRequest, parse_callback
from sep_sdk.testing import FakeSepGateway

fake = FakeSepGateway(terminal_id="12345678")
sep = SepClient("12345678", endpoints=fake.endpoints, transport=fake.transport)

token = sep.create_token(TokenRequest(amount=100_000, res_num="o-1", redirect_url="https://x.test/cb"))

fields = fake.complete_payment(token.token)            # آنچه بانک به شما POST می‌کند
fields = fake.complete_payment(token.token, paid_amount=1_000)  # پرداخت دستکاری‌شده
fields = fake.end_payment(token.token)                 # مشتری انصراف داد
fake.expire(ref_num)                                   # ۳۰ دقیقه گذشت: verify ← -6
fake.fail_next(status_code=503, operation="verify")    # خطای HTTP در verify بعدی
fake.drop_next()                                       # تماس بعدی گم شود (خطای اتصال)
FakeSepGateway(reject_ip=True)                         # IP سرور ثبت نشده
FakeSepGateway(neo_pg_url="https://neo-pg.sep.test/transaction/init")
FakeSepGateway(spelling="transcation")                 # آزمودن جایگزینی مسیر
fake.calls                                             # همهٔ درخواست‌ها، برای assert
```

شبیه‌ساز از **مستند** پیروی می‌کند نه رفتار خصوصی سامان. از آن برای آزمودن مسیرهای کد خودتان
استفاده کنید و پیش از انتشار یک پرداخت واقعی کوچک هم انجام دهید. `AsyncSepClient` هم
`transport=fake.transport` را می‌پذیرد.

### ۱۴. چک‌لیست قبل از انتشار

- [ ] IP عمومی سرور شما نزد سامان ثبت شده است.
- [ ] `expected_amount` از پایگاه‌دادهٔ شما می‌آید؛ `Amount` داخل callback هرگز استفاده نمی‌شود.
- [ ] رسیدها (`RefNum`) در ستون یکتا ذخیره می‌شوند؛ تکرار یعنی replay.
- [ ] verify برای پرداخت‌هایی که callbackشان نرسید هم از یک job پس‌زمینه انجام می‌شود.
- [ ] آدرس callback از مرورگر مشتری در دسترس است، `POST` (و در صورت استفاده `GET`) را
      می‌پذیرد، از CSRF معاف است و سریع جواب می‌دهد.
- [ ] صفحهٔ هدایت از دامنهٔ شما و بدون `Referrer-Policy: no-referrer` سرو می‌شود.
- [ ] یک پرداخت واقعی با مبلغ کم، از ابتدا تا انتها، موفق بوده — و یک پرداخت لغوشده هم.
- [ ] لاگ‌ها شامل توکن، رسید یا اطلاعات کارت نیستند.

---

## نمونه با فریم‌ورک‌ها

نمونه‌های کامل در پوشهٔ [`examples/`](examples) هستند:

- [`offline_demo.py`](examples/offline_demo.py) — کل جریان با شبیه‌ساز (همان‌طور که هست اجرا می‌شود).
- [`fastapi_app.py`](examples/fastapi_app.py) — async، با `lifespan`.
- [`flask_app.py`](examples/flask_app.py) — همگام.
- [`django_views.py`](examples/django_views.py) — با ستون یکتای رسید.

## مرجع API

**کلاینت‌ها** — `SepClient`، `AsyncSepClient`

| متد | خروجی | کاربرد |
|---|---|---|
| `create_token(request)` | `Token` | شروع پرداخت. |
| `verify_transaction(ref_num, *, session_key=None)` | `TransactionResult` | تأیید رسید. |
| `reverse_transaction(ref_num, *, session_key=None)` | `TransactionResult` | برگشت وجه. |
| `verify_callback(callback, *, expected_amount, session_key=None, reverse_on_mismatch=False)` | `TransactionResult` | بررسی کامل و ایمن. |
| `render_redirect_form(token, *, language, nonce)` | `str` | صفحهٔ HTML هدایت. |
| `close()` / `aclose()` | – | آزاد کردن اتصال‌ها. |

**توابع** — `parse_callback`، `render_redirect_form`، `redirect_form_fields`،
`build_send_token_url`، `hash_card_number`، `generate_session_key`، `derive_session_key`،
`iban_checksum_ok`.

**داده‌ها** — `TokenRequest`، `SettlementItem`، `Token`، `CallbackData`، `TransactionResult`،
`TransactionDetail`، `Endpoints`، `RetryPolicy`.

**Enumها** — `TransactionState`، `TransactionStatus`، `ResultCode`.

**تست** — `sep_sdk.testing.FakeSepGateway`.

## عیب‌یابی

| نشانه | علت محتمل |
|---|---|
| `SepTokenError` با `code=8`، یا وضعیت `MerchantIpAddressIsInvalid` در callback | IP سرور شما نزد سامان ثبت نشده است. |
| `IPNotAllowedError` (‏`-106`) در verify | همان مشکل، برای سرویس verify. |
| صفحهٔ بانک باز نمی‌شود | `Referer` ارسال نشده: فرم را از سایت خودتان سرو کنید (بخش ۳). |
| `TransactionNotFoundError` بلافاصله پس از پرداخت واقعی | `session_key` اشتباه است یا رسید همان نیست که سامان صادر کرده. |
| `VerifyWindowExpiredError` | بیش از ۳۰ دقیقه گذشته؛ سامان پرداخت را برگشت زده است. |
| `SepHTTPError` با وضعیت 404 | مسیر تغییر کرده است. `Endpoints` را بازنویسی کنید. |
| `AmountMismatchError` | بانک مبلغ دیگری برداشته. هرگز تحویل ندهید؛ برگشت بزنید (`reverse_on_mismatch=True`). |

## تایپ‌ها

پکیج `py.typed` دارد و با `mypy --strict` بررسی می‌شود. مدل‌ها dataclassهای ثابت و slotted
هستند؛ وضعیت‌ها و کدها enum‌اند؛ اتحادها صریح‌اند (`ResultCode | int` جایی که درگاه ممکن است
کدی بفرستد که این نسخه نمی‌شناسد).

## سازگاری و نسخه‌گذاری

پایتون ۳٫۱۰ تا ۳٫۱۳. [نسخه‌گذاری معنایی](https://semver.org/lang/fa/). بر اساس مستند سامان
نگارش ۳٫۶ نوشته شده؛ چند جزئیات در آن مستند کاملاً مشخص نیست (معنای دقیق
`TxnRandomSessionKey`، املای مسیر `…Transaction` یا `…Transcation`، و هدایت GET در `neo-pg`)
و محتاطانه پوشش داده شده‌اند — اگر ترمینال شما رفتار دیگری دارد لطفاً issue باز کنید.

## مشارکت

[CONTRIBUTING.md](CONTRIBUTING.md) را ببینید. مجموعه‌تست آفلاین است و پوشش خط و شاخه ۱۰۰٪
دارد؛ `ruff`، `mypy --strict` و `pytest` باید موفق باشند.

## امنیت

آسیب‌پذیری‌ها را خصوصی گزارش کنید — [SECURITY.md](SECURITY.md).

## مجوز

[MIT](LICENSE).

</div>
