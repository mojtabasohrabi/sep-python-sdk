from urllib.parse import parse_qs, urlsplit

import pytest

from sep_sdk import (
    TransactionState,
    TransactionStatus,
    build_send_token_url,
    parse_callback,
    redirect_form_fields,
    render_redirect_form,
)
from sep_sdk.responses import Token

FIELDS = {
    "MID": "1234",
    "State": "OK",
    "Status": "2",
    "RRN": "14226761817",
    "RefNum": "ref-1",
    "ResNum": "order-1",
    "TerminalId": "1234",
    "TraceNo": "100428",
    "Amount": "12,000",
    "Wage": "0",
    "AffectiveAmount": "12000",
    "SecurePan": "621986****8080",
    "HashedCardNumber": "abc",
    "Token": "tok",
}


def token(**overrides: object) -> Token:
    fields: dict[str, object] = {
        "token": "tok123456",
        "res_num": "order-1",
        "form_action": "https://bank.test/pay",
        "get_url": "https://bank.test/send?token=tok123456",
        "ipg_url": None,
        "get_method": False,
        "expires_in_minutes": 20,
    }
    fields.update(overrides)
    return Token(**fields)  # type: ignore[arg-type]


class TestParseCallback:
    def test_a_completed_payment(self) -> None:
        data = parse_callback(FIELDS)
        assert data.is_ok
        assert data.state is TransactionState.OK
        assert data.status is TransactionStatus.OK
        assert (data.ref_num, data.res_num, data.terminal_id, data.token) == (
            "ref-1",
            "order-1",
            "1234",
            "tok",
        )
        assert (data.amount, data.wage, data.affective_amount) == (12_000, 0, 12_000)
        assert data.secure_pan == "621986****8080"
        assert data.raw["RefNum"] == "ref-1"

    def test_the_repr_hides_card_data(self) -> None:
        shown = repr(parse_callback(FIELDS))
        assert "621986" not in shown
        assert "abc" not in shown

    def test_names_are_case_insensitive_and_lists_are_flattened(self) -> None:
        data = parse_callback({"state": ["OK"], "REFNUM": ("ref-2",), "mid": "9", "Status": []})
        assert data.state is TransactionState.OK
        assert data.ref_num == "ref-2"
        assert data.terminal_id == "9"
        assert data.status is None

    @pytest.mark.parametrize(
        "fields",
        [
            {"State": "CanceledByUser", "Status": "1"},
            {"State": "OK", "RefNum": ""},
            {"State": "OK", "RefNum": "r", "Status": "3"},
            {"State": "Something", "RefNum": "r"},
            {},
        ],
    )
    def test_anything_but_a_clean_ok_is_not_ok(self, fields: dict[str, str]) -> None:
        assert not parse_callback(fields).is_ok

    def test_ok_without_a_status_is_still_ok(self) -> None:
        assert parse_callback({"State": "OK", "RefNum": "r"}).is_ok

    def test_odd_numbers_become_none(self) -> None:
        data = parse_callback({"Amount": "12.5", "Wage": "x", "AffectiveAmount": None})
        assert (data.amount, data.wage, data.affective_amount) == (None, None, None)

    def test_unknown_state_is_kept_verbatim(self) -> None:
        data = parse_callback({"State": "Mystery"})
        assert data.state is TransactionState.UNKNOWN
        assert data.state_raw == "Mystery"


class TestRedirect:
    def test_the_get_link(self) -> None:
        url = build_send_token_url("a b&c")
        assert urlsplit(url).path == "/OnlinePG/SendToken"
        assert parse_qs(urlsplit(url).query) == {"token": ["a b&c"]}

    def test_fields(self) -> None:
        assert redirect_form_fields(token()) == {"Token": "tok123456"}
        assert redirect_form_fields(token(get_method=True)) == {
            "Token": "tok123456",
            "GetMethod": "true",
        }

    def test_the_form_posts_to_the_bank_and_asks_for_a_referrer(self) -> None:
        page = render_redirect_form(token())
        assert 'method="post" action="https://bank.test/pay"' in page
        assert '<input type="hidden" name="Token" value="tok123456">' in page
        assert '<meta name="referrer" content="origin">' in page
        assert 'document.getElementById("sep-redirect").submit();' in page
        assert 'lang="en" dir="ltr"' in page

    def test_persian_page_is_rtl(self) -> None:
        page = render_redirect_form(token(), language="fa")
        assert 'lang="fa" dir="rtl"' in page
        assert "درگاه" in page

    def test_nonce_and_manual_mode(self) -> None:
        assert '<script nonce="n-1">' in render_redirect_form(token(), nonce="n-1")
        assert "<script" not in render_redirect_form(token(), auto_submit=False)

    def test_everything_is_escaped(self) -> None:
        page = render_redirect_form(
            token(token='"><script>x</script>', form_action='https://x.test/"><b>'),
            nonce='"><i>',
        )
        assert "<script>x</script>" not in page
        assert "<b>" not in page
        assert "<i>" not in page

    def test_get_method_is_forwarded_to_the_form(self) -> None:
        assert 'name="GetMethod" value="true"' in render_redirect_form(token(get_method=True))
