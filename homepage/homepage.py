# homepage/homepage.py
import streamlit as st
from common.ui import go, ns

def page_home():
    st.title("📘 Syllabuddy")
    st.write("Your minimalist AI-powered syllabus study buddy.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Start Reviewing", key=ns("home", "start")):
            go("srs_menu")
    with c2:
        if st.button("Select Subject", key=ns("home", "select")):
            go("select_subject")

def page_select_subject_main():
    st.header("Select a subject")
    subjects = ["Biology", "Chemistry"]
    choice = st.selectbox("Subject", subjects, key=ns("select_subject", "sb"))
    if st.button("Continue", key=ns("select_subject", "continue")):
        go("srs_modules", subject=choice)
