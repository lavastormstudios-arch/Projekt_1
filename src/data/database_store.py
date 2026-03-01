from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.db_models import (
    Base, EntryModel, SupplierModel, FobEntryModel,
    UserModel, ModuleAccessModel, ActionRightModel,
)
from src.models.base_entry import Entry
from src.models.enums import EntryType, EntryStatus
from src.models.supplier import Supplier
from src.models.fob_entry import FobEntry
from src.utils.constants import DEPARTMENTS, ROLES, MODULES, ACTION_PERMISSIONS
from src.utils.date_helpers import parse_date, format_date, safe_float, safe_int

_DEFAULT_MODULE_ACCESS = {
    "CM":        {"WKZ & Bonus": True,  "Lieferantenmanagement": True,  "FOB-Kalkulation": True},
    "Marketing": {"WKZ & Bonus": False, "Lieferantenmanagement": True,  "FOB-Kalkulation": False},
    "Vertrieb":  {"WKZ & Bonus": True,  "Lieferantenmanagement": True,  "FOB-Kalkulation": False},
    "SCM":       {"WKZ & Bonus": True,  "Lieferantenmanagement": True,  "FOB-Kalkulation": True},
}

_DEFAULT_ACTION_RIGHTS = {
    "Admin":            {"can_edit": True,  "can_delete": True,  "can_invoice": True,  "can_export": True,  "can_import": True,  "is_admin": True},
    "Abteilungsleiter": {"can_edit": True,  "can_delete": True,  "can_invoice": True,  "can_export": True,  "can_import": True,  "is_admin": False},
    "Teamleiter":       {"can_edit": True,  "can_delete": False, "can_invoice": True,  "can_export": True,  "can_import": False, "is_admin": False},
    "Mitarbeiter":      {"can_edit": False, "can_delete": False, "can_invoice": False, "can_export": True,  "can_import": False, "is_admin": False},
}


