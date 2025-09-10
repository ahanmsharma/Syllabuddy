import streamlit as st
from common.ui import topbar, go
from selection.widgets import subject_cards, module_cards, iq_cards, dotpoint_cards

def page_srs_menu():
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

def page_srs_subjects():
    subject_cards(key_prefix="srs", back_to="srs_menu")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("srs_review")

def page_srs_modules():
    s = st.session_state.get("focus_subject")
    if not s: go("srs_subjects"); return
    module_cards(s, key_prefix="srs", back_to="srs_subjects")

def page_srs_iqs():
    sm = st.session_state.get("focus_module")
    if not sm: go("srs_modules"); return
    s, m = sm
    iq_cards(s, m, key_prefix="srs", back_to="srs_modules")

def page_srs_dotpoints():
    smi = st.session_state.get("focus_iq")
    if not smi: go("srs_iqs"); return
    s, m, iq = smi
    dotpoint_cards(s, m, iq, key_prefix="srs", back_to="srs_iqs")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("srs_review")
