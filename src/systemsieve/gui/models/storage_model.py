"""Qt table models backing the Storage page."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from systemsieve.inventory.size_parser import format_bytes
from systemsieve.models.storage import FileItem, FolderItem

FILE_COLUMNS = ["Select", "Path", "Size", "Category", "Modified"]
FCOL_CHECK, FCOL_PATH, FCOL_SIZE, FCOL_CATEGORY, FCOL_MODIFIED = range(5)

FOLDER_COLUMNS = ["Path", "Total Size", "Files", "Subfolders", "Modified"]


class FileItemsTableModel(QAbstractTableModel):
    def __init__(self, items: list[FileItem] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._items: list[FileItem] = items or []
        self._checked: set[str] = set()

    def set_items(self, items: list[FileItem]) -> None:
        self.beginResetModel()
        self._items = items
        self._checked &= {i.path for i in items}
        self.endResetModel()

    def item_at(self, row: int) -> FileItem:
        return self._items[row]

    def checked_items(self) -> list[FileItem]:
        return [i for i in self._items if i.path in self._checked]

    def clear_selection(self) -> None:
        self.beginResetModel()
        self._checked.clear()
        self.endResetModel()

    def select_all(self) -> None:
        self.beginResetModel()
        self._checked = {i.path for i in self._items}
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N803, B008
        return 0 if parent.isValid() else len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N803, B008
        return 0 if parent.isValid() else len(FILE_COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return FILE_COLUMNS[section]
        return None

    def flags(self, index: QModelIndex):  # noqa: N802
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == FCOL_CHECK:
            return base | Qt.ItemIsUserCheckable
        return base

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        item = self._items[index.row()]
        col = index.column()

        if role == Qt.CheckStateRole and col == FCOL_CHECK:
            return Qt.Checked if item.path in self._checked else Qt.Unchecked

        if role == Qt.ToolTipRole:
            return item.path
        if role == Qt.UserRole:
            if col == FCOL_SIZE:
                return item.size_bytes
            if col == FCOL_MODIFIED:
                return item.modified.timestamp() if item.modified else 0

        if role != Qt.DisplayRole:
            return None

        if col == FCOL_PATH:
            return item.path
        if col == FCOL_SIZE:
            return format_bytes(item.size_bytes)
        if col == FCOL_CATEGORY:
            return item.category.value
        if col == FCOL_MODIFIED:
            return item.modified.strftime("%Y-%m-%d") if item.modified else "-"
        return None

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):  # noqa: N802
        if role == Qt.CheckStateRole and index.column() == FCOL_CHECK:
            path = self._items[index.row()].path
            if value == Qt.Checked:
                self._checked.add(path)
            else:
                self._checked.discard(path)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True
        return False

    def selected_total_size(self) -> int:
        return sum(i.size_bytes for i in self.checked_items())


class FolderItemsTableModel(QAbstractTableModel):
    def __init__(self, items: list[FolderItem] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._items: list[FolderItem] = items or []

    def set_items(self, items: list[FolderItem]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()

    def item_at(self, row: int) -> FolderItem:
        return self._items[row]

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N803, B008
        return 0 if parent.isValid() else len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N803, B008
        return 0 if parent.isValid() else len(FOLDER_COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return FOLDER_COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: N802
        if not index.isValid():
            return None
        item = self._items[index.row()]
        col = index.column()
        if role == Qt.ToolTipRole:
            return item.path
        if role == Qt.UserRole:
            if col == 1:
                return item.total_size_bytes
            if col == 2:
                return item.file_count
            if col == 3:
                return item.subfolder_count
            if col == 4:
                return item.modified.timestamp() if item.modified else 0
        if role != Qt.DisplayRole:
            return None
        if col == 0:
            return item.path
        if col == 1:
            return format_bytes(item.total_size_bytes)
        if col == 2:
            return str(item.file_count)
        if col == 3:
            return str(item.subfolder_count)
        if col == 4:
            return item.modified.strftime("%Y-%m-%d") if item.modified else "-"
        return None
