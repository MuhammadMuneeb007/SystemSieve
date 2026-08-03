# Contributing to SystemSieve

Thanks for your interest in contributing. SystemSieve performs destructive operations on
real systems, so we hold changes in the uninstall/deletion/elevation paths to a higher bar
than typical UI or read-only inventory changes.

## Getting started

See [docs/development.md](docs/development.md) for environment setup.

## Before you open a PR

- Run `.\scripts\test.ps1` (ruff check, ruff format --check, mypy, pytest) and fix anything
  it flags.
- If you touched anything in `package_management/`, `elevation/`, `storage/deletion.py`, or
  `storage/protected_paths.py`, re-read [docs/safety.md](docs/safety.md) and make sure your
  change doesn't weaken any of the guarantees listed there.
- If you touched the command validator or the uninstall/update planner, add or update the
  relevant test cases covering both accepted and rejected inputs.
- Test any GUI change manually -- automated GUI tests do not cover everything.
- Update `CHANGELOG.md` under an "Unreleased" heading.

## Pull request expectations

- Keep PRs focused; unrelated refactors make destructive-path changes harder to review.
- Describe *why* the change is needed, not just what changed.
- For anything touching safety-critical code paths, explain what you tested and how (ideally
  including a manual VM test per [docs/testing.md](docs/testing.md)).
- Use the PR template's checklist.

## Code style

- Python 3.11+, type hints throughout, `pathlib.Path` over string paths.
- Ruff for linting/formatting; mypy for type checking.
- No `shell=True`, ever. All process execution goes through
  `package_management/command_runner.py`.
- Keep GUI code free of business logic -- it should call into the core subsystems, not
  reimplement their logic.

## Reporting bugs vs. security issues

Regular bugs: open a GitHub issue using the bug report template.

Security or safety issues (anything that could cause an unintended uninstall, deletion, or
privilege escalation): see [SECURITY.md](SECURITY.md) -- do not open a public issue.

## Code of Conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before
participating.
