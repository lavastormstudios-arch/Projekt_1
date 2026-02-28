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

    def get_active_umsatzbonus_for_supplier(
        self, supplier_id: str, supplier_name: str, exclude_id: str = None
    ) -> Optional[Entry]:
        """Returns an active (non-billed, non-cancelled) Umsatzbonus entry for the supplier, or None."""
        final = (EntryStatus.ABGERECHNET, EntryStatus.STORNIERT)
        for e in self.get_all():
            if e.entry_type != EntryType.UMSATZBONUS:
                continue
            if exclude_id and e.id == exclude_id:
                continue
            if e.status in final:
                continue
            if supplier_id and e.supplier_id and e.supplier_id == supplier_id:
                return e
            if e.supplier_name.lower() == supplier_name.lower():
                return e
        return None

    def create_annual_followup(self, entry: Entry) -> Entry:
        """Creates and saves a copy of a Umsatzbonus entry shifted by one year."""
        import uuid

        def shift_year(d):
            if d is None:
                return None
            try:
                return d.replace(year=d.year + 1)
            except ValueError:  # Feb 29 in non-leap year
                return d.replace(year=d.year + 1, day=28)

        new_entry = Entry(
            id=str(uuid.uuid4())[:8],
            entry_type=entry.entry_type,
            supplier_id=entry.supplier_id,
            supplier_name=entry.supplier_name,
            description=entry.description,
            status=EntryStatus.OFFEN,
            amount=entry.amount,
            amount_billed=0.0,
            date_start=shift_year(entry.date_start),
            date_end=shift_year(entry.date_end),
            billing_deadline=shift_year(entry.billing_deadline),
            date_billed=None,
            umsatzbonus_staffeln=entry.umsatzbonus_staffeln,
            notes=entry.notes,
            jaehrlich_wiederholen=True,
        )
        self.add(new_entry)
        return new_entry
