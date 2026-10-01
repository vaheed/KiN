# Contributing to KIN

KIN favors small, explicit changes over infrastructure or abstraction growth.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r core/requirements.txt
make test
make validate
```

## Principles

- KIN is the executive layer; do not reimplement TrueForge/Bifrost functionality.
- Prefer a single Compose stack until a real scaling constraint requires otherwise.
- Keep model/provider code behind Bifrost.
- Treat model output as data that must be validated and policy-checked.
- Add an audit event for externally meaningful state changes.
- Keep integrations explicit and documented in `docs/UPSTREAM.md`.
- Tests must not silently claim an external dependency worked. Integration tests skip unless their service dependencies are explicitly enabled.

## Pull requests

Include the behavior change, tests, operational implications, and any upstream interface/version assumptions. Update `CHANGELOG.md` for user-visible changes.
