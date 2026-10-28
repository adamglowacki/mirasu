"""GTK-free triage flow state: current file, decisions, resume, summary.

The UI layer is a thin shell that renders `session.current` and calls
`mark()`/`skip()`/`go_back()` from key handlers - all the flow logic lives
here so it can be tested without driving a GTK event loop.
"""

from .db import StateDB
from .rotation import Decision
from .scanner import FileEntry


class TriageSession:
    def __init__(self, entries: list[FileEntry], state_db: StateDB):
        self.entries = entries
        self.state_db = state_db
        self.decisions: dict[int, Decision] = {}

        for i, entry in enumerate(entries):
            existing = state_db.get_decision(entry.path, entry.size, entry.mtime_ns)
            if existing is not None:
                self.decisions[i] = existing

        self.index = next(
            (i for i in range(len(entries)) if i not in self.decisions),
            len(entries),
        )

    @property
    def current(self) -> FileEntry | None:
        if 0 <= self.index < len(self.entries):
            return self.entries[self.index]
        return None

    @property
    def is_finished(self) -> bool:
        return self.index >= len(self.entries)

    def mark(self, decision: Decision) -> None:
        entry = self.current
        if entry is None:
            return
        self.decisions[self.index] = decision
        self.state_db.set_decision(entry.path, entry.size, entry.mtime_ns, decision)
        self.index += 1

    def skip(self) -> None:
        if self.current is not None:
            self.index += 1

    def go_back(self) -> None:
        if self.index > 0:
            self.index -= 1

    def decision_at(self, index: int) -> Decision | None:
        return self.decisions.get(index)

    def summary(self) -> dict[Decision, int]:
        counts = {d: 0 for d in Decision}
        for decision in self.decisions.values():
            counts[decision] += 1
        return counts

    def unmarked_count(self) -> int:
        return len(self.entries) - len(self.decisions)
