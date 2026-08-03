# Release process

## Version bump

1. Update `version` in `pyproject.toml`.
2. Update `__version__` in `src/systemsieve/__init__.py`.
3. Add an entry to `CHANGELOG.md` under a new version heading.

## Build and verify

```powershell
.\scripts\test.ps1
python -m build
```

This produces an sdist and wheel under `dist/`. Verify the wheel installs cleanly in a
fresh virtual environment:

```powershell
python -m venv verify_venv
verify_venv\Scripts\pip install dist\systemsieve-<version>-py3-none-any.whl
verify_venv\Scripts\systemsieve doctor
```

## Standalone Windows executable

```powershell
.\scripts\build_windows.ps1
```

Produces `dist\SystemSieve\SystemSieve.exe` (one-folder distribution). Before publishing:

- Test it inside a fresh virtual machine following [testing.md](testing.md).
- **Code-sign the executable.** This project does not include a code-signing certificate --
  do not ship an unsigned build as a "release" without clearly labelling it as such.
  Unsigned executables will trigger SmartScreen warnings, which is expected for
  unsigned/unrecognised publishers.
- Verify `SystemSieve.exe doctor`, `SystemSieve.exe apps list`, and `SystemSieve.exe gui`
  (double-click) all work from the built folder, not just from source.

## Publishing to PyPI

```powershell
python -m twine upload dist/*
```

Requires PyPI credentials configured separately; not automated in this repository's CI by
default (see `.github/workflows/release.yml`, which is a template you should adapt with
your own trusted-publishing or token configuration before enabling it).

## GitHub release

1. Tag the release: `git tag vX.Y.Z && git push origin vX.Y.Z`.
2. Create a GitHub release from the tag, pasting the relevant `CHANGELOG.md` section.
3. Attach the standalone Windows build (zipped) if you have verified and signed it.
