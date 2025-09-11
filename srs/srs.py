import streamlit as st
from common.ui import topbar, get_go
from selection.widgets import (
    page_srs_subjects,
    page_srs_modules,
    page_srs_iqs,
    page_srs_dotpoints,
)

def page_srs_menu():
    go = get_go()
    topbar("Spaced Repetition", back_to="home")
    due_count = max(1, len(st.session_state["sel_dotpoints"]))
    st.write(f"**All (Today):** {due_count} dotpoints due")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Start: All (SR order)", use_container_width=True, type="primary"):
            st.info("SRS Engine (All) — placeholder for now.")
    with c2:
        if st.button("Choose Subject (SR)", use_container_width=True):
            st.session_state["cram_mode"] = False
            go("srs_subjects")
    with c3:
        if st.button("Cram Mode (mass select)", use_container_width=True):
            st.session_state["cram_mode"] = True
            st.session_state["prioritization_mode"] = False
            go("cram_subjects")
