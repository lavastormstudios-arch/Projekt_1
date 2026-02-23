from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List
import json
import uuid

from src.models.enums import EntryType, EntryStatus


@dataclass
class Entry:
    entry_type: EntryType
    supplier_id: str
    supplier_name: str
    description: str = ""
    status: EntryStatus = EntryStatus.OFFEN
    amount: float = 0.0
    amount_billed: float = 0.0
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    billing_deadline: Optional[date] = None
    date_billed: Optional[date] = None
    # Kickback-specific (multi-article as JSON)
    kickback_articles: str = ""
    # Umsatzbonus-specific (multi-tier as JSON)
    umsatzbonus_staffeln: str = ""
    # WKZ-specific
    wkz_is_percentage: bool = False
    wkz_percentage: float = 0.0
    wkz_category: str = ""
    notes: str = ""
    invoice_number: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def get_kickback_articles(self) -> List[dict]:
        if not self.kickback_articles:
            return []
        try:
            return json.loads(self.kickback_articles)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_kickback_articles(self, articles: List[dict]):
        self.kickback_articles = json.dumps(articles, ensure_ascii=False) if articles else ""

    def get_umsatzbonus_staffeln(self) -> List[dict]:
        if not self.umsatzbonus_staffeln:
            return []
        try:
            return json.loads(self.umsatzbonus_staffeln)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_umsatzbonus_staffeln(self, staffeln: List[dict]):
        self.umsatzbonus_staffeln = json.dumps(staffeln, ensure_ascii=False) if staffeln else ""

    def is_overdue(self) -> bool:
        if self.status in (EntryStatus.ABGERECHNET, EntryStatus.STORNIERT):
            return False
        if self.billing_deadline and self.billing_deadline < date.today():
            return True
        return False

    def days_until_deadline(self) -> Optional[int]:
        if self.billing_deadline is None:
            return None
        return (self.billing_deadline - date.today()).days
