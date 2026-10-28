from girasol.core.scanner import Kind, classify, scan


def test_classify_extensions():
    from pathlib import Path

    assert classify(Path("a.jpg")) == Kind.JPEG
    assert classify(Path("a.JPEG")) == Kind.JPEG
    assert classify(Path("a.heic")) == Kind.HEIC
    assert classify(Path("a.HEIF")) == Kind.HEIC
    assert classify(Path("a.mp4")) == Kind.VIDEO
    assert classify(Path("a.MOV")) == Kind.VIDEO
    assert classify(Path("a.txt")) is None
    assert classify(Path("a")) is None


def test_scan_flat_directory(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "b.mov").write_bytes(b"x")
    (tmp_path / "c.txt").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "d.jpg").write_bytes(b"x")

    entries = scan(tmp_path, recursive=False)
    names = sorted(e.path.name for e in entries)
    assert names == ["a.jpg", "b.mov"]


def test_scan_recursive(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "d.heic").write_bytes(b"x")

    entries = scan(tmp_path, recursive=True)
    names = sorted(e.path.name for e in entries)
    assert names == ["a.jpg", "d.heic"]


def test_scan_skips_backup_folder(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    backup = tmp_path / ".girasol-originals"
    backup.mkdir()
    (backup / "a.jpg").write_bytes(b"old")

    entries = scan(tmp_path, recursive=True)
    assert len(entries) == 1
    assert entries[0].path == tmp_path / "a.jpg"


def test_scan_entry_has_size_and_mtime(tmp_path):
    f = tmp_path / "a.jpg"
    f.write_bytes(b"hello")
    entries = scan(tmp_path)
    assert entries[0].size == 5
    assert entries[0].mtime_ns == f.stat().st_mtime_ns
