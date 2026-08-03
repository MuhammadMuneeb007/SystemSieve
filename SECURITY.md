# Security Policy

SystemSieve performs privileged, potentially destructive operations on Windows systems
(uninstalling software, deleting files, escalating to administrator). Security issues here
can have real consequences for users, so we take reports seriously.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security or safety vulnerabilities.**

Instead, report privately using one of:

- GitHub's [private vulnerability reporting](https://github.com/systemsieve/systemsieve/security/advisories/new)
  feature for this repository, if enabled.
- Email the maintainers (see the repository's GitHub profile for current contact details).

Please include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, including any relevant registry entries, commands, or file paths
  (redact anything sensitive).
- The SystemSieve version and Windows version you tested on.

## What counts as a security/safety issue here

- Anything that lets a command execute that was not validated through
  `package_management/command_validator.py`.
- Anything that bypasses or weakens the dry-run default, the confirmation dialogs, or the
  protected-path/protected-application checks.
- Anything that escalates privileges beyond the single operation that needs it, or that
  could be used to run arbitrary code elevated.
- Anything that deletes or uninstalls something the user did not select, or without the
  confirmations described in [docs/safety.md](docs/safety.md).
- Anything that exposes sensitive data (see [docs/privacy.md](docs/privacy.md) for what
  SystemSieve is and isn't supposed to store).

## Response

We aim to acknowledge reports within 5 business days and to provide a plan for remediation
or a rationale for why something is not considered a vulnerability. Please give us
reasonable time to investigate and release a fix before any public disclosure.

## Supported versions

Only the latest released version of SystemSieve receives security fixes.
