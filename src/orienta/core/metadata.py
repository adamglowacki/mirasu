"""Reading existing orientation signals from files via exiftool/ffprobe."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


def read_exif_orientation(path: Path) -> int:
    """Numeric EXIF ``Orientation`` (1-8); defaults to 1 if absent/unreadable."""
    try:
        result = subprocess.run(
            ["exiftool", "-Orientation#", "-s3", str(path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 1

    value = result.stdout.strip()
    try:
        return int(value)
    except ValueError:
        return 1


def ffprobe_json(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


@dataclass(frozen=True)
class VideoInfo:
    codec_name: str
    width: int
    height: int
    duration_s: float
    has_audio: bool
    has_rotation_tag: bool
    frame_count: int | None


def read_video_info(path: Path) -> VideoInfo:
    data = ffprobe_json(path)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video_stream is None:
        raise ValueError(f"No video stream found in {path}")

    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    has_rotation_tag = False
    tags = video_stream.get("tags", {})
    if str(tags.get("rotate", "0")) != "0":
        has_rotation_tag = True
    for side_data in video_stream.get("side_data_list", []):
        if side_data.get("side_data_type") == "Display Matrix" and side_data.get("rotation", 0):
            has_rotation_tag = True

    duration_raw = data.get("format", {}).get("duration") or video_stream.get("duration")
    duration_s = float(duration_raw) if duration_raw is not None else 0.0

    frame_count = None
    if "nb_frames" in video_stream:
        try:
            frame_count = int(video_stream["nb_frames"])
        except ValueError:
            frame_count = None

    return VideoInfo(
        codec_name=video_stream.get("codec_name", ""),
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        duration_s=duration_s,
        has_audio=has_audio,
        has_rotation_tag=has_rotation_tag,
        frame_count=frame_count,
    )
