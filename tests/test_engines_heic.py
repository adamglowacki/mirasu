import subprocess

import pillow_heif
import pytest
from PIL import Image

from girasol.core.engines.heic import rotate_heic
from girasol.core.metadata import read_exif_orientation
from girasol.core.rotation import Rotation

pillow_heif.register_heif_opener()


def _is_reddish(px):
    r, g, b = px[:3]
    return r > 150 and b < 100


def _is_blueish(px):
    r, g, b = px[:3]
    return b > 150 and r < 100


def test_rotate_cw90_moves_red_block_to_top_right(asymmetric_heic, tmp_path):
    dst = tmp_path / "out.heic"
    rotate_heic(asymmetric_heic, dst, Rotation.CW90)

    img = Image.open(dst)
    assert img.size == (32, 64)
    assert _is_reddish(img.getpixel((24, 8)))
    assert _is_blueish(img.getpixel((4, 60)))


def test_rotate_cw180_moves_red_block_to_bottom_right(asymmetric_heic, tmp_path):
    dst = tmp_path / "out.heic"
    rotate_heic(asymmetric_heic, dst, Rotation.CW180)

    img = Image.open(dst)
    assert img.size == (64, 32)
    assert _is_reddish(img.getpixel((56, 24)))
    assert _is_blueish(img.getpixel((4, 4)))


def test_rotate_ccw90_moves_red_block_to_bottom_left(asymmetric_heic, tmp_path):
    dst = tmp_path / "out.heic"
    rotate_heic(asymmetric_heic, dst, Rotation.CCW90)

    img = Image.open(dst)
    assert img.size == (32, 64)
    assert _is_reddish(img.getpixel((8, 56)))
    assert _is_blueish(img.getpixel((28, 4)))


def test_rotate_none_raises(asymmetric_heic, tmp_path):
    with pytest.raises(ValueError):
        rotate_heic(asymmetric_heic, tmp_path / "out.heic", Rotation.NONE)


def test_rotate_resets_orientation_tag(asymmetric_heic, tmp_path):
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Orientation#=6", str(asymmetric_heic)],
        check=True,
        capture_output=True,
    )
    assert read_exif_orientation(asymmetric_heic) == 6

    dst = tmp_path / "out.heic"
    rotate_heic(asymmetric_heic, dst, Rotation.CW90)
    assert read_exif_orientation(dst) == 1
