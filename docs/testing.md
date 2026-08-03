# Manual testing strategy

```
Do not use the first development build to remove important software from your primary computer.
```

SystemSieve's automated test suite never uninstalls real software or deletes real files (see
"Automated tests" below). Before you rely on a build for anything real, verify it manually
inside a disposable environment using the procedure below.

## Recommended procedure

1. Use Windows Sandbox, Hyper-V, VMware, or VirtualBox -- anything you can snapshot and
   discard.
2. Take a virtual-machine snapshot before installing anything.
3. Install a few harmless, easily-reinstallable test applications, e.g.:
   - VLC
   - 7-Zip
   - Notepad++
4. Run SystemSieve in dry-run mode (the default) and use
   `python scripts\create_test_vm_data.py` to confirm SystemSieve can see the test apps.
5. Verify inventory accuracy: names, versions, publishers, and sizes match what's actually
   installed.
6. Verify update detection against `winget upgrade`, if any test app has an update.
7. Preview an uninstall of one test application (dry run) and read the plan carefully.
8. Confirm the exact command shown matches what you'd expect (WinGet, MSI, or a quiet
   uninstall command -- never a raw, unvalidated string).
9. Create a restore point if System Protection is available in the VM, and confirm
   SystemSieve reports success or failure honestly.
10. Disable dry-run and execute removal of **only one** harmless test application.
11. Confirm the application disappears from SystemSieve's inventory after a refresh, and
    separately confirm via Windows "Installed apps" that it is actually gone.
12. Restore the VM snapshot after destructive testing, so the VM is clean for next time.

## Automated tests

This first release ships without a bundled automated test suite (by project decision for
this build). If you add one, follow this project's established safety conventions:

- Never uninstall real software or delete real files in the default test run.
- Use fake registry records and fake WinGet output rather than the real system.
- Use a `FakeCommandRunner` that records planned commands instead of executing them, for
  anything exercising `package_management/`.
- Mark any test that must touch a real, disposable VM with `@pytest.mark.manual`,
  `@pytest.mark.destructive`, and/or `@pytest.mark.windows_only`, and require
  `SYSTEMSIEVE_ALLOW_DESTRUCTIVE_TESTS=YES_I_AM_USING_A_VM` to be set before a destructive
  test is allowed to run at all. Even then, destructive tests should target only a
  deliberately installed, harmless test application -- never anything else.

## Reporting issues found during manual testing

If you find a correctness bug, open a GitHub issue. If you find a safety issue (something
that could uninstall/delete more than intended, bypass a confirmation, or misrepresent what
an operation will do), report it privately first -- see [SECURITY.md](../SECURITY.md).
