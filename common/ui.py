# common/ui.py
from __future__ import annotations
import streamlit as st
from typing import Any

# --- Init session ---
def init_session(default_route: str = "home") -> None:
    if "route" not in st.session_state:
        st.session_state["route"] = default_route
    if "params" not in st.session_state:
        st.session_state["params"] = {}

# --- Navigation ---
def go(route: str, **params: Any) -> None:
    st.session_state["route"] = route
    if params:
        st.session_state["params"] = params
    safe_rerun()

def get_param(name: str, default: Any = None) -> Any:
    return st.session_state.get("params", {}).get(name, default)

def safe_rerun() -> None:
    try:
        st.rerun()
    except RuntimeError:
        pass

# --- Keys ---
def ns(*parts: Any) -> str:
    """Readable unique widget key."""
    return ":".join(str(p) for p in parts)
