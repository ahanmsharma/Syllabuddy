# streamlit_app.py
# Central router & bootstrap for Syllabuddy (modular pages)

from __future__ import annotations
import json
import os
from typing import Dict, List, Tuple

import streamlit as st

# ---- Import shared UI + page modules (your existing files) ----
from common.ui import get_go
go = None  # will be set in ensure_core_state()

from homepage.homepage import page_home as _page_home, page_select_subject_main
from srs.srs import page_srs_menu as _page_srs_menu

from selection.widgets import (
    page_cram_subjects, page_cram_modules, page_cram_iqs, page_cram_dotpoints,
    page_srs_subjects,  page_srs_modules,  page_srs_iqs,  page_srs_dotpoints,
)

from review.review import page_srs_review, page_cram_review

# NEW: MVP FP engine
from fp.fp_mvp import ensure_fp_state, begin_fp_from_selection, page_fp_run


# ---------------- Page config ----------------
st.set_page_config(page_title="Syllabuddy", layout="wide")


# ---------------- Data loading ----------------
def _fallback_syllabus() -> Dict:
    return {
        "Biology": {
            "Module 6: Genetic Change": {
                "IQ1: Mutations": [
                    "Describe point vs frameshift mutations",
                    "Explain mutagens and mutation rates"
                ],
                "IQ2: Biotechnology": [
                    "Outline PCR steps and applications",
                    "Summarise CRISPR-Cas9 mechanism"
                ]
            }
        },
        "Chemistry": {
            "Module 5: Equilibrium": {
                "IQ1: Le Chatelier": [
                    "Predict shifts for concentration, pressure, temperature changes",
                    "Relate Kc to reaction quotient Q"
                ]
            }
        }
    }

def load_syllabus() -> Dict:
    path = "syllabus.json"
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _fallback_syllabus()

def explode_syllabus(data: Dict) -> Tuple[
    List[str],
    Dict[str, List[str]],
    Dict[Tuple[str, str], List[str]],
    Dict[Tuple[str, str, str], List[str]]
]:
    subjects = list(data.keys())
    modules_by_subject = {s: list(data[s].keys()) for s in subjects}
    iqs_by_subject_module = {}
    dps_by_smi = {}
    for s in subjects:
        for m in data[s]:
            iqs = list(data[s][m].keys())
            iqs_by_subject_module[(s, m)] = iqs
            for iq in iqs:
                dps_by_smi[(s, m, iq)] = list(data[s][m][iq])
    return subjects, modules_by_subject, iqs_by_subject_module, dps_by_smi


# ---------------- Bootstrap shared state ----------------
def ensure_core_state():
    global go
    go = get_go()  # stores _go in session_state and returns it

    # Route
    st.session_state.setdefault("route", "home")

    # Selection sets used by selection/review pages
    st.session_state.setdefault("sel_dotpoints", set())  # set of (subject, module, iq, dp)
    st.session_state.setdefault("focus_subject", None)
    st.session_state.setdefault("focus_module", None)  # (s, m)
    st.session_state.setdefault("focus_iq", None)      # (s, m, iq)

    # Load syllabus fan-outs once
    if "_SYL" not in st.session_state:
        data = load_syllabus()
        subjects, mods, iqs, dps = explode_syllabus(data)
        st.session_state["_SYL"] = data
        st.session_state["_SUBJECTS"] = subjects
        st.session_state["_MODS"] = mods
        st.session_state["_IQS"] = iqs
        st.session_state["_DPS"] = dps


# ---------------- Wrappers to add “Start FP” buttons ----------------
def page_home():
    _page_home()
    # If the user already picked dotpoints (e.g., via AI review or manual review), show Start FP
    if st.session_state.get("sel_dotpoints"):
        st.divider()
        if st.button("▶ Start Focused Practice", type="primary", use_container_width=True):
            begin_fp_from_selection()

def page_srs_menu():
    _page_srs_menu()
    if st.session_state.get("sel_dotpoints"):
        st.info(f"{len(st.session_state['sel_dotpoints'])} selected dotpoint(s) ready.")
        if st.button("▶ Start Focused Practice (SR selection)", type="primary", use_container_width=True):
            begin_fp_from_selection()


# ---------------- Router ----------------
ROUTES = {
    # Home
    "home": page_home,
    "select_subject_main": page_select_subject_main,
    "srs_menu": page_srs_menu,

    # Selection (CRAM)
    "cram_subjects": page_cram_subjects,
    "cram_modules":  page_cram_modules,
    "cram_iqs":      page_cram_iqs,
    "cram_dotpoints": page_cram_dotpoints,

    # Selection (SRS)
    "srs_subjects": page_srs_subjects,
    "srs_modules":  page_srs_modules,
    "srs_iqs":      page_srs_iqs,
    "srs_dotpoints": page_srs_dotpoints,

    # Review screens (unchanged)
    "srs_review":  page_srs_review,
    "cram_review": page_cram_review,

    # NEW: FP MVP routes
    "fp_start": begin_fp_from_selection,  # build queue + route to fp_run
    "fp_run":   page_fp_run,
}


# ---------------- Main dispatch ----------------
def main():
    ensure_core_state()
    ensure_fp_state()  # FP engine state

    route = st.session_state.get("route", "home")
    handler = ROUTES.get(route)
    if handler is None:
        st.session_state["route"] = "home"
        st.rerun()

    # If handler is a function that sets state and reruns (e.g., begin_fp_from_selection)
    # just call it; otherwise render a page.
    handler()

if __name__ == "__main__":
    main()
