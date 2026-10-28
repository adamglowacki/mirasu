from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from ..core.db import StateDB, default_db_path  # noqa: E402
from ..core.pipeline import process_file  # noqa: E402
from ..core.scanner import scan  # noqa: E402
from ..core.triage import TriageSession  # noqa: E402
from .process_window import ProcessWindow  # noqa: E402
from .triage_window import TriageWindow  # noqa: E402

APPLICATION_ID = "org.mirasu.Mirasu"


class MirasuApplication(Adw.Application):
    def __init__(
        self, directory: Path | None, recursive: bool = False, db_path: Path | None = None
    ):
        super().__init__(application_id=APPLICATION_ID)
        self.directory = directory
        self.recursive = recursive
        self.db_path = db_path or default_db_path()
        self._triage_window = None
        self._process_window = None

    def do_activate(self) -> None:
        if self.directory is None:
            self._prompt_for_directory()
        else:
            self._start_triage(self.directory)

    def _prompt_for_directory(self) -> None:
        dialog = Gtk.FileDialog(title="Choose a folder to triage")

        def on_chosen(dlg: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
            try:
                folder = dlg.select_folder_finish(result)
            except GLib.Error:
                self.quit()
                return
            self._start_triage(Path(folder.get_path()))

        dialog.select_folder(None, None, on_chosen)

    def _start_triage(self, directory: Path) -> None:
        entries = scan(directory, recursive=self.recursive)
        state_db = StateDB(self.db_path)
        session = TriageSession(entries, state_db)

        self._triage_window = TriageWindow(
            application=self,
            session=session,
            on_finished=self._start_processing,
        )
        self._triage_window.present()

    def _start_processing(self, session: TriageSession) -> None:
        self._process_window = ProcessWindow(
            application=self,
            session=session,
            process_file_fn=process_file,
        )
        self._process_window.present()
        if self._triage_window is not None:
            self._triage_window.close()
