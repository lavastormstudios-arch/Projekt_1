import os

from src.models.user import User, Permissions
from src.utils.constants import USERS_FILE, DEPARTMENTS, ROLES, MODULES, ACTION_PERMISSIONS


class AuthService:
    def __init__(self, store):
        self._store = store

    # ------------------------------------------------------------------
    # Windows identity
    # ------------------------------------------------------------------

    def get_windows_username(self) -> str:
        return os.environ.get("USERNAME", "").strip()

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def needs_bootstrap(self) -> bool:
        """True when users.xlsx doesn't exist yet (no users configured)."""
        return not os.path.exists(USERS_FILE)

    def bootstrap_first_admin(self, username: str, display_name: str = ""):
        """Create the first admin user and write default permission tables."""
        # Ensure the file (with default sheets) is created first
        self._store._ensure_users_file()
        # Only add if not already present
        existing = [u["username"].lower() for u in self._store.load_users()]
        if username.lower() in existing:
            return
        user = {
            "username": username.lower(),
            "display_name": display_name or username,
            "department": "CM",
            "role": "Admin",
            "active": True,
        }
        users = self._store.load_users()
        users.append(user)
        self._store.save_users(users)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> "User | None":
        """Look up the current Windows user in users.xlsx."""
        win_user = self.get_windows_username().lower()
        try:
            users = self._store.load_users()
        except Exception:
            return None
        for u in users:
            if u.get("username", "").lower() == win_user and u.get("active", True):
                return User(
                    username=u["username"],
                    display_name=u.get("display_name", ""),
                    department=u.get("department", ""),
                    role=u.get("role", ""),
                    active=bool(u.get("active", True)),
                )
        return None

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def get_permissions(self, user: User) -> Permissions:
        try:
            module_access = self._store.load_module_access()
            action_rights = self._store.load_action_rights()
        except Exception:
            return Permissions()

        dept_access = module_access.get(user.department, {})
        role_rights = action_rights.get(user.role, {})

        return Permissions(
            can_view_wkz_bonus=bool(dept_access.get("WKZ & Bonus", False)),
            can_view_lieferanten=bool(dept_access.get("Lieferantenmanagement", False)),
            can_view_fob_kalkulation=bool(dept_access.get("FOB-Kalkulation", False)),
            can_edit=bool(role_rights.get("can_edit", False)),
            can_delete=bool(role_rights.get("can_delete", False)),
            can_invoice=bool(role_rights.get("can_invoice", False)),
            can_export=bool(role_rights.get("can_export", False)),
            can_import=bool(role_rights.get("can_import", False)),
            is_admin=bool(role_rights.get("is_admin", False)),
        )

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------

    def get_all_users(self) -> list[User]:
        users = self._store.load_users()
        return [
            User(
                username=u["username"],
                display_name=u.get("display_name", ""),
                department=u.get("department", ""),
                role=u.get("role", ""),
                active=bool(u.get("active", True)),
            )
            for u in users
        ]

    def add_user(self, user: User):
        users = self._store.load_users()
        users.append({
            "username": user.username.lower(),
            "display_name": user.display_name,
            "department": user.department,
            "role": user.role,
            "active": user.active,
        })
        self._store.save_users(users)

    def update_user(self, user: User):
        users = self._store.load_users()
        for u in users:
            if u["username"].lower() == user.username.lower():
                u["display_name"] = user.display_name
                u["department"] = user.department
                u["role"] = user.role
                u["active"] = user.active
                break
        self._store.save_users(users)

    def delete_user(self, username: str):
        users = [u for u in self._store.load_users()
                 if u["username"].lower() != username.lower()]
        self._store.save_users(users)

    # ------------------------------------------------------------------
    # Module access
    # ------------------------------------------------------------------

    def get_module_access(self) -> dict:
        return self._store.load_module_access()

    def set_module_access(self, dept: str, module: str, value: bool):
        matrix = self._store.load_module_access()
        if dept not in matrix:
            matrix[dept] = {}
        matrix[dept][module] = value
        self._store.save_module_access(matrix)

    # ------------------------------------------------------------------
    # Action rights
    # ------------------------------------------------------------------

    def get_action_rights(self) -> dict:
        return self._store.load_action_rights()

    def set_action_rights(self, role: str, perm: str, value: bool):
        matrix = self._store.load_action_rights()
        if role not in matrix:
            matrix[role] = {}
        matrix[role][perm] = value
        self._store.save_action_rights(matrix)
