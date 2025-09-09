import streamlit as st

from data.data import load_syllabus, explode_syllabus, ensure_core_state
from common.style import inject_css
from common.ui import set_go, safe_rerun  # do not remove / rename

# Pages
from homepage.homepage import page_home, page_select_subject_main
from srs.srs import (
    page_srs_menu, page_srs_subjects, page_srs_modules,
    page_srs_iqs, page_srs_dotpoints
)
from cram.cram import (
    page_cram_subjects, page_cram_modules, page_cram_iqs,
    page_cram_dotpoints, page_cram_how
)
from ai.ai import page_ai_select, page_ai_review
from review.review import page_srs_review, page_cram_review

# ---------- page config & CSS ----------
st.set_page_config(page_title="Syllabuddy", layout="wide")
inject_css()

# ---------- router setter that works across Streamlit versions ----------
def go(route: str):
    st.session_state["route"] = route
    safe_rerun()

# register go() for submodules
set_go(go)

# ---------- data & shared state ----------
SYL = load_syllabus()
SUBJECTS, MODS, IQS, DPS = explode_syllabus(SYL)
ensure_core_state()

# share to modules via session_state
st.session_state["_SUBJECTS"] = SUBJECTS
st.session_state["_MODS"] = MODS
st.session_state["_IQS"] = IQS
st.session_state["_DPS"] = DPS

# ---------- router map ----------
ROUTES = {
    "home": page_home,
    "select_subject_main": page_select_subject_main,

    # SRS
    "srs_menu": page_srs_menu,
    "srs_subjects": page_srs_subjects,
    "srs_modules": page_srs_modules,
    "srs_iqs": page_srs_iqs,
    "srs_dotpoints": page_srs_dotpoints,
    "srs_review": page_srs_review,

    # Cram
    "cram_subjects": page_cram_subjects,
    "cram_modules": page_cram_modules,
    "cram_iqs": page_cram_iqs,
    "cram_dotpoints": page_cram_dotpoints,
    "cram_review": page_cram_review,
    "cram_how": page_cram_how,

    # AI
    "ai_select": page_ai_select,
    "ai_review": page_ai_review,
}

# default route
if "route" not in st.session_state:
    st.session_state["route"] = "home"

# dispatch
ROUTES.get(st.session_state["route"], page_home)()
