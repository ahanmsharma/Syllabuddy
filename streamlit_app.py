import json
import re
import random
import pathlib
from typing import Dict, List, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ================== FLAGS ==================
FORCE_PLACEHOLDERS = True  # disable AI for now

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

      /* Review container around cloze */
      .cloze-card { border: 3px solid transparent; border-radius: 12px; padding: 12px; }
      .cloze-card.good { border-color: #16a34a; }
      .cloze-card.mixed {
        border-image-slice: 1; border-width: 3px; border-style: solid;
        border-image-source: linear-gradient(90deg, #dc2626 var(--badpct,30%), #16a34a var(--badpct,30%));
      }

      .guard { background:#fff8e1; border:1px solid #f59e0b; padding:12px; border-radius:10px; }
      .guard h4 { margin:0 0 8px 0; }

      /* Global page frame */
      .global-frame {
        position: fixed; inset: 0; pointer-events: none; z-index: 9999;
        border: 6px solid transparent; border-radius: 0;
      }
      .global-frame.good { border-color: #16a34a; }
      .global-frame.mixed {
        border-image-slice: 1; border-style: solid; border-width: 6px;
        border-image-source: linear-gradient(90deg, #dc2626 var(--badpct,30%), #16a34a var(--badpct,30%));
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

# ================== COMPONENT WRAPPER ==================
BUILD_DIR = str(pathlib.Path(__file__).parent / "frontend" / "build")
_dnd_cloze = components.declare_component("dnd_cloze", path=BUILD_DIR)

def dnd_cloze(segments, answers, initial_bank, initial_fills, *, show_feedback=False, page_frame="none", bad_pct=30, key=None):
    return _dnd_cloze(
        segments=segments,
        answers=answers,
        initialBank=initial_bank,
        initialFills=initial_fills,
        showFeedback=show_feedback,
        pageFrame=page_frame,
        badPct=bad_pct,
        key=key,
        default=None,
    )

# ================== HELPERS ==================
BLANK_RE = re.compile(r"\[\[(.+?)\]\]")

def smart_fp(dotpoint: str, subject: str) -> str:
    if subject.lower() in ("physics", "chemistry"):
        return (f"Starting from definitions and conservation laws, derive the key relation for “{dotpoint}”. "
                f"State assumptions, show each step of reasoning, and discuss limiting cases.")
    if subject.lower() == "biology":
        return (f"Using first principles (structure→function), explain the mechanism behind “{dotpoint}”, "
                f"identify necessary conditions, and predict outcomes if a key assumption is violated.")
    return (f"From first principles, explain and derive: “{dotpoint}”. Include assumptions and edge cases.")

def placeholder_report(ans: str) -> Dict:
    return {
        "suggested_weaknesses": ["definition gap", "unclear mechanism", "weak example"],
        "suggested_strengths": ["correct terms", "coherent structure"]
    }

def placeholder_cloze(level:int=0) -> str:
    if level == 0:
        return (
            "Diffusion is the net movement of particles from [[higher concentration]] to [[lower concentration]]. "
            "The rate increases with [[temperature]] due to greater [[kinetic energy]], and decreases with larger [[molecular size]]. "
            "Across membranes, diffusion proceeds through the [[phospholipid bilayer]] if molecules are [[nonpolar or small]]."
        )
    return (
        "Facilitated diffusion employs [[membrane proteins]] such as [[channel proteins]] or [[carrier proteins]] "
        "to move solutes down a [[concentration gradient]] without [[ATP hydrolysis]]. "
        "Saturation occurs when all [[binding sites]] are occupied."
    )

def split_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_RE.findall(cloze)
    parts = BLANK_RE.split(cloze)
    segments = [parts[0]]
    for i in range(1, len(parts), 2):
        segments.append(parts[i+1] if i+1 < len(parts) else "")
    return segments, answers

def fp_followup_questions(weakness: str, subject: str, dotpoint: str) -> List[str]:
    if subject.lower() in ("physics","chemistry"):
        return [
            f"From definitions, derive or justify the relationship most sensitive to '{weakness}' in “{dotpoint}”. State assumptions.",
            f"Test '{weakness}' in an extreme case: predict behavior and explain each step causally."
        ]
    if subject.lower() == "biology":
        return [
            f"Explain the mechanism in “{dotpoint}” where '{weakness}' plays a role. Identify structures and conditions.",
            f"Predict an outcome if '{weakness}' is violated or removed, and justify physiologically."
        ]
    return [
        f"Derive or justify the principle connected to '{weakness}' in “{dotpoint}”.",
        f"Give a boundary/edge-case analysis focused on '{weakness}' and explain implications."
    ]

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
    st.session_state.nav_guard = None

if "stage" not in st.session_state:
    reset_flow()

# ================== SIDEBAR NAV (collapsible) ==================
with st.sidebar:
    st.header("Navigation")

    with st.expander("Subject", expanded=True):
        subject = st.selectbox("Subject", list(syllabus.keys()), key="nav_subj")

    with st.expander("Module", expanded=True):
        module  = st.selectbox("Module", list(syllabus[subject].keys()), key="nav_mod")

    with st.expander("Inquiry Question", expanded=True):
        iq      = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()), key="nav_iq")

    with st.expander("Dotpoint", expanded=True):
        chosen_dp = st.radio("Dotpoint", syllabus[subject][module][iq], key="nav_dp")

    current_dp = st.session_state.get("selected_dp")
    target_tuple = (subject, module, iq, chosen_dp)

    if current_dp is not None and current_dp != target_tuple and st.session_state.stage in ("fp","report","cloze","post_cloze","fp_followups"):
        st.session_state.nav_guard = {"target": target_tuple}
    else:
        st.session_state.selected_dp = target_tuple

# ================== MAIN ==================
subject, module, iq, dotpoint = st.session_state.selected_dp
st.markdown(f'<div class="dotpoint">{dotpoint}</div>', unsafe_allow_html=True)

# ----- FP -----
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        st.session_state.fp_q = smart_fp(dotpoint, subject)
    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form("fp_form"):
        blurt = st.text_area("Your answer", key="fp_blurt", height=320, label_visibility="collapsed", placeholder="Type your answer here…")
        if st.form_submit_button("Submit"):
            st.session_state.user_blurt = blurt or ""
            sug = placeholder_report(st.session_state.user_blurt)
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
        st.markdown('<div class="box-label">AI Weakness report</div>', unsafe_allow_html=True)
        wk = st.text_area("Weaknesses", value=st.session_state.reports["weaknesses"], key="wk_edit", height=240, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="box-label">AI Strength report</div>', unsafe_allow_html=True)
        stg = st.text_area("Strengths", value=st.session_state.reports["strengths"], key="stg_edit", height=240, label_visibility="collapsed")

    if st.button("Continue"):
        st.session_state.weak_list = [w.strip() for w in (wk or "").split(";") if w.strip()][:5]
        st.session_state.reports["strengths"] = stg or ""
        st.session_state.stage = "cloze"
        st.rerun()

# ----- CLOZE -----
elif st.session_state.stage == "cloze":
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = placeholder_cloze(st.session_state.cloze_specificity)
        segs, ans = split_cloze(st.session_state.current_cloze)
        bank = ans[:]; random.shuffle(bank)
        st.session_state._dnd_segs = segs
        st.session_state._dnd_ans = ans
        st.session_state._dnd_bank = bank
        st.session_state._dnd_fills = [None] * len(ans)
        st.session_state.correct_flags = None

    segs = st.session_state._dnd_segs
    ans  = st.session_state._dnd_ans
    bank = st.session_state._dnd_bank
    fills= st.session_state._dnd_fills

    target_label = st.session_state.weak_list[0] if st.session_state.weak_list else "this topic"
    st.markdown(f'<div class="box-label">Targeting: {target_label}</div>', unsafe_allow_html=True)

    # page frame if reviewed
    page_frame = "none"
    bad_pct = 30
    if st.session_state.correct_flags is not None:
        c = sum(st.session_state.correct_flags)
        total = len(st.session_state.correct_flags) or 1
        bad_pct = int((total - c) / total * 100)
        page_frame = "good" if c == total else "mixed"
        st.markdown(f'<div class="global-frame {page_frame}" style="--badpct:{bad_pct}%"></div>', unsafe_allow_html=True)

    comp_state = dnd_cloze(
        segments=segs,
        answers=ans,
        initial_bank=bank,
        initial_fills=fills,
        show_feedback=(st.session_state.correct_flags is not None),
        page_frame=page_frame,
        bad_pct=bad_pct,
        key="dnd"
    )
   
