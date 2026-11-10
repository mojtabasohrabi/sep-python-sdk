import pytest

from sep_sdk import ResultCode, TransactionState, TransactionStatus


@pytest.mark.parametrize("state", list(TransactionState))
def test_every_state_has_both_messages(state: TransactionState) -> None:
    assert state.message("en")
    assert state.message("fa")


@pytest.mark.parametrize("code", list(ResultCode))
def test_every_result_code_has_both_messages(code: ResultCode) -> None:
    assert code.message("en")
    assert code.message("fa")


def test_state_parsing_is_exact() -> None:
    assert TransactionState.from_wire("OK") is TransactionState.OK
    assert TransactionState.from_wire("CanceledByUser") is TransactionState.CANCELED_BY_USER
    assert TransactionState.from_wire("ok") is TransactionState.UNKNOWN
    assert TransactionState.from_wire("Unknown") is TransactionState.UNKNOWN
    assert TransactionState.from_wire(None) is TransactionState.UNKNOWN
    assert TransactionState.OK.is_ok
    assert not TransactionState.FAILED.is_ok


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2", TransactionStatus.OK),
        (2, TransactionStatus.OK),
        (" 21 ", TransactionStatus.MULTISETTLE_POLICY_ERRORS),
        ("x", None),
        ("", None),
        (None, None),
        ("99", None),
    ],
)
def test_status_parsing(raw: object, expected: TransactionStatus | None) -> None:
    assert TransactionStatus.from_wire(raw) is expected


def test_result_code_parsing_keeps_unknown_numbers() -> None:
    assert ResultCode.from_wire(-2) is ResultCode.TRANSACTION_NOT_FOUND
    assert ResultCode.from_wire(777) == 777
