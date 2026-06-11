"""
Thin wrapper around the local_storage Streamlit component.

The component is served by the Streamlit server on the same origin as the main
app, so its localStorage is shared with the browser page.

Return value on first render is always None (component not yet ready).
On the next Streamlit rerun (triggered automatically when the value changes)
the actual localStorage value is returned.
"""

import os
import streamlit.components.v1 as _components

_path = os.path.join(os.path.dirname(__file__), "..", "components", "local_storage")
_component = _components.declare_component("local_storage_component", path=_path)


def ls_get(key: str):
    """Return the localStorage value for *key*, or None while loading, or '' if absent."""
    return _component(action="get", ls_key=key, ls_val="", key=f"_ls_get_{key}", default=None)


def ls_set(key: str, value: str) -> None:
    """Write *value* to localStorage under *key*."""
    _component(action="set", ls_key=key, ls_val=value, key=f"_ls_set_{key}", default=None)


def ls_del(key: str) -> None:
    """Remove *key* from localStorage."""
    _component(action="del", ls_key=key, ls_val="", key=f"_ls_del_{key}", default=None)
