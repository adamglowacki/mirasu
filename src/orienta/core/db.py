"""Persistent triage state, keyed by (path, size, mtime).

Keying on size+mtime (not just path) means that if a file is edited or
replaced between scans, its old decision is simply orphaned rather than
silently reused.
"""

import sqlite3
from pathlib import Path

from .rotation import Decision

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    path TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    decision INTEGER NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (path, size, mtime_ns)
);
"""


def default_db_path() -> Path:
    import os

    state_home = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state_home) / "orienta" / "orienta.db"


class StateDB:
    def __init__(self, db_path: Path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StateDB":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def set_decision(self, path: Path, size: int, mtime_ns: int, decision: Decision) -> None:
        self._conn.execute(
            """
            INSERT INTO decisions(path, size, mtime_ns, decision, processed, updated_at)
            VALUES (?, ?, ?, ?, 0, datetime('now'))
            ON CONFLICT(path, size, mtime_ns) DO UPDATE SET
                decision = excluded.decision,
                processed = 0,
                updated_at = excluded.updated_at
            """,
            (str(path), size, mtime_ns, int(decision)),
        )
        self._conn.commit()

    def get_decision(self, path: Path, size: int, mtime_ns: int) -> Decision | None:
        row = self._conn.execute(
            "SELECT decision FROM decisions WHERE path = ? AND size = ? AND mtime_ns = ?",
            (str(path), size, mtime_ns),
        ).fetchone()
        return Decision(row[0]) if row is not None else None

    def is_processed(self, path: Path, size: int, mtime_ns: int) -> bool:
        row = self._conn.execute(
            "SELECT processed FROM decisions WHERE path = ? AND size = ? AND mtime_ns = ?",
            (str(path), size, mtime_ns),
        ).fetchone()
        return bool(row and row[0])

    def mark_processed(self, path: Path, size: int, mtime_ns: int) -> None:
        self._conn.execute(
            "UPDATE decisions SET processed = 1, updated_at = datetime('now') "
            "WHERE path = ? AND size = ? AND mtime_ns = ?",
            (str(path), size, mtime_ns),
        )
        self._conn.commit()

    def clear_decision(self, path: Path, size: int, mtime_ns: int) -> None:
        self._conn.execute(
            "DELETE FROM decisions WHERE path = ? AND size = ? AND mtime_ns = ?",
            (str(path), size, mtime_ns),
        )
        self._conn.commit()
