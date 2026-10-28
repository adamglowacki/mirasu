from orienta.core.db import StateDB
from orienta.core.rotation import Decision
from orienta.core.scanner import Kind
from orienta.core.triage import TriageSession


def _entries(tmp_path, names):
    from orienta.core.scanner import FileEntry

    for name in names:
        (tmp_path / name).write_bytes(b"x")

    return [
        FileEntry(path=tmp_path / name, size=1, mtime_ns=i, kind=Kind.JPEG)
        for i, name in enumerate(names)
    ]


def test_fresh_session_starts_at_zero(tmp_path):
    entries = _entries(tmp_path, ["a.jpg", "b.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)
    assert session.index == 0
    assert session.current.path.name == "a.jpg"
    assert session.is_finished is False


def test_mark_persists_and_advances(tmp_path):
    entries = _entries(tmp_path, ["a.jpg", "b.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)

    session.mark(Decision.ROTATE_CW)

    assert session.index == 1
    assert session.current.path.name == "b.jpg"
    assert db.get_decision(entries[0].path, entries[0].size, entries[0].mtime_ns) == Decision.ROTATE_CW


def test_finishes_after_last_mark(tmp_path):
    entries = _entries(tmp_path, ["a.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)

    session.mark(Decision.OK)

    assert session.is_finished is True
    assert session.current is None


def test_go_back_moves_index_without_erasing_decision(tmp_path):
    entries = _entries(tmp_path, ["a.jpg", "b.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)

    session.mark(Decision.ROTATE_CW)
    session.go_back()

    assert session.index == 0
    assert session.decision_at(0) == Decision.ROTATE_CW  # still remembered until re-marked

    session.mark(Decision.ROTATE_180)  # re-decide
    assert session.decision_at(0) == Decision.ROTATE_180


def test_go_back_at_start_is_noop(tmp_path):
    entries = _entries(tmp_path, ["a.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)
    session.go_back()
    assert session.index == 0


def test_skip_advances_without_recording_decision(tmp_path):
    entries = _entries(tmp_path, ["a.jpg", "b.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)

    session.skip()

    assert session.index == 1
    assert session.decision_at(0) is None
    assert session.unmarked_count() == 2  # neither entry has a recorded decision


def test_summary_counts_decisions(tmp_path):
    entries = _entries(tmp_path, ["a.jpg", "b.jpg", "c.jpg"])
    db = StateDB(tmp_path / "state.db")
    session = TriageSession(entries, db)

    session.mark(Decision.OK)
    session.mark(Decision.ROTATE_CW)
    session.mark(Decision.ROTATE_CW)

    summary = session.summary()
    assert summary[Decision.OK] == 1
    assert summary[Decision.ROTATE_CW] == 2
    assert summary[Decision.ROTATE_CCW] == 0


def test_resumes_from_existing_db_decisions(tmp_path):
    entries = _entries(tmp_path, ["a.jpg", "b.jpg", "c.jpg"])
    db = StateDB(tmp_path / "state.db")
    db.set_decision(entries[0].path, entries[0].size, entries[0].mtime_ns, Decision.OK)

    session = TriageSession(entries, db)

    assert session.index == 1  # resumes right after the already-decided file
    assert session.decision_at(0) == Decision.OK
    assert session.unmarked_count() == 2


def test_fully_decided_session_is_immediately_finished(tmp_path):
    entries = _entries(tmp_path, ["a.jpg"])
    db = StateDB(tmp_path / "state.db")
    db.set_decision(entries[0].path, entries[0].size, entries[0].mtime_ns, Decision.OK)

    session = TriageSession(entries, db)
    assert session.is_finished is True
