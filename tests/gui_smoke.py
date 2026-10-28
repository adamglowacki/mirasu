"""Standalone (non-pytest) smoke test: launches the real Adw.Application
under a headless X server and drives it programmatically (no synthetic X11
key events - we're checking that *our* widget tree and refresh logic work
on this exact GTK4/libadwaita/PyGObject version, not re-testing GTK's own
event plumbing). Run via `xvfb-run -a python3 tests/gui_smoke.py`.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mirasu.core.rotation import Decision  # noqa: E402
from mirasu.ui.app import MirasuApplication  # noqa: E402

errors: list[str] = []


def make_sample_dir() -> Path:
    from PIL import Image

    import pillow_heif

    pillow_heif.register_heif_opener()

    d = Path(tempfile.mkdtemp(prefix="mirasu-smoke-"))
    img = Image.new("RGB", (64, 32), "blue")
    img.save(d / "a.jpg", format="JPEG")
    img.save(d / "b.heic", format="HEIF", quality=-1)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=blue:s=64x32:d=1:r=5",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(d / "c.mp4"),
        ],
        check=True,
        capture_output=True,
    )
    return d


def main() -> int:
    sample_dir = make_sample_dir()
    app = MirasuApplication(sample_dir, recursive=False, db_path=sample_dir / "state.db")

    state = {"phase": "waiting_for_triage"}

    def step() -> bool:
        try:
            if state["phase"] == "waiting_for_triage":
                win = app._triage_window
                if win is None:
                    return True  # keep polling
                n = len(win.session.entries)
                if n != 3:
                    raise AssertionError(f"expected 3 entries, got {n}")
                for _ in range(n):
                    win.session.mark(Decision.OK)
                    win._refresh()
                if not win.session.is_finished:
                    raise AssertionError("session should be finished after marking all entries")
                win._on_start_clicked(None)
                state["phase"] = "waiting_for_processing"
                return True

            if state["phase"] == "waiting_for_processing":
                pw = app._process_window
                if pw is None:
                    raise AssertionError("process window was not created")
                if pw._done < len(pw._to_process):
                    return True  # keep polling
                log = pw.log_buffer.get_text(
                    pw.log_buffer.get_start_iter(), pw.log_buffer.get_end_iter(), False
                )
                if "FAILED" in log:
                    raise AssertionError(f"processing reported failures:\n{log}")
                state["phase"] = "done"
                GLib.idle_add(app.quit)
                return False

        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))
            GLib.idle_add(app.quit)
            return False

        return True

    def on_activate(_app):
        GLib.timeout_add(50, step)

    app.connect("activate", on_activate)
    GLib.timeout_add_seconds(30, lambda: (errors.append("timed out"), app.quit(), False)[2])

    app.run([])
    shutil.rmtree(sample_dir, ignore_errors=True)

    if errors:
        print("SMOKE TEST FAILED:", errors)
        return 1
    print("SMOKE TEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
