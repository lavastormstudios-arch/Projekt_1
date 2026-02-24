from dataclasses import dataclass, field


@dataclass
class User:
    username: str
    display_name: str = ""
    department: str = ""
    role: str = ""
    active: bool = True


@dataclass
class Permissions:
    # Module access (from department)
    can_view_wkz_bonus: bool = False
    can_view_lieferanten: bool = False
    # Action rights (from role)
    can_edit: bool = False
    can_delete: bool = False
    can_invoice: bool = False
    can_export: bool = False
    can_import: bool = False
    is_admin: bool = False
