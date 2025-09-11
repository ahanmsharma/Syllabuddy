"""Shared UI helpers for Streamlit pages.

This module consolidates small utilities used across the Streamlit pages.
It also offers helpers for generating stable keys for widgets so that
state can be reliably stored between reruns.
"""

import hashlib
from typing import Iterable

import streamlit as st

# ------------------------------
# Central rerun + navigation
# ------------------------------

def safe_rerun():
    """
    Wrapper around st.rerun for compatibility with older/newer Streamlit versions.
    """
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        raise RuntimeError("No rerun method available in this Streamlit version.")

def set_go(go=None):
    """
    Inject a 'go' function into ``st.session_state`` for navigation.

    If ``go`` is ``None`` a default implementation is created which sets the
    ``route`` entry in ``session_state`` and triggers a rerun.  The function
    stored in ``session_state['_go']`` is returned.
    """
    if go is None:
        def go(route: str):
            st.session_state["route"] = route
            safe_rerun()

    # Put it in session_state for global access
    st.session_state["_go"] = go
    return go

def get_go():
    """Helper to retrieve the navigation function from session state."""
    return st.session_state.get("_go")

# ------------------------------
# UI helpers
# ------------------------------

def topbar(title: str, back_to: str = None):
    """Simple top bar with an optional back button."""
    c1, c2 = st.columns([1, 6], vertical_alignment="center")
    with c1:
        if back_to:
            if st.button("⬅ Back", key=f"back_{title}"):
                st.session_state["_go"](back_to)
    with c2:
        st.title(title)

# ---------- key helpers (stable keys for widgets) ----------

def stable_key_tuple(items: Iterable[str]) -> str:
    """Return a deterministic key for a sequence of strings.

    The built-in :func:`hash` is randomised between interpreter sessions, so
    for stable widget keys we derive a short SHA-256 digest of the joined
    strings.  The digest is truncated to keep keys compact.
    """
    joined = "\x1f".join(str(it) for it in items)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]

def k_subject_open(subject: str, prefix: str) -> str:
    return f"{prefix}_subject_open_{subject}"

def k_subject_toggle(subject: str, prefix: str) -> str:
    return f"{prefix}_subject_toggle_{subject}"

def k_module_open(subject: str, module: str, prefix: str) -> str:
    return f"{prefix}_module_open_{subject}_{module}"

def k_module_toggle(subject: str, module: str, prefix: str) -> str:
    return f"{prefix}_module_toggle_{subject}_{module}"

def k_iq_open(subject: str, module: str, iq: str, prefix: str) -> str:
    return f"{prefix}_iq_open_{subject}_{module}_{iq}"

def k_iq_toggle(subject: str, module: str, iq: str, prefix: str) -> str:
    return f"{prefix}_iq_toggle_{subject}_{module}_{iq}"

def k_dp_toggle(subject: str, module: str, iq: str, dp: str, prefix: str) -> str:
    return f"{prefix}_dp_toggle_{subject}_{module}_{iq}_{dp}"
