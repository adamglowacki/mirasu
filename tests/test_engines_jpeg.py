import pytest
from PIL import Image

from girasol.core.engines.jpeg import rotate_jpeg
from girasol.core.metadata import read_exif_orientation
from girasol.core.rotation import Rotation

RED = (255, 0, 0)
BLUE = (0, 0, 255)


def _is_reddish(px):
    r, g, b = px
    return r > 150 and b < 100


def _is_blueish(px):
    r, g, b = px
    return b > 150 and r < 100


def test_rotate_cw90_moves_red_block_to_top_right(asymmetric_jpeg, tmp_path):
    dst = tmp_path / "out.jpg"
    rotate_jpeg(asymmetric_jpeg, dst, Rotation.CW90)

    img = Image.open(dst)
    assert img.size == (32, 64)  # dimensions swapped
    assert _is_reddish(img.getpixel((24, 8)))
    assert _is_blueish(img.getpixel((4, 60)))


def test_rotate_cw180_moves_red_block_to_bottom_right(asymmetric_jpeg, tmp_path):
    dst = tmp_path / "out.jpg"
    rotate_jpeg(asymmetric_jpeg, dst, Rotation.CW180)

    img = Image.open(dst)
    assert img.size == (64, 32)  # dimensions unchanged
    assert _is_reddish(img.getpixel((56, 24)))
    assert _is_blueish(img.getpixel((4, 4)))


def test_rotate_ccw90_moves_red_block_to_bottom_left(asymmetric_jpeg, tmp_path):
    dst = tmp_path / "out.jpg"
    rotate_jpeg(asymmetric_jpeg, dst, Rotation.CCW90)

    img = Image.open(dst)
    assert img.size == (32, 64)  # dimensions swapped
    assert _is_reddish(img.getpixel((8, 56)))
    assert _is_blueish(img.getpixel((28, 4)))


def test_rotate_none_raises(asymmetric_jpeg, tmp_path):
    with pytest.raises(ValueError):
        rotate_jpeg(asymmetric_jpeg, tmp_path / "out.jpg", Rotation.NONE)


def test_rotate_resets_orientation_tag(asymmetric_jpeg, tmp_path):
    import subprocess

    subprocess.run(
        ["exiftool", "-overwrite_original", "-Orientation#=6", str(asymmetric_jpeg)],
        check=True,
        capture_output=True,
    )
    assert read_exif_orientation(asymmetric_jpeg) == 6

    dst = tmp_path / "out.jpg"
    rotate_jpeg(asymmetric_jpeg, dst, Rotation.CW90)
    assert read_exif_orientation(dst) == 1


def test_rotate_strips_thumbnail(asymmetric_jpeg, tmp_path):
    import subprocess

    thumb = Image.new("RGB", (8, 8), "red")
    thumb_path = tmp_path / "thumb.jpg"
    thumb.save(thumb_path, format="JPEG")
    subprocess.run(
        [
            "exiftool",
            "-overwrite_original",
            f"-ThumbnailImage<={thumb_path}",
            str(asymmetric_jpeg),
        ],
        check=True,
        capture_output=True,
    )
    has_thumb = subprocess.run(
        ["exiftool", "-ThumbnailImage", "-s3", str(asymmetric_jpeg)],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert has_thumb != ""

    dst = tmp_path / "out.jpg"
    rotate_jpeg(asymmetric_jpeg, dst, Rotation.CW90)
    no_thumb = subprocess.run(
        ["exiftool", "-ThumbnailImage", "-s3", str(dst)],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert no_thumb == ""
