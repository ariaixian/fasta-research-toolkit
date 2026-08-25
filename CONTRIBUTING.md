# Contributing

Thank you for improving the toolkit. Keep contributions small, reproducible, and safe
for a public repository.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Before opening a pull request, run:

```bash
ruff check .
ruff format --check .
pytest
python scripts/audit_public_tree.py .
```

## Data policy

Use only clearly synthetic, minimal fixtures. Never contribute real or derived
research data, identifiers, metadata, screenshots, reports, notebooks with outputs,
or private directory paths. New fixture files must live under `tests/fixtures/` or
`examples/synthetic/` and explain how they were generated.

## Pull requests

- Explain the behavioral change and its privacy implications.
- Add tests for new behavior and failures.
- Preserve backward compatibility or document the migration.
- Keep dependencies minimal and pin development tooling to compatible ranges.
- Avoid logging record identifiers or sequence content.
