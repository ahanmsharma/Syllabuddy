# streamlit_app.py
# Central router & bootstrap for Syllabuddy (modular pages)

from __future__ import annotations
import json
import os
from typing import Dict, List, Tuple

# streamlit_app.py  (only the relevant diffs shown)

# ...
from review.review import page_srs_review, page_cram_review
from review.how import page_cram_how        # <-- ADD THIS
from fp.fp import page_weakness_report, page_fp_flow, ensure_fp_state
# ...

ROUTES = {
    # Home
    "home": page_home,

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

    # NEW: How-to-review screen referenced by review/review.py
    "cram_how":    page_cram_how,          # <-- ADD THIS

    # AI suggestion/review
    "ai_select": page_ai_select,
    "ai_review": page_ai_review,

    # FP engine (DnD cloze + specific→general)
    "weakness_report": page_weakness_report,
    "fp_flow":         page_fp_flow,
}

import streamlit as st

# ---- Import shared UI + page modules ----

# Navigation is provided via a ``go`` function stored in ``st.session_state``.
# Use ``get_go`` to fetch (and lazily create) this function during bootstrap.
from common.ui import get_go

# Global reference for convenience; initialised in ``ensure_core_state``.
go = None

from homepage.homepage import page_home, page_select_subject_main
from srs.srs import page_srs_menu

from selection.widgets import (
    page_cram_subjects, page_cram_modules, page_cram_iqs, page_cram_dotpoints,
    page_srs_subjects,  page_srs_modules,  page_srs_iqs,  page_srs_dotpoints,
)

from review.review import page_srs_review, page_cram_review
from ai.ai import page_ai_select, page_ai_review

# FP engine (DnD integrated)
from fp.fp import page_weakness_report, page_fp_flow, ensure_fp_state


# ---------------- Page config ----------------
st.set_page_config(page_title="Syllabuddy", layout="wide")


# ---------------- Data loading ----------------
def _fallback_syllabus() -> Dict:
    # Minimal built-in so app always runs
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
    """
    Return:
      subjects,
      modules_by_subject,
      iqs_by_subject_module,
      dotpoints_by_subject_module_iq
    """
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
    # Navigation handler
    global go
    go = get_go()  # ensure ``_go`` exists and keep a local reference

    # Route
    st.session_state.setdefault("route", "home")

    # Selection sets required by selection/review pages
    st.session_state.setdefault("sel_dotpoints", set())  # set of (subject, module, iq, dp)
    st.session_state.setdefault("focus_subject", None)
    st.session_state.setdefault("focus_module", None)  # (s, m)
    st.session_state.setdefault("focus_iq", None)      # (s, m, iq)

    # Load syllabus once and fan out into fast-lookups used by selection pages
    if "_SYL" not in st.session_state:
        data = load_syllabus()
        subjects, mods, iqs, dps = explode_syllabus(data)
        st.session_state["_SYL"] = data
        st.session_state["_SUBJECTS"] = subjects
        st.session_state["_MODS"] = mods                     # Dict[str, List[str]]
        st.session_state["_IQS"] = iqs                       # Dict[(s,m), List[iq]]
        st.session_state["_DPS"] = dps                       # Dict[(s,m,iq), List[dp]]


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

    # Review screens
    "srs_review":  page_srs_review,
    "cram_review": page_cram_review,

    # AI suggestion/review
    "ai_select": page_ai_select,
    "ai_review": page_ai_review,

    # FP engine (DnD cloze + specific→general queue)
    "weakness_report": page_weakness_report,
    "fp_flow":         page_fp_flow,
}


# ---------------- Main dispatch ----------------
def main():
    ensure_core_state()
    ensure_fp_state()  # initialize FP engine state safely

    route = st.session_state.get("route", "home")
    ROUTES.get(route, page_home)()


if __name__ == "__main__":
    main()
