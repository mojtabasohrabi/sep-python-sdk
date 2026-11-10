"""The vocabulary of the gateway: transaction states, status codes and result codes."""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Literal

Language = Literal["en", "fa"]


class TransactionState(str, Enum):
    """The ``State`` field Saman posts back to your ``RedirectUrl`` (guide, table 1).

    Only :attr:`OK` means the bank reports a completed payment, and even that is
    a *claim made by the user's browser*: always confirm with
    :meth:`SepClient.verify_transaction`.
    """

    OK = "OK"
    CANCELED_BY_USER = "CanceledByUser"
    FAILED = "Failed"
    SESSION_IS_NULL = "SessionIsNull"
    INVALID_PARAMETERS = "InvalidParameters"
    MERCHANT_IP_ADDRESS_IS_INVALID = "MerchantIpAddressIsInvalid"
    TOKEN_NOT_FOUND = "TokenNotFound"
    TOKEN_REQUIRED = "TokenRequired"
    TERMINAL_NOT_FOUND = "TerminalNotFound"
    MULTISETTLE_POLICY_ERRORS = "MultisettlePolicyErrors"
    #: A value this version of the SDK does not know. Treated as "not paid".
    UNKNOWN = "Unknown"

    @classmethod
    def from_wire(cls, value: str | None) -> TransactionState:
        """Parse the wire value exactly; anything unrecognised becomes :attr:`UNKNOWN`."""
        for member in cls:
            if member is not cls.UNKNOWN and member.value == value:
                return member
        return cls.UNKNOWN

    @property
    def is_ok(self) -> bool:
        return self is TransactionState.OK

    def message(self, language: Language = "en") -> str:
        """A short, user-presentable explanation in English or Persian."""
        return _STATE_MESSAGES[self][language]


class TransactionStatus(IntEnum):
    """The numeric ``Status`` field that accompanies :class:`TransactionState`."""

    CANCELED_BY_USER = 1
    OK = 2
    FAILED = 3
    SESSION_IS_NULL = 4
    INVALID_PARAMETERS = 5
    MERCHANT_IP_ADDRESS_IS_INVALID = 8
    TOKEN_NOT_FOUND = 10
    TOKEN_REQUIRED = 11
    TERMINAL_NOT_FOUND = 12
    MULTISETTLE_POLICY_ERRORS = 21

    @classmethod
    def from_wire(cls, value: object) -> TransactionStatus | None:
        """Parse an int or numeric string; ``None`` if absent or unrecognised."""
        try:
            return cls(int(str(value).strip()))
        except ValueError:
            return None


class ResultCode(IntEnum):
    """``ResultCode`` of the verify and reverse services (guide, error table)."""

    SUCCESS = 0
    DUPLICATE_REQUEST = 2
    TRANSACTION_REVERSED = 5
    TRANSACTION_NOT_FOUND = -2
    VERIFY_WINDOW_EXPIRED = -6
    TERMINAL_INACTIVE = -104
    TERMINAL_NOT_FOUND = -105
    IP_NOT_ALLOWED = -106

    @classmethod
    def from_wire(cls, value: int) -> ResultCode | int:
        """The enum member when known, otherwise the raw integer."""
        try:
            return cls(value)
        except ValueError:
            return value

    def message(self, language: Language = "en") -> str:
        return _RESULT_MESSAGES[self][language]


_STATE_MESSAGES: dict[TransactionState, dict[Language, str]] = {
    TransactionState.OK: {
        "en": "The payment was completed.",
        "fa": "پرداخت با موفقیت انجام شد.",
    },
    TransactionState.CANCELED_BY_USER: {
        "en": "The customer cancelled the payment.",
        "fa": "کاربر از پرداخت انصراف داد.",
    },
    TransactionState.FAILED: {
        "en": "The payment was not completed.",
        "fa": "پرداخت انجام نشد.",
    },
    TransactionState.SESSION_IS_NULL: {
        "en": "The customer did not respond within the allowed time.",
        "fa": "کاربر در بازهٔ زمانی تعیین‌شده پاسخی ارسال نکرد.",
    },
    TransactionState.INVALID_PARAMETERS: {
        "en": "The parameters sent to the gateway are invalid.",
        "fa": "پارامترهای ارسالی نامعتبر است.",
    },
    TransactionState.MERCHANT_IP_ADDRESS_IS_INVALID: {
        "en": "The merchant server address is not registered with the gateway.",
        "fa": "آدرس سرور پذیرنده نزد درگاه ثبت نشده است.",
    },
    TransactionState.TOKEN_NOT_FOUND: {
        "en": "The token was not found.",
        "fa": "توکن ارسال‌شده پیدا نشد.",
    },
    TransactionState.TOKEN_REQUIRED: {
        "en": "This terminal accepts token-based payments only.",
        "fa": "با این ترمینال فقط تراکنش‌های توکنی قابل پرداخت هستند.",
    },
    TransactionState.TERMINAL_NOT_FOUND: {
        "en": "The terminal number was not found.",
        "fa": "شمارهٔ ترمینال ارسال‌شده پیدا نشد.",
    },
    TransactionState.MULTISETTLE_POLICY_ERRORS: {
        "en": "The multi-account settlement rules were not respected.",
        "fa": "محدودیت‌های مدل چندحسابی رعایت نشده است.",
    },
    TransactionState.UNKNOWN: {
        "en": "The gateway reported a state this SDK does not recognise.",
        "fa": "درگاه وضعیتی گزارش کرد که این SDK نمی‌شناسد.",
    },
}

_RESULT_MESSAGES: dict[ResultCode, dict[Language, str]] = {
    ResultCode.SUCCESS: {"en": "The operation succeeded.", "fa": "عملیات با موفقیت انجام شد."},
    ResultCode.DUPLICATE_REQUEST: {
        "en": "This request was already processed.",
        "fa": "این درخواست قبلاً انجام شده است.",
    },
    ResultCode.TRANSACTION_REVERSED: {
        "en": "The transaction has been reversed.",
        "fa": "تراکنش برگشت خورده است.",
    },
    ResultCode.TRANSACTION_NOT_FOUND: {
        "en": "The transaction was not found.",
        "fa": "تراکنش پیدا نشد.",
    },
    ResultCode.VERIFY_WINDOW_EXPIRED: {
        "en": "More than 30 minutes have passed since the transaction.",
        "fa": "بیش از نیم ساعت از زمان تراکنش گذشته است.",
    },
    ResultCode.TERMINAL_INACTIVE: {
        "en": "The terminal is inactive.",
        "fa": "ترمینال غیرفعال است.",
    },
    ResultCode.TERMINAL_NOT_FOUND: {
        "en": "The terminal does not exist.",
        "fa": "ترمینال در سیستم موجود نیست.",
    },
    ResultCode.IP_NOT_ALLOWED: {
        "en": "The server address is not allowed to call this service.",
        "fa": "آدرس IP درخواست‌دهنده مجاز نیست.",
    },
}
