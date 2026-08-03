"""Developer helper for the manual virtual-machine test procedure (docs/testing.md).

Run this *inside a disposable VM snapshot*, after installing a few harmless
test applications (VLC, 7-Zip, Notepad++ are recommended). It does not
install or remove anything itself -- it only reports what SystemSieve can
currently see, so you can confirm inventory/update/scan behaviour before
attempting a real removal.
"""

from __future__ import annotations

import sys

RECOMMENDED_TEST_APPS = ["VLC", "7-Zip", "Notepad++"]


def main() -> int:
    if sys.platform != "win32":
        print("This helper only runs on Windows.")
        return 1

    from systemsieve.inventory.service import build_inventory

    print("Building inventory (read-only)...")
    result = build_inventory()

    print(
        f"\nFound {len(result.applications)} applications. WinGet available: {result.winget_available}"
    )
    if result.errors:
        print("Errors encountered:")
        for error in result.errors:
            print(f"  - {error}")

    print("\nChecking for recommended harmless test applications:")
    names = [a.display_name.lower() for a in result.applications]
    for candidate in RECOMMENDED_TEST_APPS:
        found = any(candidate.lower() in name for name in names)
        status = "FOUND" if found else "not installed"
        print(f"  - {candidate}: {status}")

    if not any(candidate.lower() in name for candidate in RECOMMENDED_TEST_APPS for name in names):
        print(
            "\nNone of the recommended test applications were found. Install at least one "
            "(e.g. 7-Zip) before proceeding with a real uninstall test."
        )

    print("\nNext steps: see docs/testing.md for the full manual test sequence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
