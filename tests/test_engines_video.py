import subprocess

import pytest
from PIL import Image

from mirasu.core.engines.video import UnsupportedCodecError, rotate_video
from mirasu.core.metadata import VideoInfo, read_video_info
from mirasu.core.rotation import Rotation


def _is_reddish(px):
    r, g, b = px[:3]
    return r > 150 and b < 100


def _is_blueish(px):
    r, g, b = px[:3]
    return b > 150 and r < 100


def _first_frame(video_path, tmp_path, name="frame.png"):
    out = tmp_path / name
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path), "-frames:v", "1", str(out)],
        check=True,
        capture_output=True,
    )
    return Image.open(out)


@pytest.fixture
def tagged_video(asymmetric_video, tmp_path):
    """asymmetric_video with a real QuickTime display-matrix rotation=90 (CW) tag."""
    tagged = tmp_path / "tagged.mp4"
    tagged.write_bytes(asymmetric_video.read_bytes())
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Rotation=90", str(tagged)],
        check=True,
        capture_output=True,
    )
    return tagged


def test_rotate_cw90_moves_red_block_to_top_right(asymmetric_video, tmp_path):
    dst = tmp_path / "out.mp4"
    rotate_video(asymmetric_video, dst, Rotation.CW90)

    info = read_video_info(dst)
    assert (info.width, info.height) == (32, 64)
    frame = _first_frame(dst, tmp_path)
    assert _is_reddish(frame.getpixel((frame.size[0] - 2, 2)))
    assert _is_blueish(frame.getpixel((2, frame.size[1] - 2)))


def test_rotate_cw180_moves_red_block_to_bottom_right(asymmetric_video, tmp_path):
    dst = tmp_path / "out.mp4"
    rotate_video(asymmetric_video, dst, Rotation.CW180)

    info = read_video_info(dst)
    assert (info.width, info.height) == (64, 32)
    frame = _first_frame(dst, tmp_path)
    assert _is_reddish(frame.getpixel((frame.size[0] - 2, frame.size[1] - 2)))
    assert _is_blueish(frame.getpixel((2, 2)))


def test_rotate_ccw90_moves_red_block_to_bottom_left(asymmetric_video, tmp_path):
    dst = tmp_path / "out.mp4"
    rotate_video(asymmetric_video, dst, Rotation.CCW90)

    info = read_video_info(dst)
    assert (info.width, info.height) == (32, 64)
    frame = _first_frame(dst, tmp_path)
    assert _is_reddish(frame.getpixel((2, frame.size[1] - 2)))
    assert _is_blueish(frame.getpixel((frame.size[0] - 2, 2)))


def test_rotate_none_no_tag_raises(asymmetric_video, tmp_path):
    with pytest.raises(ValueError):
        rotate_video(asymmetric_video, tmp_path / "out.mp4", Rotation.NONE)


def test_rotate_none_decision_still_bakes_in_existing_tag(tagged_video, tmp_path):
    """'OK' (no additional rotation) on an already-tagged file must still
    bake the tag's rotation into real pixels and drop the tag - this is
    the core case the whole app exists for."""
    dst = tmp_path / "out.mp4"
    rotate_video(tagged_video, dst, Rotation.NONE)

    info = read_video_info(dst)
    assert info.has_rotation_tag is False
    assert (info.width, info.height) == (32, 64)
    frame = _first_frame(dst, tmp_path)
    assert _is_reddish(frame.getpixel((frame.size[0] - 2, 2)))


def test_decision_composes_with_existing_tag_in_one_pass(tagged_video, tmp_path):
    """Tag implies CW90; marking CW90 again should yield a net CW180."""
    dst = tmp_path / "out.mp4"
    rotate_video(tagged_video, dst, Rotation.CW90)

    info = read_video_info(dst)
    assert info.has_rotation_tag is False
    assert (info.width, info.height) == (64, 32)
    frame = _first_frame(dst, tmp_path)
    assert _is_reddish(frame.getpixel((frame.size[0] - 2, frame.size[1] - 2)))


def test_audio_and_duration_preserved(tmp_path):
    src = tmp_path / "base.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=blue:s=64x32:d=2:r=10,drawbox=x=0:y=0:w=16:h=16:color=red:t=fill",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(src),
        ],
        check=True,
        capture_output=True,
    )
    before = read_video_info(src)
    assert before.has_audio is True

    dst = tmp_path / "out.mp4"
    rotate_video(src, dst, Rotation.CW90)

    after = read_video_info(dst)
    assert after.has_audio is True
    assert abs(after.duration_s - before.duration_s) < 0.05


def test_unsupported_codec_raises(tmp_path):
    fake_info = VideoInfo(
        codec_name="vp9",
        width=64,
        height=32,
        duration_s=1.0,
        has_audio=False,
        has_rotation_tag=False,
        frame_count=10,
    )
    with pytest.raises(UnsupportedCodecError):
        rotate_video(tmp_path / "irrelevant.mp4", tmp_path / "out.mp4", Rotation.CW90, video_info=fake_info)
