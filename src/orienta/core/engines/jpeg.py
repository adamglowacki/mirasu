"""Lossless JPEG rotation via jpegtran's DCT-coefficient transform.

The image is never fully decoded/re-encoded, so this is bit-exact aside
from trimming a sliver of edge pixels when a dimension isn't a multiple of
the JPEG MCU size (see design.md "Known limitations").
"""

import subprocess
from pathlib import Path

from ..rotation import Rotation

_JPEGTRAN_DEGREES = {
    Rotation.CW90: "90",
    Rotation.CW180: "180",
    Rotation.CCW90: "270",
}


def rotate_jpeg(src: Path, dst: Path, rotation: Rotation) -> None:
    if rotation is Rotation.NONE:
        raise ValueError("rotate_jpeg called with Rotation.NONE; nothing to do")

    degrees = _JPEGTRAN_DEGREES[rotation]
    subprocess.run(
        [
            "jpegtran",
            "-rotate",
            degrees,
            "-trim",
            "-copy",
            "all",
            "-outfile",
            str(dst),
            str(src),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )

    # Pixels are now physically correct: reset Orientation so no viewer
    # double-rotates. The embedded thumbnail/preview is stale (it still
    # shows the old orientation) and isn't worth the complexity of rotating
    # separately, so it's stripped rather than left wrong.
    subprocess.run(
        [
            "exiftool",
            "-overwrite_original",
            "-Orientation#=1",
            "-ThumbnailImage=",
            "-PreviewImage=",
            str(dst),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
