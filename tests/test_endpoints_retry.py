import pytest

from sep_sdk import Endpoints, RetryPolicy, SepConfigurationError


def test_defaults_follow_the_guide() -> None:
    endpoints = Endpoints.production()
    assert endpoints.verify_url.endswith("/ipg/VerifyTransaction")
    assert endpoints.verify_fallback_url is not None
    assert endpoints.verify_fallback_url.endswith("/ipg/VerifyTranscation")


def test_legacy_swaps_the_spellings() -> None:
    endpoints = Endpoints.legacy()
    assert endpoints.verify_url.endswith("VerifyTranscation")
    assert endpoints.reverse_url.endswith("ReverseTranscation")
    assert endpoints.verify_fallback_url is not None
    assert endpoints.verify_fallback_url.endswith("VerifyTransaction")


def test_without_fallback() -> None:
    endpoints = Endpoints.without_fallback()
    assert endpoints.verify_fallback_url is None
    assert endpoints.reverse_fallback_url is None


@pytest.mark.parametrize("field", ["token_url", "verify_url", "verify_fallback_url"])
def test_bad_urls_are_refused(field: str) -> None:
    with pytest.raises(SepConfigurationError):
        Endpoints(**{field: "ftp://nope"})


def test_retry_delays_double_and_cap() -> None:
    policy = RetryPolicy(backoff_factor=0.5, max_backoff=3.0)
    assert [policy.delay(n) for n in (1, 2, 3, 4)] == [0.5, 1.0, 2.0, 3.0]


def test_no_retry() -> None:
    assert RetryPolicy.none().max_attempts == 1


@pytest.mark.parametrize(
    "fields", [{"max_attempts": 0}, {"backoff_factor": -1}, {"max_backoff": -1}]
)
def test_bad_retry_policies(fields: dict[str, float]) -> None:
    with pytest.raises(SepConfigurationError):
        RetryPolicy(**fields)  # type: ignore[arg-type]
