"""Allows `python -m systemsieve` to run the CLI.

With no arguments (e.g. when double-clicking a packaged executable), launches
the GUI directly rather than showing the CLI help text.
"""

import sys


def main() -> None:
    if len(sys.argv) == 1:
        from systemsieve.gui.app import run_gui

        sys.exit(run_gui())
    from systemsieve.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
