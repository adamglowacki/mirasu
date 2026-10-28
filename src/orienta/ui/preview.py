"""Preview generation: a thumbnail/frame already corrected for any existing
orientation tag, so what you see is what a correct player/viewer would
currently show you.
"""

import hashlib
import subprocess
import tempfile
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

from ..core.scanner import FileEntry, Kind  # noqa: E402

_CACHE_DIR = Path(tempfile.gettempdir()) / "orienta-preview-cache"


def _cache_path(entry: FileEntry, suffix: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = f"{entry.path}:{entry.size}:{entry.mtime_ns}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:24]
    return _CACHE_DIR / f"{digest}{suffix}"


def _load_pixbuf_oriented(path: Path) -> GdkPixbuf.Pixbuf:
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
    return pixbuf.apply_embedded_orientation() or pixbuf


def get_preview_pixbuf(entry: FileEntry) -> GdkPixbuf.Pixbuf:
    """A GdkPixbuf of the file, already corrected for any existing tag."""
    if entry.kind is Kind.JPEG:
        return _load_pixbuf_oriented(entry.path)

    if entry.kind is Kind.HEIC:
        png_path = _cache_path(entry, ".png")
        if not png_path.exists():
            _render_heic_preview(entry.path, png_path)
        return _load_pixbuf_oriented(png_path)

    if entry.kind is Kind.VIDEO:
        png_path = _cache_path(entry, ".png")
        if not png_path.exists():
            _extract_video_frame(entry.path, png_path)
        # ffmpeg's default autorotate already baked in any display-matrix
        # rotation when extracting the frame, so no embedded-orientation
        # step is needed here.
        return GdkPixbuf.Pixbuf.new_from_file(str(png_path))

    raise ValueError(f"Unknown kind: {entry.kind}")


def _render_heic_preview(src: Path, dst_png: Path) -> None:
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    img = Image.open(src)
    img.load()
    # Preserve the embedded EXIF orientation when flattening to PNG, since
    # PNG has no EXIF-orientation convention of its own.
    try:
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img) or img
    except Exception:
        pass
    img.convert("RGB").save(dst_png, format="PNG")


def _extract_video_frame(src: Path, dst_png: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-frames:v", "1", str(dst_png)],
        check=True,
        capture_output=True,
        timeout=60,
    )
