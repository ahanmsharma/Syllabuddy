# streamlit_app.py
import streamlit as st
from common.ui import init_session, go

st.set_page_config(page_title="Syllabuddy", layout="centered")
init_session(default_route="home")

# Import pages AFTER init_session to avoid circular imports
from homepage.homepage import page_home, page_select_subject_main
from srs.srs import (
    page_srs_menu,
    page_srs_subjects,
    page_srs_modules,
    page_srs_iqs,
    page_srs_dotpoints,
    page_cram_review,
)

ROUTES = {
    "home": page_home,
    "select_subject": page_select_subject_main,
    "srs_menu": page_srs_menu,
    "srs_subjects": page_srs_subjects,
    "srs_modules": page_srs_modules,
    "srs_iqs": page_srs_iqs,
    "srs_dotpoints": page_srs_dotpoints,
    "cram_review": page_cram_review,
}

def main():
    route = st.session_state.get("route", "home")
    page = ROUTES.get(route, page_home)
    page()

if __name__ == "__main__":
    main()
