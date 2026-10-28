import subprocess

import pytest
from PIL import Image

from orienta.core.db import StateDB
from orienta.core.pipeline import VerificationError, needs_processing, process_file
from orienta.core.rotation import Decision
from orienta.core.scanner import ORIGINALS_BACKUP_DIR_NAME, Kind, scan


def _entry_for(tmp_path, name):
    entries = scan(tmp_path)
    (match,) = [e for e in entries if e.path.name == name]
    return match


def test_needs_processing_jpeg_no_tag_ok_is_false(tmp_path, asymmetric_jpeg):
    target = tmp_path / "a.jpg"
    target.write_bytes(asymmetric_jpeg.read_bytes())
    entry = _entry_for(tmp_path, "a.jpg")
    assert needs_processing(entry, Decision.OK) is False


def test_needs_processing_jpeg_tagged_ok_is_true(tmp_path, asymmetric_jpeg):
    target = tmp_path / "a.jpg"
    target.write_bytes(asymmetric_jpeg.read_bytes())
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Orientation#=6", str(target)],
        check=True,
        capture_output=True,
    )
    entry = _entry_for(tmp_path, "a.jpg")
    assert needs_processing(entry, Decision.OK) is True


def test_needs_processing_video_no_tag_ok_is_false(tmp_path, asymmetric_video):
    target = tmp_path / "a.mp4"
    target.write_bytes(asymmetric_video.read_bytes())
    entry = _entry_for(tmp_path, "a.mp4")
    assert needs_processing(entry, Decision.OK) is False


def test_needs_processing_video_tagged_ok_is_true(tmp_path, asymmetric_video):
    target = tmp_path / "a.mp4"
    target.write_bytes(asymmetric_video.read_bytes())
    subprocess.run(
        ["exiftool", "-overwrite_original", "-Rotation=90", str(target)],
        check=True,
        capture_output=True,
    )
    entry = _entry_for(tmp_path, "a.mp4")
    assert needs_processing(entry, Decision.OK) is True


def test_process_file_ok_no_tag_is_untouched_noop(tmp_path, asymmetric_jpeg):
    target = tmp_path / "a.jpg"
    original_bytes = asymmetric_jpeg.read_bytes()
    target.write_bytes(original_bytes)
    entry = _entry_for(tmp_path, "a.jpg")

    db = StateDB(tmp_path / "state.db")
    db.set_decision(entry.path, entry.size, entry.mtime_ns, Decision.OK)
    result = process_file(entry, Decision.OK, state_db=db)

    assert result.processed is False
    assert target.read_bytes() == original_bytes  # byte-for-byte untouched
    assert not (tmp_path / ORIGINALS_BACKUP_DIR_NAME).exists()
    assert db.is_processed(entry.path, entry.size, entry.mtime_ns)
    db.close()


def test_process_file_rotates_backs_up_and_promotes(tmp_path, asymmetric_jpeg):
    target = tmp_path / "a.jpg"
    original_bytes = asymmetric_jpeg.read_bytes()
    target.write_bytes(original_bytes)
    entry = _entry_for(tmp_path, "a.jpg")

    db = StateDB(tmp_path / "state.db")
    db.set_decision(entry.path, entry.size, entry.mtime_ns, Decision.ROTATE_CW)
    result = process_file(entry, Decision.ROTATE_CW, state_db=db)

    assert result.processed is True
    assert result.backed_up_to is not None
    assert result.backed_up_to.read_bytes() == original_bytes  # untouched original preserved
    assert target.exists()

    rotated = Image.open(target)
    assert rotated.size == (32, 64)  # swapped: rotation actually happened
    assert db.is_processed(entry.path, entry.size, entry.mtime_ns)
    db.close()


def test_process_file_verification_failure_leaves_original_untouched(tmp_path, asymmetric_jpeg, monkeypatch):
    target = tmp_path / "a.jpg"
    original_bytes = asymmetric_jpeg.read_bytes()
    target.write_bytes(original_bytes)
    entry = _entry_for(tmp_path, "a.jpg")

    def _write_garbage(src, dst, rotation):
        dst.write_bytes(b"not a real jpeg")

    monkeypatch.setattr("orienta.core.pipeline.rotate_jpeg", _write_garbage)

    with pytest.raises(VerificationError):
        process_file(entry, Decision.ROTATE_CW, state_db=None)

    assert target.read_bytes() == original_bytes  # untouched
    assert not (tmp_path / ORIGINALS_BACKUP_DIR_NAME).exists()
    tmp_name = f"{target.stem}.orienta-tmp{target.suffix}"
    assert not (tmp_path / tmp_name).exists()  # temp file cleaned up


def test_process_file_backup_name_collision_is_disambiguated(tmp_path, asymmetric_jpeg):
    target = tmp_path / "a.jpg"
    target.write_bytes(asymmetric_jpeg.read_bytes())
    backup_dir = tmp_path / ORIGINALS_BACKUP_DIR_NAME
    backup_dir.mkdir()
    (backup_dir / "a.jpg").write_bytes(b"pre-existing backup from an earlier run")

    entry = _entry_for(tmp_path, "a.jpg")
    result = process_file(entry, Decision.ROTATE_CW, state_db=None)

    assert result.backed_up_to != backup_dir / "a.jpg"
    assert result.backed_up_to.exists()
    assert (backup_dir / "a.jpg").read_bytes() == b"pre-existing backup from an earlier run"


def test_process_file_video_rotates_backs_up_and_promotes(tmp_path, asymmetric_video):
    target = tmp_path / "a.mp4"
    original_bytes = asymmetric_video.read_bytes()
    target.write_bytes(original_bytes)
    entry = _entry_for(tmp_path, "a.mp4")
    assert entry.kind is Kind.VIDEO

    result = process_file(entry, Decision.ROTATE_CW, state_db=None)

    assert result.processed is True
    assert result.backed_up_to.read_bytes() == original_bytes
    assert target.exists()