class DatabaseStore:
    def __init__(self, url: str):
        self.engine = create_engine(url)
        Base.metadata.create_all(self.engine)
        self._migrate_schema()
        self.Session = sessionmaker(bind=self.engine)
        self._seed_defaults_if_empty()
        from src.services.article_service import ArticleService
        ArticleService.load_from_config()

    def _migrate_schema(self):
        """Add columns that were introduced after initial table creation."""
        from sqlalchemy import inspect, text
        inspector = inspect(self.engine)
        with self.engine.connect() as conn:
            fob_cols = {c["name"] for c in inspector.get_columns("fob_entries")}
            if "price_history" not in fob_cols:
                conn.execute(text(
                    "ALTER TABLE fob_entries ADD COLUMN price_history TEXT DEFAULT ''"
                ))
                conn.commit()

    def _seed_defaults_if_empty(self):
        with self.Session() as s:
            if s.query(ModuleAccessModel).count() == 0:
                for dept, mods in _DEFAULT_MODULE_ACCESS.items():
                    for mod, allowed in mods.items():
                        s.add(ModuleAccessModel(department=dept, module=mod, allowed=allowed))
            if s.query(ActionRightModel).count() == 0:
                for role, perms in _DEFAULT_ACTION_RIGHTS.items():
                    for perm, allowed in perms.items():
                        s.add(ActionRightModel(role=role, permission=perm, allowed=allowed))
            s.commit()

    # --- Entries ---

    def load_entries(self) -> List[Entry]:
        with self.Session() as s:
            rows = s.query(EntryModel).all()
            return [self._row_to_entry(r) for r in rows]

    def save_entries(self, entries: List[Entry]):
        with self.Session() as s:
            s.query(EntryModel).delete()
            for e in entries:
                s.add(self._entry_to_row(e))
            s.commit()

    def add_entry(self, entry: Entry):
        with self.Session() as s:
            s.add(self._entry_to_row(entry))
            s.commit()

    def update_entry(self, entry: Entry):
        with self.Session() as s:
            s.merge(self._entry_to_row(entry))
            s.commit()

    def delete_entry(self, entry_id: str):
        with self.Session() as s:
            s.query(EntryModel).filter_by(id=entry_id).delete()
            s.commit()

    # --- Suppliers ---

    def load_suppliers(self) -> List[Supplier]:
        with self.Session() as s:
            rows = s.query(SupplierModel).all()
            return [self._row_to_supplier(r) for r in rows]

    def save_suppliers(self, suppliers: List[Supplier]):
        with self.Session() as s:
            s.query(SupplierModel).delete()
            for sup in suppliers:
                s.add(self._supplier_to_row(sup))
            s.commit()

    def add_supplier(self, supplier: Supplier):
        with self.Session() as s:
            s.add(self._supplier_to_row(supplier))
            s.commit()

    def update_supplier(self, supplier: Supplier):
        with self.Session() as s:
            s.merge(self._supplier_to_row(supplier))
            s.commit()

    def delete_supplier(self, supplier_id: str):
        with self.Session() as s:
            s.query(SupplierModel).filter_by(id=supplier_id).delete()
            s.commit()

    # --- FOB-Kalkulation ---

    def load_fob_entries(self) -> List[FobEntry]:
        with self.Session() as s:
            rows = s.query(FobEntryModel).all()
            return [self._row_to_fob(r) for r in rows]

    def save_fob_entries(self, entries):
        with self.Session() as s:
            s.query(FobEntryModel).delete()
            for e in entries:
                s.add(self._fob_to_row(e))
            s.commit()

    def add_fob_entry(self, entry):
        with self.Session() as s:
            s.add(self._fob_to_row(entry))
            s.commit()

    def update_fob_entry(self, entry):
        with self.Session() as s:
            s.merge(self._fob_to_row(entry))
            s.commit()

    def delete_fob_entry(self, entry_id: str):
        with self.Session() as s:
            s.query(FobEntryModel).filter_by(id=entry_id).delete()
            s.commit()

    # --- Users ---

    def load_users(self) -> list:
        with self.Session() as s:
            rows = s.query(UserModel).all()
            return [
                {
                    "username": r.username,
                    "display_name": r.display_name,
                    "department": r.department,
                    "role": r.role,
                    "active": bool(r.active),
                }
                for r in rows
            ]

    def save_users(self, users: list):
        with self.Session() as s:
            s.query(UserModel).delete()
            for u in users:
                s.add(UserModel(
                    username=u.get("username", ""),
                    display_name=u.get("display_name", ""),
                    department=u.get("department", ""),
                    role=u.get("role", ""),
                    active=bool(u.get("active", True)),
                ))
            s.commit()

    def load_module_access(self) -> dict:
        with self.Session() as s:
            rows = s.query(ModuleAccessModel).all()
            result = {}
            for r in rows:
                if r.department not in result:
                    result[r.department] = {}
                result[r.department][r.module] = bool(r.allowed)
        # Fill missing departments/modules with defaults
        for dept in DEPARTMENTS:
            if dept not in result:
                result[dept] = dict(_DEFAULT_MODULE_ACCESS.get(dept, {m: False for m in MODULES}))
            for mod in MODULES:
                if mod not in result[dept]:
                    result[dept][mod] = _DEFAULT_MODULE_ACCESS.get(dept, {}).get(mod, False)
        return result

    def save_module_access(self, matrix: dict):
        with self.Session() as s:
            s.query(ModuleAccessModel).delete()
            for dept in DEPARTMENTS:
                for mod in MODULES:
                    allowed = bool(matrix.get(dept, {}).get(mod, False))
                    s.add(ModuleAccessModel(department=dept, module=mod, allowed=allowed))
            s.commit()

    def load_action_rights(self) -> dict:
        with self.Session() as s:
            rows = s.query(ActionRightModel).all()
            result = {}
            for r in rows:
                if r.role not in result:
                    result[r.role] = {}
                result[r.role][r.permission] = bool(r.allowed)
        # Fill missing roles/permissions with defaults
        for role in ROLES:
            if role not in result:
                result[role] = dict(_DEFAULT_ACTION_RIGHTS.get(role, {p: False for p in ACTION_PERMISSIONS}))
        return result

    def save_action_rights(self, matrix: dict):
        with self.Session() as s:
            s.query(ActionRightModel).delete()
            for role in ROLES:
                for perm in ACTION_PERMISSIONS:
                    allowed = bool(matrix.get(role, {}).get(perm, False))
                    s.add(ActionRightModel(role=role, permission=perm, allowed=allowed))
            s.commit()

    # --- Mapping helpers ---

    def _entry_to_row(self, e: Entry) -> EntryModel:
        return EntryModel(
            id=e.id,
            entry_type=e.entry_type.value,
            supplier_id=e.supplier_id,
            supplier_name=e.supplier_name,
            description=e.description,
            status=e.status.value,
            amount=e.amount,
            amount_billed=e.amount_billed,
            date_start=format_date(e.date_start),
            date_end=format_date(e.date_end),
            billing_deadline=format_date(e.billing_deadline),
            date_billed=format_date(e.date_billed),
            kickback_articles=e.kickback_articles,
            umsatzbonus_staffeln=e.umsatzbonus_staffeln,
            jaehrlich_wiederholen=e.jaehrlich_wiederholen,
            wkz_is_percentage=e.wkz_is_percentage,
            wkz_percentage=e.wkz_percentage,
            wkz_category=e.wkz_category,
            notes=e.notes,
            created_at=e.created_at,
            invoice_number=e.invoice_number,
        )

    def _row_to_entry(self, r: EntryModel) -> Entry:
        return Entry(
            id=r.id,
            entry_type=EntryType(r.entry_type),
            supplier_id=r.supplier_id or "",
            supplier_name=r.supplier_name or "",
            description=r.description or "",
            status=EntryStatus(r.status),
            amount=safe_float(r.amount),
            amount_billed=safe_float(r.amount_billed),
            date_start=parse_date(r.date_start),
            date_end=parse_date(r.date_end),
            billing_deadline=parse_date(r.billing_deadline),
            date_billed=parse_date(r.date_billed),
            kickback_articles=r.kickback_articles or "",
            umsatzbonus_staffeln=r.umsatzbonus_staffeln or "",
            jaehrlich_wiederholen=bool(r.jaehrlich_wiederholen),
            wkz_is_percentage=bool(r.wkz_is_percentage),
            wkz_percentage=safe_float(r.wkz_percentage),
            wkz_category=r.wkz_category or "",
            notes=r.notes or "",
            created_at=r.created_at or "",
            invoice_number=r.invoice_number or "",
        )

    def _supplier_to_row(self, sup: Supplier) -> SupplierModel:
        return SupplierModel(
            id=sup.id,
            name=sup.name,
            contact_person=sup.contact_person,
            email=sup.email,
            phone=sup.phone,
            notes=sup.notes,
            purchase_volume=sup.purchase_volume,
            country=sup.country,
        )

    def _row_to_supplier(self, r: SupplierModel) -> Supplier:
        return Supplier(
            id=r.id,
            name=r.name or "",
            contact_person=r.contact_person or "",
            email=r.email or "",
            phone=r.phone or "",
            notes=r.notes or "",
            purchase_volume=safe_float(r.purchase_volume),
            country=r.country or "",
        )

    def _fob_to_row(self, e: FobEntry) -> FobEntryModel:
        return FobEntryModel(
            id=e.id,
            artnr=e.artnr,
            bezeichnung=e.bezeichnung,
            lieferant=e.lieferant,
            warengruppe=e.warengruppe,
            cm=e.cm,
            aktuelle_ztn=e.aktuelle_ztn,
            aktueller_ek=e.aktueller_ek,
            geplanter_uvp=e.geplanter_uvp,
            aktionspreis=e.aktionspreis,
            ek_fob_dollar=e.ek_fob_dollar,
            ek_fob_rmb=e.ek_fob_rmb,
            ek_fob_euro=e.ek_fob_euro,
            produktionszeit=e.produktionszeit,
            kubikmeter=e.kubikmeter,
            lcl=e.lcl,
            container_20=e.container_20,
            container_40hc=e.container_40hc,
            zollsatz=e.zollsatz,
            sonder_toolingkosten=e.sonder_toolingkosten,
            archiv=e.archiv,
            price_history=e.price_history,
        )

    def _row_to_fob(self, r: FobEntryModel) -> FobEntry:
        return FobEntry(
            id=r.id,
            artnr=r.artnr or "",
            bezeichnung=r.bezeichnung or "",
            lieferant=r.lieferant or "",
            warengruppe=r.warengruppe or "",
            cm=r.cm or "",
            aktuelle_ztn=r.aktuelle_ztn or "",
            aktueller_ek=safe_float(r.aktueller_ek),
            geplanter_uvp=safe_float(r.geplanter_uvp),
            aktionspreis=safe_float(r.aktionspreis),
            ek_fob_dollar=safe_float(r.ek_fob_dollar),
            ek_fob_rmb=safe_float(r.ek_fob_rmb),
            ek_fob_euro=safe_float(r.ek_fob_euro),
            produktionszeit=safe_int(r.produktionszeit),
            kubikmeter=safe_float(r.kubikmeter),
            lcl=bool(r.lcl),
            container_20=safe_int(r.container_20),
            container_40hc=safe_int(r.container_40hc),
            zollsatz=safe_float(r.zollsatz),
            sonder_toolingkosten=safe_float(r.sonder_toolingkosten),
            archiv=bool(r.archiv),
            price_history=r.price_history or "",
        )
