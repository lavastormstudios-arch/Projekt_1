from typing import List, Tuple

from src.models.base_entry import Entry
from src.services.entry_service import EntryService


class ReminderService:
    def __init__(self, entry_service: EntryService, warn_days: int = 7):
        self.entry_service = entry_service
        self.warn_days = warn_days

    def check(self) -> Tuple[List[Entry], List[Entry]]:
        """Returns (overdue_entries, due_soon_entries)."""
        self.entry_service.mark_overdue_entries()
        entries = self.entry_service.get_all()
        overdue = self.entry_service.get_overdue(entries)
        due_soon = self.entry_service.get_due_soon(self.warn_days, entries)
        return overdue, due_soon

    def get_status_text(self) -> str:
        overdue, due_soon = self.check()
        parts = []
        if overdue:
            parts.append(f"{len(overdue)} überfällig")
        if due_soon:
            parts.append(f"{len(due_soon)} fällig in {self.warn_days} Tagen")
        return " | ".join(parts) if parts else "Keine anstehenden Fristen"
