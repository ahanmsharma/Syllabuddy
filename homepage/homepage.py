import streamlit as st
from common.ui import get_go

def page_home():
    go = get_go()
    st.title("Syllabuddy")
    st.write("Stay on track with spaced repetition, prioritised cramming, and targeted practice.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Spaced Repetition", use_container_width=True):
            go("srs_menu")
    with c2:
        if st.button("Select Subject", use_container_width=True):
            go("select_subject_main")

def page_select_subject_main():
    go = get_go()
    from common.ui import topbar
    topbar("Select Subject", back_to="home")
    st.write("Choose subjects/modules/IQs/dotpoints or try AI-based selection.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Manual selection", use_container_width=True, type="primary"):
            st.session_state["cram_mode"] = True
            st.session_state["prioritization_mode"] = False
            go("cram_subjects")
    with c2:
        if st.button("AI selection (enter weaknesses)", use_container_width=True):
            go("ai_select")
