"""User preferences, persisted as JSON.

Safety-relevant defaults (dry_run, recycle_bin_default) are intentionally
conservative and require explicit user action to relax.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field

from systemsieve.paths import config_file_path, database_path, export_dir

logger = logging.getLogger("systemsieve.config")


@dataclass
class AppConfig:
    dry_run_default: bool = True
    """Global default for whether destructive operations preview-only. Always True
    on first launch; users must explicitly disable it in Settings."""

    create_restore_point_default: bool = True
    recycle_bin_default: bool = True
    show_system_components: bool = False
    include_hidden_files_in_scans: bool = False
    follow_reparse_points: bool = False
    continue_bulk_on_failure: bool = False
    logging_level: str = "INFO"
    theme: str = "system"
    database_path: str = field(default_factory=lambda: str(database_path()))
    export_location: str = field(default_factory=lambda: str(export_dir()))
    developer_mode: bool = False
    window_geometry: str | None = None
    window_state: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        known = set(cls.__dataclass_fields__)
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


def load_config() -> AppConfig:
    path = config_file_path()
    if not path.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppConfig.from_dict(data)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load config from %s: %s. Using defaults.", path, exc)
        return AppConfig()


def save_config(cfg: AppConfig) -> None:
    path = config_file_path()
    try:
        path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to save config to %s: %s", path, exc)
