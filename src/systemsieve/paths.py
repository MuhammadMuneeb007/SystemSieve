"""Filesystem locations used by SystemSieve, resolved via platformdirs.

Centralising these avoids scattering raw path construction (and potential
inconsistencies) across the codebase.
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

from systemsieve.constants import APP_ID, APP_NAME, ORG_NAME

_dirs = PlatformDirs(appname=APP_NAME, appauthor=ORG_NAME, roaming=True)


def data_dir() -> Path:
    path = Path(_dirs.user_data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_dir() -> Path:
    path = Path(_dirs.user_config_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = Path(_dirs.user_cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_dir() -> Path:
    path = data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / f"{APP_ID}.sqlite3"


def config_file_path() -> Path:
    return config_dir() / "settings.json"


def elevation_result_dir() -> Path:
    """Directory for privileged-helper result files. Cleaned after each use."""
    path = data_dir() / "elevation"
    path.mkdir(parents=True, exist_ok=True)
    return path
