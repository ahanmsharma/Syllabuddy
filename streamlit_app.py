import json
import os
import re
import random
import pathlib
from typing import Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ================== FLAGS ==================
FORCE_PLACEHOLDERS = True  # keep AI off for now

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
    # Better non-AI FP prompt template by subject; feel free to extend
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
    st.session_state.nav_guard = None

if "stage" not in st.session_state:
    reset_flow()

# ================== SIDEBAR NAV (collapsible) ==================
with st.sidebar:
    st.header("Navigation")
    subject = st.selectbox("Subject", list(syllabus.keys()), key="nav_subj")
    module  = st.selectbox("Module", list(syllabus[subject].keys()), key="nav_mod")
    iq      = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()), key="nav_iq")
    chosen_dp = st.radio("Dotpoint", syllabus[subject][module][iq], key="nav_dp")

    current_dp = st.session_state.get("selected_dp")
    target_tuple = (subject, module, iq, chosen_dp)

    if current_dp is not None and current_dp != target_tuple and st.session_state.stage in ("fp","report","cloze","post_cloze","fp_followups"):
        st.session_state.nav_guard = {"target": target_tuple}
    else:
        st.session_state.selected_dp = target_tuple

# Navigation guard (modal-like panel)
if st.session_state.nav_guard:
    st.markdown('<div class="guard">', unsafe_allow_html=True)
    st.markdown("### Heads up")
    st.write("You’re leaving this dotpoint before finishing. What should I do?")
    colg = st.columns([1,1,1])
    with colg[0]:
        if st.button("Save as incomplete (SRS next)", use_container_width=True):
            # TODO: persist as incomplete + SRS
            reset_flow()
            st.session_state.selected_dp = st.session_state.nav_guard["target"]
            st.session_state.nav_guard = None
            st.rerun()
    with colg[1]:
        rating_tmp = st.slider("Mark complete (rate 0–10)", 0, 10, 7, key="guard_rating")
        if st.button("Save & schedule", use_container_width=True):
            # TODO: persist rating + SRS
            reset_flow()
            st.session_state.selected_dp = st.session_state.nav_guard["target"]
            st.session_state.nav_guard = None
            st.rerun()
    with colg[2]:
        if st.button("Cancel", use_container_width=True):
            st.session_state.nav_guard = None
            # revert sidebar selection
            subj, mod, iqx, dp = st.session_state.selected_dp
            st.session_state.nav_subj = subj
            st.session_state.nav_mod  = mod
            st.session_state.nav_iq   = iqx
            st.session_state.nav_dp   = dp
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Resolve current context
subject, module, iq, dotpoint = st.session_state.selected_dp

# ================== MAIN ==================
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
        st.session_state.weak_index = 0
        st.session_state.current_cloze = None
        st.session_state.cloze_specificity = 0
        st.session_state.correct_flags = None
        st.session_state._dnd_segs = None
        st.session_state._dnd_ans = None
        st.session_state._dnd_bank = None
        st.session_state._dnd_fills = None
        st.session_state.stage = "cloze" if st.session_state.weak_list else "fp"
        st.rerun()

