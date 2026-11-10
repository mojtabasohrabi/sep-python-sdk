# Contributing

Thanks for helping! This project is small on purpose: every change needs a test, and the
suite must stay at 100% line and branch coverage.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

ruff format . && ruff check .      # style
mypy                               # strict typing
pytest                             # tests + coverage gate (100%)
```

Guidelines:

- No network in tests. Use `sep_sdk.testing.FakeSepGateway` or `httpx.MockTransport`.
- Public behaviour changes go in `CHANGELOG.md` under *Unreleased*.
- Never paste real terminal numbers, tokens, receipts or card data into issues or tests.
- Match the wording of the vendor's guide for field names; document any guess as a guess.
- Keep the English and Persian READMEs in sync.
