import csv
import os
from typing import List, Optional

from src.models.supplier import Supplier
from src.data.excel_store import ExcelStore


class SupplierService:
    def __init__(self, store: ExcelStore):
        self.store = store

    def get_all(self) -> List[Supplier]:
        return self.store.load_suppliers()

    def get_by_id(self, supplier_id: str) -> Optional[Supplier]:
        for s in self.store.load_suppliers():
            if s.id == supplier_id:
                return s
        return None

    def add(self, supplier: Supplier):
        self.store.add_supplier(supplier)

    def update(self, supplier: Supplier):
        self.store.update_supplier(supplier)

    def delete(self, supplier_id: str):
        self.store.delete_supplier(supplier_id)

    def get_names(self) -> List[str]:
        return [s.name for s in self.get_all()]

    def get_by_name(self, name: str) -> Optional[Supplier]:
        for s in self.get_all():
            if s.name == name:
                return s
        return None

    def import_from_csv(self, path: str) -> str:
        if not os.path.exists(path):
            return f"CSV-Datei nicht gefunden: {path}"

        rows = []
        field_map = {}
        last_error = ""

        _DETECT_COLS = {"name1", "name", "einkaufsumsatz", "dlifnr", "landkz"}
        _ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1")
        _DELIMITERS = (";", "\t", ",")

        found = False
        for encoding in _ENCODINGS:
            if found:
                break
            for delimiter in _DELIMITERS:
                try:
                    with open(path, "r", encoding=encoding) as f:
                        reader = csv.DictReader(f, delimiter=delimiter)
                        fieldnames = reader.fieldnames or []
                        lower_fields = {fn.strip().lower() for fn in fieldnames}
                        if lower_fields & _DETECT_COLS:
                            rows = list(reader)
                            field_map = {fn.strip().lower(): fn for fn in fieldnames}
                            found = True
                            break
                except Exception as e:
                    last_error = str(e)
                    continue

        if not rows:
            detail = f" ({last_error})" if last_error else ""
            return f"CSV konnte nicht gelesen werden. Erwartete Spalten: NAME1, LANDKZ, ...{detail}"

        # ── Column resolution (SAP format takes priority) ──────────────
        def col(key):
            """Return the original fieldname for a lower-case key, or None."""
            return field_map.get(key.lower())

        name1_key   = col("NAME1") or col("name")
        name2_key   = col("NAME2")
        name3_key   = col("NAME3")
        country_key = col("LANDKZ") or col("land") or col("country")
        dlifnr_key  = col("DLIFNR")
        stras_key   = col("STRAS")
        plor_key    = col("PLOR")
        ortna_key   = col("ORTNA")

        if not name1_key:
            return "Spalte 'NAME1' (oder 'Name') nicht in der CSV gefunden."

        suppliers = self.get_all()
        supplier_by_name = {s.name.strip().lower(): s for s in suppliers}

        updated = 0
        created = 0

        for row in rows:
            def cell(key):
                return (row.get(key) or "").strip() if key else ""

            # NAME1 is the canonical name used for both display and matching
            name = cell(name1_key)
            if not name:
                continue

            country = cell(country_key)

            # Build notes: Lief.-Nr., NAME2/NAME3 extras, address
            note_parts = []
            if dlifnr_key and cell(dlifnr_key):
                note_parts.append(f"Lief.-Nr.: {cell(dlifnr_key)}")
            for extra_key in (name2_key, name3_key):
                val = cell(extra_key)
                if val:
                    note_parts.append(val)
            address_parts = [cell(k) for k in (stras_key, plor_key, ortna_key) if k]
            address = ", ".join(p for p in address_parts if p)
            if address:
                note_parts.append(address)
            notes = "\n".join(note_parts)

            match_key = name.lower()
            existing = supplier_by_name.get(match_key)
            if existing:
                if country:
                    existing.country = country
                if notes and not existing.notes:
                    existing.notes = notes
                self.store.update_supplier(existing)
                updated += 1
            else:
                new_supplier = Supplier(name=name, country=country, notes=notes)
                self.store.add_supplier(new_supplier)
                supplier_by_name[match_key] = new_supplier
                created += 1

        return f"CSV-Import: {created} neue Lieferanten, {updated} aktualisiert."
