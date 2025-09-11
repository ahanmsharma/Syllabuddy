import streamlit as st
from common.ui import topbar, get_go
from selection.widgets import (
    page_cram_subjects,
    page_cram_modules,
    page_cram_iqs,
    page_cram_dotpoints,
)

def page_cram_how():
    go = get_go()
    topbar("How to review", back_to="cram_review")
    mode = st.radio("Choose order:", ["SR order (spaced repetition)", "Prioritization (based on strengths/weaknesses)"])
    if mode.startswith("Prioritization"):
        st.subheader("Tell the AI")
        st.session_state["ai_weakness_text"] = st.text_area(
            "What topics are you struggling with most?",
            height=120, placeholder="e.g., diffusion vs osmosis; rates; energy changes"
        )
        st.session_state["ai_strength_text"] = st.text_area(
            "Where are your strengths?",
            height=100, placeholder="e.g., definitions; diagrams"
        )
        st.caption("These can flow into your tutor screens as initial weaknesses/strengths.")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Proceed", type="primary", use_container_width=True):
            st.session_state["prioritization_mode"] = mode.startswith("Prioritization")
            go("home")
