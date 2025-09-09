import streamlit as st
from typing import Optional

def set_go(go_fn):
    st.session_state["_go"] = go_fn

def go(route: str):
    st.session_state["_go"](route)

def topbar(title: str, back_to: Optional[str] = None):
    go = st.session_state["_go"]
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
