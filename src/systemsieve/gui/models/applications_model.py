"""Qt table model backing the Applications page.

Selection state (checkbox column) is tracked here so the page can query it
without walking widget state. Filtering/search is applied via
ApplicationsFilterProxyModel below.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QBrush, QColor, QFont

from systemsieve.constants import SAFETY_PROTECTED
from systemsieve.inventory.size_parser import format_bytes
from systemsieve.models.application import InstalledApplication

COLUMNS = [
    "Select",
    "Application",
    "Version",
    "Publisher",
    "Size",
    "Installed",
    "Last Activity",
    "Activity Confidence",
    "Update",
    "Source",
    "Safety",
    "Status",
]

COL_CHECK = 0
COL_NAME = 1
COL_VERSION = 2
COL_PUBLISHER = 3
COL_SIZE = 4
COL_INSTALLED = 5
COL_ACTIVITY = 6
COL_ACTIVITY_CONFIDENCE = 7
COL_UPDATE = 8
COL_SOURCE = 9
COL_SAFETY = 10
COL_STATUS = 11


class ApplicationsTableModel(QAbstractTableModel):
    def __init__(self, applications: list[InstalledApplication] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._applications: list[InstalledApplication] = applications or []
        self._checked: set[str] = set()

    def set_applications(self, applications: list[InstalledApplication]) -> None:
        self.beginResetModel()
        self._applications = applications
        self._checked &= {a.id for a in applications}
        self.endResetModel()

    def application_at(self, row: int) -> InstalledApplication:
        return self._applications[row]

    def checked_applications(self) -> list[InstalledApplication]:
        return [a for a in self._applications if a.id in self._checked]

    def clear_selection(self) -> None:
        self.beginResetModel()
        self._checked.clear()
        self.endResetModel()

    def select_all(self, ids: list[str] | None = None) -> None:
        self.beginResetModel()
        if ids is None:
            self._checked = {a.id for a in self._applications}
        else:
            self._checked |= set(ids)
        self.endResetModel()

    def invert_selection(self) -> None:
        self.beginResetModel()
        all_ids = {a.id for a in self._applications}
        self._checked = all_ids - self._checked
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N803, B008
        return 0 if parent.isValid() else len(self._applications)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N803, B008
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def flags(self, index: QModelIndex):  # noqa: N802
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == COL_CHECK:
            return base | Qt.ItemIsUserCheckable
        return base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        app_record = self._applications[index.row()]
        col = index.column()

        if role == Qt.CheckStateRole and col == COL_CHECK:
            return Qt.Checked if app_record.id in self._checked else Qt.Unchecked

        if role == Qt.ToolTipRole:
            reasons = "\n".join(app_record.safety_reasons) or "No safety warnings."
            return f"{app_record.display_name}\nSafety: {app_record.safety_level}\n{reasons}"

        if role == Qt.ForegroundRole:
            colors = {
                "protected": "#dc2626",
                "review": "#d97706",
                "normal": "#059669",
                "unknown": "#64748b",
            }
            if col in (COL_NAME, COL_SAFETY, COL_STATUS):
                return QBrush(QColor(colors.get(app_record.safety_level, "#64748b")))

        if role == Qt.FontRole and col == COL_NAME:
            font = QFont()
            font.setBold(True)
            return font

        if role == Qt.UserRole:
            if col == COL_SIZE:
                return (
                    app_record.estimated_size_bytes
                    if app_record.estimated_size_bytes is not None
                    else -1
                )
            if col == COL_INSTALLED:
                return app_record.install_date.timestamp() if app_record.install_date else 0
            if col == COL_ACTIVITY:
                return app_record.activity_date.timestamp() if app_record.activity_date else 0
            if col == COL_UPDATE:
                return 1 if app_record.update_available else 0

        if role != Qt.DisplayRole:
            return None

        if col == COL_NAME:
            return app_record.display_name
        if col == COL_VERSION:
            return app_record.display_version or "-"
        if col == COL_PUBLISHER:
            return app_record.publisher or "-"
        if col == COL_SIZE:
            return app_record.estimated_size_display
        if col == COL_INSTALLED:
            return app_record.install_date.strftime("%Y-%m-%d") if app_record.install_date else "-"
        if col == COL_ACTIVITY:
            return (
                app_record.activity_date.strftime("%Y-%m-%d") if app_record.activity_date else "-"
            )
        if col == COL_ACTIVITY_CONFIDENCE:
            return app_record.activity_confidence.value
        if col == COL_UPDATE:
            return app_record.available_version if app_record.update_available else "-"
        if col == COL_SOURCE:
            return app_record.source
        if col == COL_SAFETY:
            return app_record.safety_level
        if col == COL_STATUS:
            return "Protected" if app_record.safety_level == SAFETY_PROTECTED else "Available"
        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):  # noqa: N802
        if role == Qt.CheckStateRole and index.column() == COL_CHECK:
            app_id = self._applications[index.row()].id
            if value == Qt.Checked:
                self._checked.add(app_id)
            else:
                self._checked.discard(app_id)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False

    def selected_total_size(self) -> int:
        return sum(a.estimated_size_bytes or 0 for a in self.checked_applications())


class ApplicationsFilterProxyModel(QSortFilterProxyModel):
    """Supports free-text search plus a named category filter."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._search_text = ""
        self._category = "all"
        self.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.setSortRole(Qt.UserRole)

    def set_search_text(self, text: str) -> None:
        self._search_text = text.lower()
        self.invalidateFilter()

    def set_category(self, category: str) -> None:
        self._category = category
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        model: ApplicationsTableModel = self.sourceModel()  # type: ignore[assignment]
        app_record = model.application_at(source_row)

        if self._search_text:
            haystack = f"{app_record.display_name} {app_record.publisher or ''}".lower()
            if self._search_text not in haystack:
                return False

        return _matches_category(app_record, self._category)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        left_value = left.data(Qt.UserRole)
        right_value = right.data(Qt.UserRole)
        if left_value is not None and right_value is not None:
            return left_value < right_value
        return (
            str(left.data(Qt.DisplayRole) or "").casefold()
            < str(right.data(Qt.DisplayRole) or "").casefold()
        )


def _matches_category(app_record: InstalledApplication, category: str) -> bool:
    if category == "all":
        return True
    if category == "updates_available":
        return app_record.update_available
    if category == "large":
        return (app_record.estimated_size_bytes or 0) >= 500 * 1024 * 1024
    if category == "recently_installed":
        from datetime import datetime, timedelta

        return bool(
            app_record.install_date
            and app_record.install_date >= datetime.now() - timedelta(days=30)
        )
    if category == "possibly_unused":
        return app_record.activity_confidence.value in ("low", "unavailable")
    if category == "winget_managed":
        return "winget" in app_record.source
    if category == "registry_only":
        return app_record.source == "registry"
    if category == "user_applications":
        return not app_record.system_component
    if category == "system_components":
        return app_record.system_component
    if category == "safe_to_review":
        return app_record.safety_level in ("normal", "review")
    if category == "protected":
        return app_record.safety_level == SAFETY_PROTECTED
    if category == "unknown_size":
        return app_record.estimated_size_bytes is None
    return True


def format_size_bytes(num_bytes: int) -> str:
    return format_bytes(num_bytes)
