import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from ..core.rotation import Decision  # noqa: E402
from ..core.triage import TriageSession  # noqa: E402
from .preview import get_preview_pixbuf  # noqa: E402

_KEY_TO_DECISION = {
    Gdk.KEY_Right: Decision.ROTATE_CW,
    Gdk.KEY_Left: Decision.ROTATE_CCW,
    Gdk.KEY_Down: Decision.ROTATE_180,
    Gdk.KEY_Up: Decision.OK,
    Gdk.KEY_space: Decision.OK,
}

_DECISION_LABEL = {
    Decision.OK: "OK",
    Decision.ROTATE_CW: "Rotate CW 90°",
    Decision.ROTATE_CCW: "Rotate CCW 90°",
    Decision.ROTATE_180: "Rotate 180°",
}


class TriageWindow(Adw.ApplicationWindow):
    """The triage screen: one file at a time, one keystroke per decision."""

    def __init__(self, application, session: TriageSession, on_finished=None, **kwargs):
        super().__init__(application=application, title="Orienta", **kwargs)
        self.session = session
        self.on_finished = on_finished
        self._start_button = None
        self.set_default_size(900, 700)

        toolbar_view = Adw.ToolbarView()
        self.header = Adw.HeaderBar()
        toolbar_view.add_top_bar(self.header)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        self.picture = Gtk.Picture()
        self.picture.set_vexpand(True)
        self.picture.set_hexpand(True)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        content.append(self.picture)

        self.status_label = Gtk.Label()
        self.status_label.set_wrap(True)
        content.append(self.status_label)

        hint = Gtk.Label(
            label=(
                "↑/Space OK  •  → Rotate CW  •  ← Rotate CCW  •  "
                "↓ Rotate 180°  •  Backspace: back  •  . : skip"
            )
        )
        hint.add_css_class("dim-label")
        content.append(hint)

        toolbar_view.set_content(content)
        self.set_content(toolbar_view)

        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        self._refresh()

    def _on_key_pressed(self, _controller, keyval, _keycode, _state):
        if self.session.is_finished:
            return False

        if keyval in _KEY_TO_DECISION:
            self.session.mark(_KEY_TO_DECISION[keyval])
        elif keyval == Gdk.KEY_BackSpace:
            self.session.go_back()
        elif keyval == Gdk.KEY_period:
            self.session.skip()
        else:
            return False

        self._refresh()
        return True

    def _refresh(self) -> None:
        if self.session.is_finished:
            self._show_summary()
            return

        entry = self.session.current
        n = len(self.session.entries)
        self.header.set_title_widget(
            Gtk.Label(label=f"{self.session.index + 1} / {n}  —  {entry.path.name}")
        )
        try:
            pixbuf = get_preview_pixbuf(entry)
            self.picture.set_pixbuf(pixbuf)
            self.status_label.set_label("")
        except Exception as exc:  # noqa: BLE001 - surface the error, don't crash the session
            self.picture.set_paintable(None)
            self.status_label.set_label(f"Couldn't preview this file: {exc}")

    def _show_summary(self) -> None:
        self.picture.set_paintable(None)
        self.header.set_title_widget(Gtk.Label(label="Review"))
        counts = self.session.summary()
        lines = [f"{_DECISION_LABEL[d]}: {c}" for d, c in counts.items() if c]
        unmarked = self.session.unmarked_count()
        if unmarked:
            lines.append(f"Skipped / unmarked: {unmarked}")
        self.status_label.set_label("\n".join(lines) or "Nothing to process.")

        if self._start_button is None:
            self._start_button = Gtk.Button(label="Start processing")
            self._start_button.add_css_class("suggested-action")
            self._start_button.connect("clicked", self._on_start_clicked)
            self.header.pack_end(self._start_button)

    def _on_start_clicked(self, _button) -> None:
        if self.on_finished is not None:
            self.on_finished(self.session)
