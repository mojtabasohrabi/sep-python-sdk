"""Sending the customer to the bank.

Saman refuses a visitor whose browser does not send a ``Referer`` from the
merchant's own site. The form below is meant to be *served by your site*. Do not
send ``Referrer-Policy: no-referrer`` on that page; the form sets
``<meta name="referrer" content="origin">`` itself so that ``origin`` is used.
"""

from __future__ import annotations

from html import escape
from urllib.parse import urlencode

from sep_sdk.constants import SEND_TOKEN_URL
from sep_sdk.enums import Language
from sep_sdk.responses import Token

_TEXT: dict[Language, dict[str, str]] = {
    "en": {
        "title": "Redirecting to the payment gateway",
        "message": "Please wait while we take you to the bank…",
        "button": "Continue to the bank",
        "dir": "ltr",
    },
    "fa": {
        "title": "انتقال به درگاه پرداخت",
        "message": "لطفاً چند لحظه صبر کنید؛ در حال انتقال به درگاه بانک هستیم…",
        "button": "ادامه به درگاه بانک",
        "dir": "rtl",
    },
}


def build_send_token_url(token: str, *, base_url: str = SEND_TOKEN_URL) -> str:
    """The classic ``GET`` redirect link. Not available on ``neo-pg`` terminals."""
    return f"{base_url}?{urlencode({'token': token})}"


def redirect_form_fields(token: Token) -> dict[str, str]:
    """The hidden inputs of the hand-off form, for use in your own template."""
    fields = {"Token": token.token}
    if token.get_method:
        fields["GetMethod"] = "true"
    return fields


def render_redirect_form(
    token: Token,
    *,
    language: Language = "en",
    nonce: str | None = None,
    auto_submit: bool = True,
) -> str:
    """A complete HTML page that POSTs the customer to the bank.

    ``nonce`` is added to the inline script when your Content-Security-Policy uses
    one. With ``auto_submit=False`` (or JavaScript disabled) the customer gets a
    button instead. Every value is HTML-escaped.
    """
    text = _TEXT[language]
    inputs = "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in redirect_form_fields(token).items()
    )
    script = ""
    if auto_submit:
        nonce_attribute = f' nonce="{escape(nonce, quote=True)}"' if nonce else ""
        script = (
            f'<script{nonce_attribute}>document.getElementById("sep-redirect").submit();</script>'
        )
    return (
        f'<!doctype html><html lang="{language}" dir="{text["dir"]}"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="referrer" content="origin">'
        '<meta name="robots" content="noindex, nofollow">'
        f"<title>{escape(text['title'])}</title></head><body>"
        f"<p>{escape(text['message'])}</p>"
        f'<form id="sep-redirect" method="post" action="{escape(token.form_action, quote=True)}">'
        f'{inputs}<noscript><button type="submit">{escape(text["button"])}</button></noscript>'
        f"</form>{script}</body></html>"
    )
