from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from systemsieve.config import AppConfig
from systemsieve.elevation.manager import build_command_request
from systemsieve.elevation.validation import validate_elevated_request
from systemsieve.gui.models.applications_model import (
    COL_CHECK,
    COL_NAME,
    COL_SIZE,
    ApplicationsFilterProxyModel,
    ApplicationsTableModel,
)
from systemsieve.gui.pages.applications_page import ApplicationsPage
from systemsieve.gui.pages.storage_page import StoragePage
from systemsieve.gui.pages.updates_page import UpdatesPage
from systemsieve.gui.shell_actions import existing_location, open_path
from systemsieve.models.application import InstalledApplication
from systemsieve.models.operation import UninstallMethod, UninstallPlan, UninstallStep
from systemsieve.models.storage import FileItem
from systemsieve.package_management.uninstall import execute_bulk_uninstall
from systemsieve.package_management.winget import build_uninstall_command


def _application(name: str, *, size: int = 0, update: bool = False) -> InstalledApplication:
    return InstalledApplication(
        id=name.casefold(),
        display_name=name,
        estimated_size_bytes=size,
        winget_id=f"Example.{name}" if update else None,
        update_available=update,
        current_version="1.0" if update else None,
        available_version="2.0" if update else None,
        update_source="winget" if update else None,
    )


def test_application_checkbox_selection_and_numeric_sorting(qapp) -> None:
    model = ApplicationsTableModel(
        [_application("Small", size=10), _application("Large", size=100)]
    )
    proxy = ApplicationsFilterProxyModel()
    proxy.setSourceModel(model)

    assert model.setData(model.index(0, COL_CHECK), Qt.Checked, Qt.CheckStateRole)
    assert [app.display_name for app in model.checked_applications()] == ["Small"]

    proxy.sort(COL_SIZE, Qt.DescendingOrder)
    assert proxy.index(0, COL_NAME).data() == "Large"


def test_update_selection_keeps_identity_after_sorting(qapp) -> None:
    page = UpdatesPage(AppConfig())
    page.set_applications([_application("Zulu", update=True), _application("Alpha", update=True)])

    page.table.selectRow(0)
    selected = page._checked_applications()

    assert len(selected) == 1
    assert selected[0].display_name == "Alpha"


def test_update_checkbox_full_cell_is_clickable(qapp) -> None:
    page = UpdatesPage(AppConfig())
    page.set_applications([_application("Example", update=True)])
    page.resize(900, 500)
    page.show()
    qapp.processEvents()

    index = page.table.model().index(0, 0)
    QTest.mouseClick(
        page.table.viewport(), Qt.LeftButton, pos=page.table.visualRect(index).center()
    )
    qapp.processEvents()

    assert index.data(Qt.CheckStateRole) == Qt.Checked
    assert [app.display_name for app in page._checked_applications()] == ["Example"]


def test_application_checkbox_full_cell_is_clickable(qapp) -> None:
    page = ApplicationsPage(AppConfig())
    page.set_applications([_application("Example")])
    page.resize(900, 500)
    page.show()
    qapp.processEvents()

    index = page._proxy.index(0, COL_CHECK)
    QTest.mouseClick(
        page.table.viewport(), Qt.LeftButton, pos=page.table.visualRect(index).center()
    )
    qapp.processEvents()

    assert index.data(Qt.CheckStateRole) == Qt.Checked
    assert [app.display_name for app in page._model.checked_applications()] == ["Example"]


def test_all_storage_file_checkboxes_are_full_cell_clickable(qapp) -> None:
    page = StoragePage(AppConfig())
    page.resize(900, 500)
    page.show()
    contexts = [
        (page.files_table, page._files_model),
        (page.old_files_table, page._old_files_model),
        (page.recent_files_table, page._recent_files_model),
    ]

    for position, (table, model) in enumerate(contexts):
        model.set_items([FileItem(path=f"C:/demo/file-{position}.zip", size_bytes=100)])
        page.tabs.setCurrentWidget(table)
        qapp.processEvents()
        index = table.model().index(0, 0)
        QTest.mouseClick(table.viewport(), Qt.LeftButton, pos=table.visualRect(index).center())
        qapp.processEvents()
        assert index.data(Qt.CheckStateRole) == Qt.Checked
        assert len(model.checked_items()) == 1


def _uninstall_plan(name: str) -> UninstallPlan:
    return UninstallPlan(
        application_id=name.casefold(),
        application_name=name,
        method=UninstallMethod.STANDARD_UNINSTALL_COMMAND,
        steps=[
            UninstallStep(
                description=f"Remove {name}",
                command=["example-uninstaller.exe", "/remove"],
                requires_admin=False,
            )
        ],
    )


def test_dry_run_reports_each_completed_item() -> None:
    reported = []
    records = execute_bulk_uninstall(
        [_uninstall_plan("One"), _uninstall_plan("Two")],
        dry_run=True,
        on_result=lambda index, total, record: reported.append(
            (index, total, record.target_name, record.status.value)
        ),
    )

    assert len(records) == 2
    assert reported == [(1, 2, "One", "dry_run"), (2, 2, "Two", "dry_run")]


def test_uninstall_mode_is_explicit(qapp) -> None:
    page = ApplicationsPage(AppConfig(dry_run_default=True))
    assert page.uninstall_btn.text() == "Preview Uninstall"
    assert "no software will be removed" in page.dry_run_checkbox.text().lower()

    page.dry_run_checkbox.setChecked(False)
    assert page.uninstall_btn.text() == "Uninstall Selected"
    assert page.uninstall_btn.objectName() == "DangerButton"


def test_winget_uninstall_passes_elevated_validation() -> None:
    command = build_uninstall_command("Example.Package")
    valid, reason = validate_elevated_request(build_command_request(command))

    assert command[0] == "winget.exe"
    assert valid, reason


def test_existing_location_handles_registry_icon_index(tmp_path) -> None:
    executable = tmp_path / "Example App.exe"
    executable.touch()

    result = existing_location(f'"{executable}",-12')

    assert result == executable.resolve()


def test_open_path_validates_and_uses_windows_shell(tmp_path, monkeypatch) -> None:
    opened: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        "systemsieve.gui.shell_actions._shell_execute",
        lambda target, parameters=None: opened.append((target, parameters)),
    )

    open_path(tmp_path)

    assert opened == [(str(tmp_path.resolve()), None)]