# ----- CLOZE (with review kept until Continue) -----
elif st.session_state.stage == "cloze":
    # Prepare cloze
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

    target_label = st.session_state.weak_list[st.session_state.weak_index] if st.session_state.weak_list else "this topic"
    st.markdown(f'<div class="box-label">Targeting: {target_label}</div>', unsafe_allow_html=True)

    # If reviewed, compute % for borders
    page_frame = "none"
    bad_pct = 30
    if st.session_state.correct_flags is not None:
        c = sum(st.session_state.correct_flags)
        total = len(st.session_state.correct_flags) or 1
        bad_pct = int((total - c) / total * 100)
        page_frame = "good" if c == total else "mixed"

    # Card border class
    card_class = ""
    if st.session_state.correct_flags is not None:
        c = sum(st.session_state.correct_flags)
        total = len(st.session_state.correct_flags) or 1
        card_class = "good" if c == total else "mixed"

    # Render component
    with st.container():
        comp_state = dnd_cloze(
            segments=segs,
            answers=ans,
            initial_bank=bank,
            initial_fills=fills,
            show_feedback=(st.session_state.correct_flags is not None),
            page_frame=page_frame, bad_pct=bad_pct,
            key=f"dnd_{st.session_state.weak_index}"
        )
        if comp_state:
            st.session_state._dnd_bank  = comp_state.get("bank", bank)
            st.session_state._dnd_fills = comp_state.get("fills", fills)

    # Submit
    cols = st.columns([1,1,1])
    with cols[1]:
        submitted = st.button("Submit", type="primary", use_container_width=True)
    if submitted:
        got = [ (x or "") for x in st.session_state._dnd_fills ]
        flags = [ a.strip().lower() == g.strip().lower() for a, g in zip(ans, got) ]
        st.session_state.correct_flags = flags
        st.rerun()

    # REVIEW BLOCK (stays until Continue)
    if st.session_state.correct_flags is not None:
        c = sum(st.session_state.correct_flags)
        total = len(st.session_state.correct_flags)
        klass = "good" if c == total else "mixed"
        bad_pct = int((total - c) / total * 100)
        st.markdown(f'<div class="cloze-card {klass}" style="--badpct:{bad_pct}%"><strong>Review your cloze:</strong> Score {c}/{total}. Green/red borders show correct/incorrect per blank. The full-page border matches overall correctness. </div>', unsafe_allow_html=True)

        cols2 = st.columns([1,1,1])
        with cols2[1]:
            if st.button("Continue", use_container_width=True):
                st.session_state.last_cloze_result = (c, total)
                st.session_state.stage = "post_cloze"
                st.rerun()

# ----- POST-CLOZE (rating + weaknesses -> branch) -----
elif st.session_state.stage == "post_cloze":
    c, t = st.session_state.last_cloze_result if st.session_state.last_cloze_result else (0,0)
    st.info(f"Cloze score: {c}/{t}")

    colA, colB = st.columns([1,1])
    with colA:
        rating = st.slider("Rate your understanding (0–10)", 0, 10, 6, key="cloze_rating")
    with colB:
        more_w = st.text_input("Add weaknesses (semicolon-separated)", key="more_wk", placeholder="e.g., boundary conditions; term definitions")

    go = st.columns(3)[1].button("Continue", use_container_width=True)
    if go:
        # Merge new weaknesses (dedupe, cap 5)
        add_list = [w.strip() for w in (more_w or "").split(";") if w.strip()]
        merged = st.session_state.weak_list[:]
        for w in add_list:
            if w not in merged: merged.append(w)
        st.session_state.weak_list = merged[:5]

        if rating <= 6:
            # more specific cloze on same weakness
            st.session_state.cloze_specificity = 1
            st.session_state.current_cloze = None
            st.session_state.correct_flags = None
            st.session_state._dnd_segs = None
            st.session_state._dnd_ans = None
            st.session_state._dnd_bank = None
            st.session_state._dnd_fills = None
            st.session_state.stage = "cloze"
            st.rerun()
        else:
            # move to per-weakness FP follow-ups (placeholder)
            st.session_state.cloze_specificity = 0
            st.session_state.current_cloze = None
            st.session_state.correct_flags = None
            st.session_state._dnd_segs = None
            st.session_state._dnd_ans = None
            st.session_state._dnd_bank = None
            st.session_state._dnd_fills = None
            st.session_state.stage = "fp_followups"
            st.rerun()

# ----- FP FOLLOW-UPS (placeholder) -----
elif st.session_state.stage == "fp_followups":
    current_weak = st.session_state.weak_list[st.session_state.weak_index] if st.session_state.weak_list else "this topic"
    st.markdown(f"**Follow-up first-principles questions for:** _{current_weak}_")
    qlist = [
        f"Derive the governing relationship for {current_weak}, starting only from definitions and conservation principles.",
        f"Explain how {current_weak} behaves under an extreme boundary case and justify each step of your reasoning."
    ]
    for q in qlist: st.write("• " + q)

    if st.button("Next weakness"):
        st.session_state.weak_index += 1
        st.session_state.current_cloze = None
        st.session_state.correct_flags = None
        st.session_state._dnd_segs = None
        st.session_state._dnd_ans = None
        st.session_state._dnd_bank = None
        st.session_state._dnd_fills = None
        st.session_state.cloze_specificity = 0
        if st.session_state.weak_index < len(st.session_state.weak_list):
            st.session_state.stage = "cloze"
        else:
            st.success("All weaknesses cleared. (Next: overall dotpoint rating / exam mode.)")
            st.session_state.stage = "fp"
        st.rerun()
