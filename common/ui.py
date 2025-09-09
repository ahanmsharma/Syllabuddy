import streamlit as st
from typing import Optional

def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()  # type: ignore[attr-defined]
    else:
        st.session_state["_force_rerun_tick"] = st.session_state.get("_force_rerun_tick", 0) + 1

def set_go(go_fn):
    st.session_state["_go"] = go_fn

def go(route: str):
    st.session_state["route"] = route
    safe_rerun()

def topbar(title: str, back_to: Optional[str] = None):
    c1, c2 = st.columns([1,6], vertical_alignment="center")
    with c1:
        if back_to:
            b1, b2 = st.columns([1,3])
            with b1:
                if st.button("⬅", key=f"arrow_{title}"):
                    go(back_to)
            with b2:
                if st.button("Back", key=f"back_{title}", use_container_width=True):
                    go(back_to)
    with c2:
        st.title(title)
