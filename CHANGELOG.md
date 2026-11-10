# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.1] - 2026-11-10

### Fixed

- Serialize `TxnRandomSessionKey` as a positive signed 64-bit JSON integer for token,
  verify and reverse in both clients. Version 1.0.0 sent hexadecimal text, which the
  real verify service rejected with HTTP 400 after the customer had paid.
- Generate and derive decimal session keys; keep the helpers' string return type.
  Accept integer or decimal-text input and reject invalid keys before network I/O.
- Make the fake gateway reject the same invalid wire formats as SEP.
- Allow `derive_session_key(..., namespace=...)` to preserve an application's existing
  HMAC domain and already-issued numeric keys while adopting the SDK helper.

Existing hexadecimal keys cannot be sent unchanged. Reconcile their in-flight payments
before switching key generation; do not retry verification by automatically omitting a key.

## [1.0.0] - 2026-11-10

### Added

- `SepClient` and `AsyncSepClient`: token creation, verify, reverse and the one-call
  `verify_callback` (state check, receipt check, terminal check, amount check, optional
  automatic reversal on a mismatch).
- `TokenRequest` with every field of the v3.6 guide: wage, cell number, token expiry,
  allowed cards (MD5), four extra-data slots, `TxnRandomSessionKey`, multi-account
  settlement, government payments and `GET` callbacks.
- `parse_callback`, `render_redirect_form`, `build_send_token_url` and support for terminals
  on `neo-pg` (`X-IPG-Url`).
- Typed exceptions for every documented result code, `RetryPolicy` with safe-by-default
  retries, and a one-time fallback between the `…Transaction` / `…Transcation` spellings.
- `sep_sdk.testing.FakeSepGateway`: an in-memory gateway for offline tests.
- Persian and English documentation.
