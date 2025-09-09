import streamlit as st
from common.ui import topbar
from selection.widgets import subject_cards, module_cards, iq_cards, dotpoint_cards

def page_cram_subjects():
    go = st.session_state["_go"]
    subject_cards(key_prefix="cram",
                  back_to=("srs_menu" if st.session_state["cram_mode"] else "select_subject_main"))
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("cram_review")

def page_cram_modules():
    go = st.session_state["_go"]
    s = st.session_state.get("focus_subject")
    if not s: go("cram_subjects"); return
    module_cards(s, key_prefix="cram", back_to="cram_subjects")

def page_cram_iqs():
    go = st.session_state["_go"]
    sm = st.session_state.get("focus_module")
    if not sm: go("cram_modules"); return
    s, m = sm
    iq_cards(s, m, key_prefix="cram", back_to="cram_modules")

def page_cram_dotpoints():
    go = st.session_state["_go"]
    smi = st.session_state.get("focus_iq")
    if not smi: go("cram_iqs"); return
    s, m, iq = smi
    dotpoint_cards(s, m, iq, key_prefix="cram", back_to="cram_iqs")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("cram_review")

def page_cram_how():
    go = st.session_state["_go"]
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
