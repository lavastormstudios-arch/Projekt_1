from typing import List, Optional
from datetime import date

from src.models.base_entry import Entry
from src.models.enums import EntryType, EntryStatus
from src.data.excel_store import ExcelStore


class EntryService:
    def __init__(self, store: ExcelStore):
        self.store = store

    def get_all(self) -> List[Entry]:
        return self.store.load_entries()

    def get_by_id(self, entry_id: str) -> Optional[Entry]:
        for e in self.store.load_entries():
            if e.id == entry_id:
                return e
        return None

    def add(self, entry: Entry):
        self.store.add_entry(entry)

    def update(self, entry: Entry):
        self.store.update_entry(entry)

    def delete(self, entry_id: str):
        self.store.delete_entry(entry_id)

    def filter_entries(
        self,
        entries: Optional[List[Entry]] = None,
        entry_type: Optional[EntryType] = None,
        status: Optional[EntryStatus] = None,
        supplier_name: Optional[str] = None,
        search_text: Optional[str] = None,
    ) -> List[Entry]:
        if entries is None:
            entries = self.get_all()
        result = entries
        if entry_type:
            result = [e for e in result if e.entry_type == entry_type]
        if status:
            result = [e for e in result if e.status == status]
        if supplier_name:
            result = [e for e in result if supplier_name.lower() in e.supplier_name.lower()]
        if search_text:
            text = search_text.lower()
            result = [e for e in result if (
                text in e.description.lower() or
                text in e.supplier_name.lower() or
                text in e.notes.lower() or
                text in e.kickback_articles.lower()
            )]
        return result

    def get_overdue(self, entries: Optional[List[Entry]] = None) -> List[Entry]:
        if entries is None:
            entries = self.get_all()
        return [e for e in entries if e.is_overdue()]

    def get_due_soon(self, days: int = 7, entries: Optional[List[Entry]] = None) -> List[Entry]:
        if entries is None:
            entries = self.get_all()
        result = []
        for e in entries:
            d = e.days_until_deadline()
            if d is not None and 0 <= d <= days and e.status == EntryStatus.OFFEN:
                result.append(e)
        return result

    def mark_overdue_entries(self):
        entries = self.get_all()
        changed = False
        for e in entries:
            if e.is_overdue() and e.status == EntryStatus.OFFEN:
                e.status = EntryStatus.UEBERFAELLIG
                changed = True
        if changed:
            self.store.save_entries(entries)
