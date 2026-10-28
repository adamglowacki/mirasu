import subprocess

from orienta.core.metadata import read_exif_orientation, read_video_info


def test_read_exif_orientation_default_is_1(asymmetric_jpeg):
    assert read_exif_orientation(asymmetric_jpeg) == 1


def test_read_exif_orientation_reads_set_tag(asymmetric_jpeg):
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Orientation#=6", str(asymmetric_jpeg)],
        check=True,
        capture_output=True,
    )
    assert read_exif_orientation(asymmetric_jpeg) == 6


def test_read_exif_orientation_missing_file_defaults_to_1(tmp_path):
    assert read_exif_orientation(tmp_path / "nope.jpg") == 1


def test_read_video_info_basic(asymmetric_video):
    info = read_video_info(asymmetric_video)
    assert info.codec_name == "h264"
    assert info.width == 64
    assert info.height == 32
    assert info.has_audio is True
    assert info.has_rotation_tag is False
    assert 0.9 <= info.duration_s <= 1.1


def test_read_video_info_detects_rotation_tag(asymmetric_video, tmp_path):
    # Real camera files (e.g. iPhone) carry a QuickTime display-matrix
    # rotation, not a plain stream "rotate" tag. exiftool's -Rotation
    # writes that same real display matrix, which is what we need to
    # detect here (and is what ffmpeg's own autorotate demuxer logic acts
    # on, per design.md).
    tagged = tmp_path / "tagged.mp4"
    tagged.write_bytes(asymmetric_video.read_bytes())
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Rotation=90", str(tagged)],
        check=True,
        capture_output=True,
    )
    info = read_video_info(tagged)
    assert info.has_rotation_tag is True
