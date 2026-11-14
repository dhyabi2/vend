# Contributing to Vend

Vend is MIT licensed and takes contributions from anyone.

## Setup

```bash
git clone https://github.com/dhyabi2/vend.git && cd vend
uv sync
export NANO_AGENT_ACCOUNT="nano_..."   # any account you control; the server only receives
uv run pytest tests
```

## What a good change looks like

- One problem per pull request, with a test that fails before the change and passes after it.
- A new paid endpoint comes with: the handler, its price, its entry in the x402 manifest and OpenAPI
  (`tests/test_discovery_parity.py` checks that every door advertises the same list), and a test that an
  unpaid call answers 402 and a failed call does not keep the payment (`tests/test_delivery_proof.py`).
- Anything that touches `nano_verify.py` (what counts as a payment) needs a test for the refused case as
  well as the accepted one.
- Never commit a key, a seed, a token or an `.env` file. `.githooks/pre-commit` and `bin/secret-scan.py`
  refuse the common shapes; enable the hook with `git config core.hooksPath .githooks`.

## Reporting a problem

Open an issue with the request you sent, the response you got and what you expected. For a payment that
was taken without a result, include the block hash. For a vulnerability, see [SECURITY.md](SECURITY.md).

By contributing you agree that your contribution is licensed under the MIT license of this repository.
