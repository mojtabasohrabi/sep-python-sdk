"""Protocol constants taken from the SEP online gateway guide (v3.6).

Nothing here is secret. Anything that may change on Saman's side (hosts, paths)
lives in :class:`sep_sdk.Endpoints`, so it can be overridden without patching.
"""

from __future__ import annotations

from typing import Final

TOKEN_URL: Final = "https://sep.shaparak.ir/onlinepg/onlinepg"
FORM_ACTION_URL: Final = "https://sep.shaparak.ir/OnlinePG/OnlinePG"
SEND_TOKEN_URL: Final = "https://sep.shaparak.ir/OnlinePG/SendToken"
VERIFY_URL: Final = "https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTransaction"
REVERSE_URL: Final = "https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/ReverseTransaction"
# Saman's own Postman collections spell these "Transcation". The PDF guide does not.
# The client tries the other spelling once if the first answers 404.
LEGACY_VERIFY_URL: Final = "https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTranscation"
LEGACY_REVERSE_URL: Final = (
    "https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/ReverseTranscation"
)

DEFAULT_TOKEN_EXPIRY_MINUTES: Final = 20
MIN_TOKEN_EXPIRY_MINUTES: Final = 20
MAX_TOKEN_EXPIRY_MINUTES: Final = 3600

#: A transaction must be verified within this many minutes, or Saman reverses it.
VERIFY_WINDOW_MINUTES: Final = 30
#: A verified transaction can be reversed up to this many minutes after it happened.
REVERSE_WINDOW_MINUTES: Final = 50

MAX_REDIRECT_URL_LENGTH: Final = 2083
MAX_REDIRECT_URL_LENGTH_GET: Final = 1538
MAX_EXTRA_DATA_ITEMS: Final = 4
MAX_EXTRA_DATA_LENGTH: Final = 50
MAX_ALLOWED_CARDS: Final = 10
MAX_SETTLEMENT_ITEMS: Final = 9
PURCHASE_ID_LENGTH: Final = 30
#: The purchase id of an ordinary (non-government) settlement line in a mixed request.
NO_PURCHASE_ID: Final = "0" * PURCHASE_ID_LENGTH

#: Header Saman sends back on token requests for terminals moved to ``neo-pg``.
IPG_URL_HEADER: Final = "X-IPG-Url"
