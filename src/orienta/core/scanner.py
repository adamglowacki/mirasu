"""Directory scanning and file-kind classification."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ORIGINALS_BACKUP_DIR_NAME = ".orienta-originals"


class Kind(Enum):
    JPEG = "jpeg"
    HEIC = "heic"
    VIDEO = "video"


_EXT_TO_KIND = {
    ".jpg": Kind.JPEG,
    ".jpeg": Kind.JPEG,
    ".heic": Kind.HEIC,
    ".heif": Kind.HEIC,
    ".mp4": Kind.VIDEO,
    ".m4v": Kind.VIDEO,
    ".mov": Kind.VIDEO,
}


@dataclass(frozen=True)
class FileEntry:
    path: Path
    size: int
    mtime_ns: int
    kind: Kind


def classify(path: Path) -> Kind | None:
    return _EXT_TO_KIND.get(path.suffix.lower())


def scan(directory: Path, recursive: bool = False) -> list[FileEntry]:
    directory = Path(directory)
    pattern_iter = directory.rglob("*") if recursive else directory.glob("*")

    entries = []
    for candidate in pattern_iter:
        if ORIGINALS_BACKUP_DIR_NAME in candidate.parts:
            continue
        if not candidate.is_file():
            continue
        kind = classify(candidate)
        if kind is None:
            continue
        stat = candidate.stat()
        entries.append(
            FileEntry(path=candidate, size=stat.st_size, mtime_ns=stat.st_mtime_ns, kind=kind)
        )

    entries.sort(key=lambda e: str(e.path))
    return entries
