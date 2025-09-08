import json
import os
import re
import random
import pathlib
from typing import Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ================== FLAGS ==================
FORCE_PLACEHOLDERS = True  # Keep AI off for now until frontend is stable

# ================== PAGE / STYLE ==================
st.set_page_config(page_title="", layout="wide")
st.markdown(
    """
    <style>
      header {visibility: hidden;}
      #MainMenu {visibility: hidden;} footer {visibility: hidden;}
      .block-container { max-width: 1280px; margin: auto; padding-top: .2rem; }

      .dotpoint { font-weight: 700; font-size: 1.35rem; margin: .25rem 0 .65rem 0; }
      .fpq { font-size: 1.18rem; margin: 0 0 .5rem 0; }
      .box-label { font-weight: 600; color: #555; margin: .25rem 0 .35rem 0; }
      .feedback { border: 3px solid transparent; border-radius: 12px; padding: 12px; margin-top: .5rem; }
      .feedback.good { border-color: #22c55e; }
      .feedback.mixed {
        border-image-slice:1; border-width:3px; border-style:solid;
        border-image-source: linear-gradient(90deg, #dc2626 var(--badpct,30%), #22c55e var(--badpct,30%));
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================== DATA ==================
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    with open("syllabus.json", "r") as f:
        return json.load(f)

syllabus = load_syllabus()

# ================== DnD CLOZE COMPONENT ==================
BUILD_DIR = str(pathlib.Path(__file__).parent / "frontend" / "build")
_dnd_cloze = components.declare_component("dnd_cloze", path=BUILD_DIR)

def dnd_cloze(segments, answers, initial_bank, initial_fills, show_feedback=False, key=None):
    """
    Returns dict: {"bank":[...], "fills":[...]}
    """
    return _dnd_cloze(
        segments=segments,
        answers=answers,
        initialBank=initial_bank,
        initialFills=initial_fills,
        showFeedback=show_feedback,
        key=key,
        default=None,
    )

# ================== HELPERS ==================
BLANK_RE = re.compile(r"\[\[(.+?)\]\]")

def placeholder_fp(dotpoint: str) -> str:
    return f"From first principles, explain and derive: “{dotpoint}”."

def placeholder_report(ans: str) -> Dict:
    return {
        "suggested_weaknesses": ["definition gap", "unclear mechanism", "weak example"],
        "suggested_strengths": ["correct terms", "coherent structure"]
    }

def placeholder_cloze(level:int=0) -> str:
    if level==0:
        return "Diffusion is movement from [[higher concentration]] to [[lower concentration]] across a [[semi-permeable membrane]]."
    return "Facilitated diffusion uses [[membrane proteins]] to move molecules down a [[concentration gradient]] without [[ATP hydrolysis]]."

def split_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_RE.findall(cloze)
    parts = BLANK_RE.split(cloze)
    segments = [parts[0]]
    for i in range(1, len(parts), 2):
        segments.append(parts[i+1] if i+1 < len(parts) else "")
    return segments, answers

# ================== STATE ==================
def reset_flow():
    st.session_state.stage = "fp"
    st.session_state.fp_q = None
    st.session_state.user_blurt = ""
    st.session_state.reports = {"weaknesses":"", "strengths":""}
    st.session_state.weak_list = []
    st.session_state.weak_index = 0
    st.session_state.current_cloze = None
    st.session_state.cloze_specificity = 0
    st.session_state.correct_flags = None
    st.session_state.last_cloze_result = None
    st.session_state._dnd_segs = None
    st.session_state._dnd_ans = None
    st.session_state._dnd_bank = None
    st.session_state._dnd_fills = None

if "stage" not in st.session_state:
    reset_flow()

# ================== SIDEBAR NAV ==================
with st.sidebar:
    st.header("Navigation")
    subject = st.selectbox("Subject", list(syllabus.keys()), key="nav_subj")
    module  = st.selectbox("Module", list(syllabus[subject].keys()), key="nav_mod")
    iq      = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()), key="nav_iq")
    chosen_dp = st.radio("Dotpoint", syllabus[subject][module][iq], key="nav_dp")

    current_dp = st.session_state.get("selected_dp")
    if current_dp != (subject, module, iq, chosen_dp):
        reset_flow()
    st.session_state.selected_dp = (subject, module, iq, chosen_dp)

subject, module, iq, dotpoint = st.session_state.selected_dp

# ================== MAIN ==================
st.markdown(f'<div class="dotpoint">{dotpoint}</div>', unsafe_allow_html=True)

# ----- FP -----
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        st.session_state.fp_q = placeholder_fp(dotpoint)
    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form("fp_form"):
        blurt = st.text_area("Your answer", key="fp_blurt", height=300, label_visibility="collapsed")
        if st.form_submit_button("Submit"):
            st.session_state.user_blurt = blurt
            sug = placeholder_report(blurt)
            st.session_state.reports = {
                "weaknesses": "; ".join(sug["suggested_weaknesses"]),
                "strengths": "; ".join(sug["suggested_strengths"])
            }
            st.session_state.stage = "report"
            st.rerun()

# ----- REPORT -----
elif st.session_state.stage == "report":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="box-label">Weaknesses</div>', unsafe_allow_html=True)
        wk = st.text_area("Weaknesses", value=st.session_state.reports["weaknesses"], key="wk_edit", height=220)
    with c2:
        st.markdown('<div class="box-label">Strengths</div>', unsafe_allow_html=True)
        stg = st.text_area("Strengths", value=st.session_state.reports["strengths"], key="stg_edit", height=220)

    if st.button("Continue"):
        st.session_state.weak_list = [w.strip() for w in wk.split(";") if w.strip()][:5]
        st.session_state.reports["strengths"] = stg
        st.session_state.stage = "cloze"
        st.rerun()

# ----- CLOZE -----
elif st.session_state.stage == "cloze":
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = placeholder_cloze(st.session_state.cloze_specificity)
        segs, ans = split_cloze(st.session_state.current_cloze)
        bank = ans[:]
        random.shuffle(bank)
        st.session_state._dnd_segs = segs
        st.session_state._dnd_ans = ans
        st.session_state._dnd_bank = bank
        st.session_state._dnd_fills = [None] * len(ans)

    segs = st.session_state._dnd_segs
    ans = st.session_state._dnd_ans
    bank = st.session_state._dnd_bank
    fills = st.session_state._dnd_fills

    st.markdown(f'<div class="box-label">Targeting: {st.session_state.weak_list[0] if st.session_state.weak_list else "general understanding"}</div>', unsafe_allow_html=True)

    comp_state = dnd_cloze(
        segments=segs,
        answers=ans,
        initial_bank=bank,
        initial_fills=fills,
        show_feedback=(st.session_state.correct_flags is not None),
        key="dnd_cloze"
    )
    if comp_state:
        st.session_state._dnd_bank = comp_state.get("bank", bank)
        st.session_state._dnd_fills = comp_state.get("fills", fills)

    if st.button("Submit Cloze", type="primary"):
        got = [ (x or "") for x in st.session_state._dnd_fills ]
        flags = [ a.strip().lower() == g.strip().lower() for a, g in zip(ans, got) ]
        st.session_state.correct_flags = flags
        st.rerun()

    if st.session_state.correct_flags is not None:
        c = sum(st.session_state.correct_flags)
        total = len(st.session_state.correct_flags)
        klass = "good" if c == total else "mixed"
        bad_pct = int((total - c) / total * 100)
        st.markdown(f'<div class="feedback {klass}" style="--badpct:{bad_pct}%">Score: {c}/{total}</div>', unsafe_allow_html=True)

        if st.button("Continue"):
            st.session_state.last_cloze_result = (c, total)
            st.session_state.stage = "post_cloze"
            st.rerun()

# ----- POST-CLOZE -----
elif st.session_state.stage == "post_cloze":
    c, t = st.session_state.last_cloze_result
    st.info(f"Cloze score: {c}/{t}")
    rating = st.slider("Rate your understanding", 0, 10, 6)
    if st.button("Continue"):
        if rating <= 6:
            st.session_state.cloze_specificity = 1
            st.session_state.current_cloze = None
            st.session_state.correct_flags = None
            st.session_state.stage = "cloze"
        else:
            st.session_state.stage = "fp"
        st.rerun()
