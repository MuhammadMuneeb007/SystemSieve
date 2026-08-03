## Summary

<!-- What does this PR change, and why? -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / code quality
- [ ] CI / build / packaging

## Safety checklist (required if this touches uninstall, deletion, or elevation code)

- [ ] This change does not weaken the dry-run default.
- [ ] This change does not bypass or reduce confirmation dialogs/prompts.
- [ ] This change does not add a new code path that builds/executes shell strings
      (`shell=True` or manual string concatenation into a command).
- [ ] This change does not weaken protected-application or protected-path checks.
- [ ] I re-read [docs/safety.md](../docs/safety.md) and this change is consistent with it.
- [ ] N/A -- this PR does not touch safety-critical code paths.

## Testing

<!-- How did you verify this change? Include manual VM test notes if applicable
     (see docs/testing.md), and/or new/updated automated tests. -->

- [ ] `.\scripts\test.ps1` passes locally.
- [ ] Tested manually in a virtual machine (required for uninstall/deletion/elevation changes).

## Checklist

- [ ] I updated `CHANGELOG.md` under "Unreleased".
- [ ] I updated relevant documentation (`docs/`, `README.md`).
- [ ] My changes generate no new ruff/mypy warnings.
