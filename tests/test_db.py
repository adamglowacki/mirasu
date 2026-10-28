from orienta.core.db import StateDB
from orienta.core.rotation import Decision


def test_set_and_get_decision(tmp_path):
    db = StateDB(tmp_path / "state.db")
    path = tmp_path / "photo.jpg"
    db.set_decision(path, size=123, mtime_ns=456, decision=Decision.ROTATE_CW)
    assert db.get_decision(path, 123, 456) == Decision.ROTATE_CW
    db.close()


def test_get_decision_missing_returns_none(tmp_path):
    db = StateDB(tmp_path / "state.db")
    assert db.get_decision(tmp_path / "nope.jpg", 1, 1) is None
    db.close()


def test_set_decision_overwrites_and_resets_processed(tmp_path):
    db = StateDB(tmp_path / "state.db")
    path = tmp_path / "photo.jpg"
    db.set_decision(path, 123, 456, Decision.ROTATE_CW)
    db.mark_processed(path, 123, 456)
    assert db.is_processed(path, 123, 456)

    # Re-marking (e.g. user hit Backspace and re-decided) resets processed.
    db.set_decision(path, 123, 456, Decision.ROTATE_180)
    assert db.get_decision(path, 123, 456) == Decision.ROTATE_180
    assert not db.is_processed(path, 123, 456)
    db.close()


def test_different_mtime_is_different_key(tmp_path):
    db = StateDB(tmp_path / "state.db")
    path = tmp_path / "photo.jpg"
    db.set_decision(path, 123, 456, Decision.ROTATE_CW)
    assert db.get_decision(path, 123, 999) is None
    db.close()


def test_clear_decision(tmp_path):
    db = StateDB(tmp_path / "state.db")
    path = tmp_path / "photo.jpg"
    db.set_decision(path, 123, 456, Decision.ROTATE_CW)
    db.clear_decision(path, 123, 456)
    assert db.get_decision(path, 123, 456) is None
    db.close()


def test_survives_reopen(tmp_path):
    db_path = tmp_path / "state.db"
    path = tmp_path / "photo.jpg"
    db1 = StateDB(db_path)
    db1.set_decision(path, 123, 456, Decision.ROTATE_180)
    db1.close()

    db2 = StateDB(db_path)
    assert db2.get_decision(path, 123, 456) == Decision.ROTATE_180
    db2.close()


def test_context_manager(tmp_path):
    path = tmp_path / "photo.jpg"
    with StateDB(tmp_path / "state.db") as db:
        db.set_decision(path, 1, 1, Decision.OK)
        assert db.get_decision(path, 1, 1) == Decision.OK
