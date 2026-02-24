import configparser
import json
import os
import re
import tempfile
from datetime import date, datetime
from typing import Optional

INVOICE_POOL_FILE = os.path.join("data", "invoice_pool.json")

DE_NAMES = {"deutschland", "germany", "de", "d"}


def _is_german(supplier) -> bool:
    country = (getattr(supplier, "country", "") or "").strip().lower()
    return country in DE_NAMES


class InvoiceService:
    TEMPLATE_BONUS   = os.path.join("data", "templates", "invoice_bonus.docx")
    # Legacy templates kept as fallback (may not exist)
    TEMPLATE_STANDARD = os.path.join("data", "templates", "invoice_standard.docx")
    TEMPLATE_KICKBACK = os.path.join("data", "templates", "invoice_kickback.docx")
    OUTPUT_DIR = os.path.join("data", "invoices")
    CONFIG_PATH = "config.ini"

    # ------------------------------------------------------------------
    # Helper: extract SAP address fields from supplier.notes
    # Notes are stored during CSV import as:
    #   "Lief.-Nr.: DLIFNR\nNAME2\nNAME3\nSTRAS, PLOR, ORTNA"
    # ------------------------------------------------------------------
    def _parse_supplier_notes(self, notes: str) -> dict:
        result = {"DLIFNR": "", "NAME2": "", "NAME3": "", "STRAS": "", "PLOR": "", "ORTNA": ""}
        if not notes:
            return result

        lines = [ln.strip() for ln in notes.splitlines() if ln.strip()]
        remaining = []

        for line in lines:
            if line.startswith("Lief.-Nr.:"):
                result["DLIFNR"] = line[len("Lief.-Nr.:"):].strip()
            else:
                remaining.append(line)

        # Detect address line (last line with at least one comma → STRAS, PLOR, ORTNA)
        addr_idx = None
        for i in range(len(remaining) - 1, -1, -1):
            if "," in remaining[i]:
                addr_idx = i
                break

        name_lines = [remaining[i] for i in range(len(remaining)) if i != addr_idx]

        if len(name_lines) >= 1:
            result["NAME2"] = name_lines[0]
        if len(name_lines) >= 2:
            result["NAME3"] = name_lines[1]

        if addr_idx is not None:
            parts = [p.strip() for p in remaining[addr_idx].split(",", 2)]
            result["STRAS"] = parts[0] if len(parts) > 0 else ""
            result["PLOR"]  = parts[1] if len(parts) > 1 else ""
            result["ORTNA"] = parts[2] if len(parts) > 2 else ""

        return result

    def _load_pool(self) -> dict:
        if not os.path.exists(INVOICE_POOL_FILE):
            return {"available": [], "used": []}
        with open(INVOICE_POOL_FILE, encoding="utf-8") as f:
            return json.load(f)

    def _save_pool(self, pool: dict):
        with open(INVOICE_POOL_FILE, "w", encoding="utf-8") as f:
            json.dump(pool, f, ensure_ascii=False, indent=2)

    def available_count(self) -> int:
        return len(self._load_pool()["available"])

    def has_available_numbers(self, count: int = 1) -> bool:
        return self.available_count() >= count

    def add_invoice_numbers(self, numbers: list) -> int:
        """Fügt neue Nummern zum Pool hinzu. Gibt Anzahl tatsächlich hinzugefügter zurück."""
        pool = self._load_pool()
        existing = {n for n in pool["available"]} | {u["number"] for u in pool["used"]}
        new_nums = [n.strip() for n in numbers if n.strip() and n.strip() not in existing]
        pool["available"].extend(new_nums)
        self._save_pool(pool)
        return len(new_nums)

    def get_next_invoice_number(self) -> str:
        pool = self._load_pool()
        if not pool["available"]:
            raise ValueError(
                "Keine Rechnungsnummern mehr verfügbar.\n"
                "Bitte neue Nummern bei der Buchhaltung anfordern\n"
                "und im Admin-Bereich unter 'Rechnungsnummern' hinterlegen."
            )
        number = pool["available"].pop(0)
        pool["used"].append({"number": number, "used_at": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self._save_pool(pool)
        return number

    def build_context(self, entry, supplier, qty_map: Optional[dict] = None,
                      achieved_revenue: Optional[float] = None,
                      storno_net: Optional[float] = None,
                      orig_invoice_number: str = "",
                      override_amount: Optional[float] = None,
                      override_purchase_volume: Optional[float] = None) -> dict:
        from src.models.enums import EntryType

        tax_rate = 19 if _is_german(supplier) else 0

        # Storno reuses the original invoice number; new invoices get a fresh number
        if storno_net is not None:
            invoice_number = orig_invoice_number
        else:
            invoice_number = self.get_next_invoice_number()
        today = date.today()
        invoice_date = today.strftime("%d.%m.%Y")
        period_start = entry.date_start.strftime("%d.%m.%Y") if entry.date_start else ""
        period_end = entry.date_end.strftime("%d.%m.%Y") if entry.date_end else ""
        year = entry.date_start.year if entry.date_start else today.year

        # SAP-style address fields from supplier.notes
        addr = self._parse_supplier_notes(getattr(supplier, "notes", "") or "")

        ctx: dict = {
            # ── legacy keys (kept for backward compat with old templates) ──
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "supplier_name": supplier.name,
            "supplier_contact": supplier.contact_person or "",
            "entry_type": entry.entry_type.value,
            "description": entry.description,
            "period_start": period_start,
            "period_end": period_end,
            "notes": entry.notes or "",
            "tax_rate": tax_rate,
            # ── SAP / Vorlage Bonus keys ──────────────────────────────────
            "NAME1":  supplier.name,
            "NAME2":  addr["NAME2"],
            "NAME3":  addr["NAME3"],
            "STRAS":  addr["STRAS"],
            "PLOR":   addr["PLOR"],
            "ORTNA":  addr["ORTNA"],
            "LANDKZ": getattr(supplier, "country", "") or "",
            "DLIFNR": addr["DLIFNR"],
            "RENR":   invoice_number,
            "AKTDAT": invoice_date,
            "ARTBON": entry.entry_type.value,
            "JAHR":   str(year),
        }

        # ── Net amount determination ──────────────────────────────────────
        if storno_net is not None:
            net = round(storno_net, 2)
            is_storno = True
            ctx["line_description"] = entry.description
        elif override_amount is not None:
            net = round(override_amount, 2)
            is_storno = False
            ctx["line_description"] = entry.description
        elif override_purchase_volume is not None:
            net = round(override_purchase_volume * entry.wkz_percentage / 100, 2)
            is_storno = False
            ctx["base_amount"] = f"{override_purchase_volume:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            ctx["percentage"] = f"{entry.wkz_percentage:.2f}"
            ctx["line_description"] = f"WKZ {entry.wkz_percentage:.2f}% auf Einkaufsumsatz"
        elif entry.entry_type == EntryType.KICKBACK:
            articles = entry.get_kickback_articles()
            items = []
            net = 0.0
            for art in articles:
                art_nr = art.get("article_number", "")
                rate = float(art.get("kickback_amount", 0))
                qty = float(qty_map.get(art_nr, 0)) if qty_map else 0.0
                line_amount = round(qty * rate, 2)
                net += line_amount
                items.append({
                    "article_number": art_nr,
                    "qty": f"{qty:g}",
                    "rate": f"{rate:.2f}",
                    "line_amount": f"{line_amount:.2f}",
                })
            net = round(net, 2)
            is_storno = False
            ctx["items"] = items
            ctx["line_description"] = entry.description

        elif entry.entry_type == EntryType.WKZ:
            if entry.wkz_is_percentage:
                net = round(supplier.purchase_volume * entry.wkz_percentage / 100, 2)
                ctx["base_amount"] = f"{supplier.purchase_volume:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ctx["percentage"] = f"{entry.wkz_percentage:.2f}"
                ctx["line_description"] = f"WKZ {entry.wkz_percentage:.2f}% auf Einkaufsumsatz"
            else:
                net = round(entry.amount, 2)
                ctx["line_description"] = entry.description
            is_storno = False

        elif entry.entry_type == EntryType.UMSATZBONUS:
            staffeln = entry.get_umsatzbonus_staffeln()
            rev = float(achieved_revenue) if achieved_revenue is not None else 0.0
            matching_tier = None
            for tier in sorted(staffeln, key=lambda t: float(t.get("revenue_threshold", 0)), reverse=True):
                if rev >= float(tier.get("revenue_threshold", 0)):
                    matching_tier = tier
                    break
            if matching_tier:
                pct = float(matching_tier.get("bonus_percentage", 0))
                net = round(rev * pct / 100, 2)
                ctx["achieved_revenue"] = f"{rev:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ctx["bonus_tier"] = f"{float(matching_tier.get('revenue_threshold', 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ctx["bonus_percentage"] = f"{pct:.2f}"
                ctx["line_description"] = f"Umsatzbonus {pct:.2f}% auf {rev:,.2f} €"
            else:
                net = 0.0
                ctx["achieved_revenue"] = f"{rev:.2f}"
                ctx["bonus_tier"] = "–"
                ctx["bonus_percentage"] = "0"
                ctx["line_description"] = entry.description
            is_storno = False
        else:
            net = round(entry.amount, 2)
            is_storno = False
            ctx["line_description"] = entry.description

        # ── Storno / normal prefix & reference ───────────────────────────
        if entry.entry_type in (EntryType.WKZ, EntryType.KICKBACK):
            ctx["BELAST_PREFIX"] = "Storno Werbekosten-Rechnung" if is_storno else "Werbekosten-Rechnung"
            ctx["ARTBON"] = ""  # Typ-Bezeichnung nicht doppelt anzeigen
        else:
            ctx["BELAST_PREFIX"] = "Storno Belastungsanzeige " if is_storno else "Belastungsanzeige "
        ctx["ORIG_RENR"] = ""   # same RENR used → no separate reference line needed
        ctx["is_storno"] = is_storno
        ctx["net_raw"] = net

        # ── Amounts (negated for storno) ──────────────────────────────────
        sign = -1 if is_storno else 1
        tax_amount = round(net * tax_rate / 100, 2)
        total = round(net + tax_amount, 2)

        def fmt(v: float) -> str:
            return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        ctx["net_amount"] = fmt(sign * net)
        ctx["tax_amount"] = fmt(sign * tax_amount)
        ctx["total_amount"] = fmt(sign * total)

        # SAP financial keys (Vorlage Bonus)
        ctx["NETSUM"] = fmt(sign * net)
        ctx["MWST"]   = fmt(sign * tax_amount)
        ctx["GESBET"] = fmt(sign * total)

        # Ensure optional template keys are always present so Jinja2 conditionals evaluate cleanly
        ctx.setdefault("base_amount", "")
        ctx.setdefault("percentage", "")
        ctx.setdefault("achieved_revenue", "")
        ctx.setdefault("bonus_tier", "")
        ctx.setdefault("bonus_percentage", "")
        ctx.setdefault("line_description", "")

        return ctx

    def generate(self, entry, supplier, context: dict) -> str:
        from src.models.enums import EntryType

        try:
            from docxtpl import DocxTemplate
        except ImportError:
            raise RuntimeError(
                "Das Paket 'docxtpl' ist nicht installiert.\n"
                "Bitte führen Sie aus: pip install docxtpl"
            )

        try:
            from docx2pdf import convert as docx2pdf_convert
        except ImportError:
            raise RuntimeError(
                "Das Paket 'docx2pdf' ist nicht installiert.\n"
                "Bitte führen Sie aus: pip install docx2pdf"
            )

        # Use the unified Bonus template; fall back to legacy templates if it doesn't exist yet
        if os.path.exists(self.TEMPLATE_BONUS):
            template_path = self.TEMPLATE_BONUS
        elif entry.entry_type == EntryType.KICKBACK:
            template_path = self.TEMPLATE_KICKBACK
        else:
            template_path = self.TEMPLATE_STANDARD

        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"Word-Vorlage nicht gefunden: {template_path}\n\n"
                "Bitte erstellen Sie die Vorlage und legen Sie sie unter\n"
                f"'{os.path.abspath(self.TEMPLATE_BONUS)}' ab."
            )

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        inv_num = context.get("invoice_number", "RE-0000")
        safe_num = inv_num.replace("/", "-").replace("\\", "-")
        if context.get("is_storno"):
            safe_num = f"{safe_num}-Storno"

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_docx = os.path.join(tmp_dir, f"{safe_num}.docx")
            tpl = DocxTemplate(template_path)
            tpl.render(context)
            tpl.save(tmp_docx)

            output_pdf = os.path.join(self.OUTPUT_DIR, f"{safe_num}.pdf")
            docx2pdf_convert(tmp_docx, output_pdf)

        return output_pdf
