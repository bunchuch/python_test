"""Role-Based Access Control — permission matrix and session helpers."""

# ── Permission map ─────────────────────────────────────────────────────────────
# Each key names a discrete action/resource; value is the set of roles that may
# perform it.  All checks go through has_perm() so the matrix is the single
# source of truth.
PERMISSIONS: dict[str, frozenset] = {
    # Page access
    "access_processor": frozenset({"admin", "dev"}),
    "access_guide":     frozenset({"admin", "dev"}),
    "access_database":  frozenset({"admin", "dev"}),
    "access_query":     frozenset({"user", "admin", "dev"}),
    # Actions
    "import_files":     frozenset({"admin", "dev"}),
    "execute_query":    frozenset({"user", "admin", "dev"}),
    "download_data":    frozenset({"user", "admin", "dev"}),
    "export_data":      frozenset({"user", "admin", "dev"}),
    "remove_data":      frozenset({"admin", "dev"}),   # "replace" mode in save
    "manage_users":     frozenset({"admin", "dev"}),
    "view_logs":        frozenset({"dev"}),
}

# ── Navigation pages per role ─────────────────────────────────────────────────
# Tuple: (page_key, display_label, material_icon)
NAV_PAGES: dict[str, list] = {
    "user": [
        ("query", "Query", ":material/search:"),
    ],
    "admin": [
        ("processor", "Processor", ":material/flight:"),
        ("query",     "Query",     ":material/search:"),
        ("guide",     "Guide",     ":material/menu_book:"),
        ("database",  "Database",  ":material/storage:"),
    ],
    "dev": [
        ("processor", "Processor", ":material/flight:"),
        ("query",     "Query",     ":material/search:"),
        ("guide",     "Guide",     ":material/menu_book:"),
        ("database",  "Database",  ":material/storage:"),
    ],
}

# ── Role display metadata ─────────────────────────────────────────────────────
# (display_label, badge_background_colour)
ROLE_BADGE: dict[str, tuple] = {
    "user":  ("User",  "#2E86C1"),
    "admin": ("Admin", "#1a7a44"),
    "dev":   ("Dev",   "#7d3c98"),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def current_role() -> str:
    import streamlit as st
    return st.session_state.get("_role", "user")


def has_perm(permission: str, role: str | None = None) -> bool:
    r = role or current_role()
    return r in PERMISSIONS.get(permission, frozenset())


def allowed_nav(role: str | None = None) -> list:
    """Return the list of (key, label, icon) tuples the role may see."""
    r = role or current_role()
    return NAV_PAGES.get(r, NAV_PAGES["user"])


def default_page(role: str | None = None) -> str:
    """First page key available to the role (fallback destination)."""
    return allowed_nav(role)[0][0]
