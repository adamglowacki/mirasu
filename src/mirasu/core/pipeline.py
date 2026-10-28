"""Orchestration: dispatch to the right engine, verify, then promote or fail.

Nothing overwrites the original until the engine's output has passed a
verification check. On success the original is moved into a
``.mirasu-originals`` backup folder and the new file takes its name; on
failure the original is left exactly as it was and the temp output is
removed.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path

from .db import StateDB
from .engines.heic import rotate_heic
from .engines.jpeg import rotate_jpeg
from .engines.video import rotate_video
from .metadata import read_exif_orientation, read_video_info
from .rotation import Decision, Rotation, effective_image_rotation
from .scanner import ORIGINALS_BACKUP_DIR_NAME, FileEntry, Kind


class VerificationError(Exception):
    pass


@dataclass
class ProcessResult:
    entry: FileEntry
    processed: bool  # False means the file needed no changes at all
    backed_up_to: Path | None = None


def needs_processing(entry: FileEntry, decision: Decision) -> bool:
    """Whether anything has to be written for this file.

    False only when the decision adds no rotation *and* there's no
    existing orientation tag left to bake in - the only true no-op case.
    """
    if entry.kind in (Kind.JPEG, Kind.HEIC):
        orientation = read_exif_orientation(entry.path)
        return effective_image_rotation(orientation, decision) is not Rotation.NONE
    if entry.kind is Kind.VIDEO:
        info = read_video_info(entry.path)
        return decision.to_rotation() is not Rotation.NONE or info.has_rotation_tag
    raise ValueError(f"Unknown kind: {entry.kind}")


def _rotate_to_temp(entry: FileEntry, decision: Decision, tmp_dst: Path) -> None:
    if entry.kind is Kind.JPEG:
        rotation = effective_image_rotation(read_exif_orientation(entry.path), decision)
        rotate_jpeg(entry.path, tmp_dst, rotation)
    elif entry.kind is Kind.HEIC:
        rotation = effective_image_rotation(read_exif_orientation(entry.path), decision)
        rotate_heic(entry.path, tmp_dst, rotation)
    elif entry.kind is Kind.VIDEO:
        rotate_video(entry.path, tmp_dst, decision.to_rotation())
    else:
        raise ValueError(f"Unknown kind: {entry.kind}")


def _verify(entry: FileEntry, output: Path) -> None:
    if entry.kind in (Kind.JPEG, Kind.HEIC):
        _verify_image(output)
    else:
        _verify_video(entry.path, output)


def _verify_image(output: Path) -> None:
    from PIL import Image

    try:
        with Image.open(output) as img:
            img.verify()
        with Image.open(output) as img2:
            width, height = img2.size
    except Exception as exc:  # noqa: BLE001 - any decode failure means verification failed
        raise VerificationError(f"Output image failed to open/verify: {exc}") from exc

    if width <= 0 or height <= 0:
        raise VerificationError("Output image has invalid dimensions")


def _verify_video(original: Path, output: Path) -> None:
    try:
        before = read_video_info(original)
        after = read_video_info(output)
    except Exception as exc:  # noqa: BLE001
        raise VerificationError(f"Could not read output video info: {exc}") from exc

    if before.has_audio and not after.has_audio:
        raise VerificationError("Output video lost its audio stream")

    tolerance = max(0.5, before.duration_s * 0.02)
    if before.duration_s > 0 and abs(after.duration_s - before.duration_s) > tolerance:
        raise VerificationError(
            f"Output duration {after.duration_s:.3f}s differs from source "
            f"{before.duration_s:.3f}s by more than {tolerance:.3f}s"
        )

    if after.width <= 0 or after.height <= 0:
        raise VerificationError("Output video has invalid dimensions")


def process_file(
    entry: FileEntry,
    decision: Decision,
    state_db: StateDB | None = None,
) -> ProcessResult:
    if not needs_processing(entry, decision):
        if state_db is not None:
            state_db.mark_processed(entry.path, entry.size, entry.mtime_ns)
        return ProcessResult(entry=entry, processed=False)

    tmp_dst = entry.path.with_name(f"{entry.path.stem}.mirasu-tmp{entry.path.suffix}")
    try:
        _rotate_to_temp(entry, decision, tmp_dst)
        _verify(entry, tmp_dst)
    except Exception:
        tmp_dst.unlink(missing_ok=True)
        raise

    backup_dir = entry.path.parent / ORIGINALS_BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / entry.path.name
    if backup_path.exists():
        backup_path = backup_dir / f"{entry.path.stem}.{entry.mtime_ns}{entry.path.suffix}"

    shutil.move(str(entry.path), str(backup_path))
    shutil.move(str(tmp_dst), str(entry.path))

    if state_db is not None:
        state_db.mark_processed(entry.path, entry.size, entry.mtime_ns)

    return ProcessResult(entry=entry, processed=True, backed_up_to=backup_path)
