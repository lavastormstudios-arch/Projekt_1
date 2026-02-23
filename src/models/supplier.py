from dataclasses import dataclass, field
import uuid


@dataclass
class Supplier:
    name: str
    contact_person: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""
    purchase_volume: float = 0.0
    country: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
