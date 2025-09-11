# review/how.py
from __future__ import annotations
import streamlit as st
from common.ui import topbar, get_go

def page_cram_how():
    """
    Screen that runs right after Cram Review:
      - SR option sends back to SRS subjects (until your SR engine route is ready)
      - Prioritization goes to the FP weakness workflow (weakness_report)
    """
    go = get_go()
    topbar("How to review", back_to="cram_review")

    mode = st.radio(
        "Choose order:",
        ["SR (spaced repetition order)", "Prioritization (based on strengths/weaknesses)"],
        index=1,
    )

    st.write("")
    mid = st.columns(3)[1]
    with mid:
        if st.button("Proceed", type="primary", use_container_width=True):
            if mode.startswith("Prioritization"):
                go("weakness_report")   # → FP engine (DnD cloze flow)
            else:
                # If you add an SR engine route later, swap this to that route.
                go("srs_subjects")
