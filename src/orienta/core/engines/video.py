"""Visually-lossless, size-preserving video rotation via ffmpeg.

Only the video stream is re-encoded (audio and subtitles are always
stream-copied, so presentation timestamps - and therefore A/V sync - are
untouched). Any existing rotation tag/display matrix on the source is
*not* hand-computed: ffmpeg's demuxer bakes a stream's display-matrix
rotation into the decoded pixels by default whenever it decodes for
filtering/encoding (its "autorotate" behavior), and the output simply has
no display matrix to carry over. The engine only adds its own `transpose`
filter for the user's triage decision, so both the tag correction and the
decision are baked into the same single re-encode pass.
"""

import subprocess
from pathlib import Path

from ..metadata import VideoInfo, read_video_info
from ..rotation import Rotation, ffmpeg_transpose_filter

# (encoder, crf) per source codec, tuned for "visually lossless" at each
# codec's own quantization scale - x265 needs a higher CRF than x264 for
# comparable perceived quality.
_CODEC_ENCODERS = {
    "h264": ("libx264", 16),
    "hevc": ("libx265", 18),
}


class UnsupportedCodecError(Exception):
    pass


def rotate_video(
    src: Path,
    dst: Path,
    decision_rotation: Rotation,
    video_info: VideoInfo | None = None,
) -> None:
    if video_info is None:
        video_info = read_video_info(src)

    if decision_rotation is Rotation.NONE and not video_info.has_rotation_tag:
        raise ValueError(
            "rotate_video called with nothing to do: no decision rotation and "
            "no existing rotation tag to bake in"
        )

    encoder = _CODEC_ENCODERS.get(video_info.codec_name)
    if encoder is None:
        raise UnsupportedCodecError(f"Unsupported video codec: {video_info.codec_name!r}")
    codec_name, crf = encoder

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-map", "0"]

    transpose = ffmpeg_transpose_filter(decision_rotation)
    if transpose:
        cmd += ["-vf", transpose]

    cmd += [
        "-c:v", codec_name,
        "-crf", str(crf),
        "-preset", "slow",
        "-c:a", "copy",
        "-c:s", "copy",
        str(dst),
    ]

    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=3600)
