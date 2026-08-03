# PyInstaller spec for SystemSieve.
#
# Produces a one-folder distribution (dist/SystemSieve/) rather than a single
# .exe: PySide6 apps generally start faster and are easier to troubleshoot
# as a folder build than as a one-file bundle. Build with:
#   pyinstaller packaging/systemsieve.spec
#
# This does not sign the resulting executable. Public releases should be
# code-signed separately -- see docs/release.md.

# ruff: noqa
import sys
from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).parent
src_root = project_root / "src"
icon_path = src_root / "systemsieve" / "resources" / "icons" / "systemsieve.ico"

a = Analysis(
    [str(src_root / "systemsieve" / "__main__.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=[
        (str(src_root / "systemsieve" / "resources"), "systemsieve/resources"),
    ],
    hiddenimports=[
        "systemsieve.cli",
        "systemsieve.gui.app",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SystemSieve",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # console=True so `SystemSieve.exe apps list` etc. work from a terminal.
    # `SystemSieve.exe gui` (or no arguments) still opens the normal window;
    # a console window will briefly flash when launched by double-click.
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SystemSieve",
)
