"""Django: two views. Persist orders and receipts with your own models.

A ``Payment`` model should store the order id, the amount in rials and a ``ref_num``
column with a UNIQUE constraint, so a receipt can never be used twice.
"""

from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from sep_sdk import (
    SepClient,
    SepError,
    TokenRequest,
    derive_session_key,
    parse_callback,
    render_redirect_form,
)

from .models import Payment  # your model: order_id, amount_irr, ref_num (unique, blank), status

sep = SepClient("12345678")
SECRET = "load-me-from-django-settings"


def pay(request: HttpRequest, order_id: str) -> HttpResponse:
    payment = get_object_or_404(Payment, order_id=order_id, status="pending")
    token = sep.create_token(
        TokenRequest(
            amount=payment.amount_irr,
            res_num=order_id,
            redirect_url=request.build_absolute_uri("/payments/callback/"),
            session_key=derive_session_key(SECRET, order_id),
        )
    )
    return HttpResponse(render_redirect_form(token, language="fa"))


@csrf_exempt  # the bank cannot send your CSRF token; the verify call is the protection
def callback(request: HttpRequest) -> HttpResponse:
    data = parse_callback(request.POST or request.GET)
    payment = get_object_or_404(Payment, order_id=data.res_num, status="pending")
    try:
        result = sep.verify_callback(
            data,
            expected_amount=payment.amount_irr,
            session_key=derive_session_key(SECRET, payment.order_id),
            reverse_on_mismatch=True,
        )
        with transaction.atomic():
            payment.ref_num = result.ref_num  # UNIQUE: a replayed receipt fails here
            payment.status = "paid"
            payment.save(update_fields=["ref_num", "status"])
    except (SepError, IntegrityError):
        return HttpResponseRedirect("/failed")
    return HttpResponseRedirect("/thanks")
