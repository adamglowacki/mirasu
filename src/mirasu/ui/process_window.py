import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ..core.db import StateDB  # noqa: E402
from ..core.triage import TriageSession  # noqa: E402


class ProcessWindow(Adw.ApplicationWindow):
    """Runs the batch rotation in a background thread with live progress."""

    def __init__(self, application, session: TriageSession, process_file_fn, **kwargs):
        super().__init__(application=application, title="Mirasu — Processing", **kwargs)
        self.session = session
        self._process_file_fn = process_file_fn
        self.set_default_size(700, 500)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(12)

        self.progress = Gtk.ProgressBar(show_text=True)
        box.append(self.progress)

        self.log_buffer = Gtk.TextBuffer()
        log_view = Gtk.TextView(buffer=self.log_buffer, editable=False, monospace=True)
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(log_view)
        box.append(scroller)

        toolbar_view.set_content(box)
        self.set_content(toolbar_view)

        self._to_process = [
            (entry, session.decision_at(i))
            for i, entry in enumerate(session.entries)
            if session.decision_at(i) is not None
        ]
        self._total = len(self._to_process) or 1
        self._done = 0

        threading.Thread(target=self._run, daemon=True).start()

    def _log(self, text: str) -> None:
        GLib.idle_add(self._append_log, text)

    def _append_log(self, text: str) -> bool:
        self.log_buffer.insert(self.log_buffer.get_end_iter(), text + "\n")
        return False

    def _set_progress(self, fraction: float, label: str) -> None:
        GLib.idle_add(self._apply_progress, fraction, label)

    def _apply_progress(self, fraction: float, label: str) -> bool:
        self.progress.set_fraction(fraction)
        self.progress.set_text(label)
        return False

    def _run(self) -> None:
        # sqlite3 connections can't cross threads, so this thread gets its own
        # StateDB rather than reusing the one the GTK main thread created.
        state_db = StateDB(self.session.state_db.path)
        try:
            for entry, decision in self._to_process:
                try:
                    result = self._process_file_fn(entry, decision, state_db)
                    if result.processed:
                        self._log(f"rotated   {entry.path.name}")
                    else:
                        self._log(f"unchanged {entry.path.name}")
                except Exception as exc:  # noqa: BLE001 - keep going, report, move on
                    self._log(f"FAILED    {entry.path.name}: {exc}")

                self._done += 1
                self._set_progress(
                    self._done / self._total, f"{self._done} / {len(self._to_process)}"
                )
        finally:
            state_db.close()

        self._log("Done.")
