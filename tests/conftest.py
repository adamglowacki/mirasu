import subprocess
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def asymmetric_jpeg(tmp_path) -> Path:
    """A 64x32 JPEG with a distinct red block in the top-left corner only.

    Dimensions are multiples of 16 (the 4:2:0 JPEG MCU size) so jpegtran's
    lossless rotation never needs to trim edge pixels, keeping the expected
    pixel positions exact. Used to verify rotation direction empirically:
    after a correct 90 CW rotation, the red block must end up in the
    top-right corner, etc.
    """
    path = tmp_path / "asym.jpg"
    img = Image.new("RGB", (64, 32), "blue")
    for x in range(16):
        for y in range(16):
            img.putpixel((x, y), (255, 0, 0))
    img.save(path, format="JPEG", quality=95)
    return path


@pytest.fixture
def asymmetric_heic(tmp_path) -> Path:
    """Same pattern as asymmetric_jpeg, saved as HEIC."""
    import pillow_heif

    pillow_heif.register_heif_opener()
    path = tmp_path / "asym.heic"
    img = Image.new("RGB", (64, 32), "blue")
    for x in range(16):
        for y in range(16):
            img.putpixel((x, y), (255, 0, 0))
    img.save(path, format="HEIF", quality=-1)
    return path


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)


@pytest.fixture
def asymmetric_video(tmp_path) -> Path:
    """A short H.264 MP4, 64x32, with a red block top-left and audio tone."""
    path = tmp_path / "asym.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x32:d=1:r=10,drawbox=x=0:y=0:w=16:h=16:color=red:t=fill",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ]
    )
    return path
