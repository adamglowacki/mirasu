"""Near-lossless HEIC/HEIF rotation via decode -> exact pixel transpose -> re-encode.

Unlike JPEG, there's no bitstream-level lossless rotation trick for HEIF, so
this is one generation of re-encode at libheif's maximum ("lossless",
quality=-1) setting. In practice this is visually indistinguishable but, as
documented in design.md, it is not bit-exact the way the JPEG engine is -
this module is the one place that distinction actually matters.
"""

import subprocess
from pathlib import Path

import pillow_heif
from PIL import Image

from ..rotation import Rotation

pillow_heif.register_heif_opener()

# PIL's Transpose.ROTATE_N constants rotate N degrees counter-clockwise, so
# a clockwise Rotation.CW90 needs PIL's ROTATE_270, and vice versa.
_PIL_TRANSPOSE = {
    Rotation.CW90: Image.Transpose.ROTATE_270,
    Rotation.CW180: Image.Transpose.ROTATE_180,
    Rotation.CCW90: Image.Transpose.ROTATE_90,
}


def rotate_heic(src: Path, dst: Path, rotation: Rotation) -> None:
    if rotation is Rotation.NONE:
        raise ValueError("rotate_heic called with Rotation.NONE; nothing to do")

    img = Image.open(src)
    img.load()
    rotated = img.transpose(_PIL_TRANSPOSE[rotation])
    rotated.save(dst, format="HEIF", quality=-1, exif=img.info.get("exif"))

    # Pixels are now physically correct: reset Orientation so no viewer
    # double-rotates (the exif blob carried over above still has the old
    # tag value).
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Orientation#=1", str(dst)],
        check=True,
        capture_output=True,
        timeout=30,
    )
