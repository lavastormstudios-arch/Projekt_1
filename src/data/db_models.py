from sqlalchemy import Column, String, Float, Boolean, Text, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EntryModel(Base):
    __tablename__ = "entries"

    id = Column(String, primary_key=True)
    entry_type = Column(String, default="WKZ")
    supplier_id = Column(String, default="")
    supplier_name = Column(String, default="")
    description = Column(String, default="")
    status = Column(String, default="Offen")
    amount = Column(Float, default=0.0)
    amount_billed = Column(Float, default=0.0)
    date_start = Column(String, nullable=True)
    date_end = Column(String, nullable=True)
    billing_deadline = Column(String, nullable=True)
    date_billed = Column(String, nullable=True)
    kickback_articles = Column(Text, default="")
    umsatzbonus_staffeln = Column(Text, default="")
    jaehrlich_wiederholen = Column(Boolean, default=False)
    wkz_is_percentage = Column(Boolean, default=False)
    wkz_percentage = Column(Float, default=0.0)
    wkz_category = Column(String, default="")
    notes = Column(Text, default="")
    created_at = Column(String, default="")
    invoice_number = Column(String, default="")


class SupplierModel(Base):
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True)
    name = Column(String, default="")
    contact_person = Column(String, default="")
    email = Column(String, default="")
    phone = Column(String, default="")
    notes = Column(Text, default="")
    purchase_volume = Column(Float, default=0.0)
    country = Column(String, default="")


class FobEntryModel(Base):
    __tablename__ = "fob_entries"

    id = Column(String, primary_key=True)
    artnr = Column(String, default="")
    bezeichnung = Column(String, default="")
    lieferant = Column(String, default="")
    warengruppe = Column(String, default="")
    cm = Column(String, default="")
    aktuelle_ztn = Column(String, default="")
    aktueller_ek = Column(Float, default=0.0)
    geplanter_uvp = Column(Float, default=0.0)
    aktionspreis = Column(Float, default=0.0)
    ek_fob_dollar = Column(Float, default=0.0)
    ek_fob_rmb = Column(Float, default=0.0)
    ek_fob_euro = Column(Float, default=0.0)
    produktionszeit = Column(Integer, default=0)
    kubikmeter = Column(Float, default=0.0)
    lcl = Column(Boolean, default=False)
    container_20 = Column(Integer, default=0)
    container_40hc = Column(Integer, default=0)
    zollsatz = Column(Float, default=0.0)
    sonder_toolingkosten = Column(Float, default=0.0)
    archiv = Column(Boolean, default=False)
    price_history = Column(Text, default="")


class UserModel(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True)
    display_name = Column(String, default="")
    department = Column(String, default="")
    role = Column(String, default="")
    active = Column(Boolean, default=True)


class ModuleAccessModel(Base):
    __tablename__ = "module_access"

    department = Column(String, primary_key=True)
    module = Column(String, primary_key=True)
    allowed = Column(Boolean, default=False)


class ActionRightModel(Base):
    __tablename__ = "action_rights"

    role = Column(String, primary_key=True)
    permission = Column(String, primary_key=True)
    allowed = Column(Boolean, default=False)
