# fp/fp.py
# Focused Practice engine:
# General FP → Weakness report (general) → Cloze (general weakness) → Review → Weakness report (specific)
# → FP (specific) → Cloze (specific) → loop specifics → next general → finish
from __future__ import annotations
import os
import pathlib
import random
import re
from typing import List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

# ------------- DnD Cloze Component (fallback if build not present) -------------
BUILD_DIR = str(pathlib.Path(__file__).resolve().parent.parent / "frontend" / "build")
_dnd_cloze = None
if os.path.exists(BUILD_DIR):
    try:
        _dnd_cloze = components.declare_component("dnd_cloze", path=BUILD_DIR)
    except Exception:
        _dnd_cloze = None  # fall back to text inputs


def _render_dnd_cloze(segments: List[str], answers: List[str], bank: List[str],
                      initial_fills: Optional[List[Optional[str]]] = None) -> Tuple[List[Optional[str]], List[bool]]:
    """
    Renders the DnD cloze if available; else falls back to text inputs.
    Returns (fills, flags) where fills are the user's choices; flags True/False per blank.
    """
    fills: List[Optional[str]] = list(initial_fills or [None] * len(answers))

    if _dnd_cloze is not None:
        payload = _dnd_cloze(
            segments=segments,
            answers=answers,
            bank=bank,
            initial_fills=fills,
            key=f"dnd_{st.session_state.get('fp_ptr', 0)}_{len(answers)}"
        )
        # payload is expected to be {"fills":[...], "correct":[...]} per your working component
        if isinstance(payload, dict):
            fills = payload.get("fills", fills)
            flags = payload.get("correct", [False] * len(answers))
        else:
            flags = [False] * len(answers)
        return fills, flags

    # ---- Fallback (typed blanks) ----
    st.info("Drag-and-drop cloze component not found — using typed blanks as fallback.")
    new_fills = list(fills)
    st.write("")  # spacing
    st.markdown('<div class="cloze-wrap">', unsafe_allow_html=True)
    for i in range(len(answers)):
        st.write(segments[i], unsafe_allow_html=True)
        new_fills[i] = st.text_input(f"Blank {i+1}", value=new_fills[i] or "", key=f"txt_blank_{i}")
    st.write(segments[-1], unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    flags = [(a.strip().lower() == (new_fills[i] or "").strip().lower()) for i, a in enumerate(answers)]
    return new_fills, flags


# ------------------------- FP State & Helpers -------------------------
def ensure_fp_state():
    """Create all FP-related state keys if missing."""
    ss = st.session_state
    ss.setdefault("fp_stage", "fp_general_q")  # entry stage
    ss.setdefault("fp_ptr", 0)                 # general weakness pointer
    ss.setdefault("fp_attempts", 0)
    ss.setdefault("fp_direct_exam", False)

    # Dotpoint context (use the first selected if available)
    ss.setdefault("active_dotpoint", None)
    if ss["active_dotpoint"] is None:
        sel = list(ss.get("sel_dotpoints", []))
        ss["active_dotpoint"] = sel[0] if sel else ("Biology", "Module 6: Genetic Change", "IQ1: Mutations", "Describe point vs frameshift mutations")

    # General weaknesses list & specific queues per weakness
    ss.setdefault("fp_weak_list", [])             # ["osmosis", "equilibrium Kc", ...] (general)
    ss.setdefault("fp_specific_map", {})          # { "osmosis": ["reverse osmosis", ...], ... }
    ss.setdefault("fp_cur_general", None)         # current general weakness name
    ss.setdefault("fp_specific_queue", [])        # specifics for current general
    ss.setdefault("fp_cur_specific", None)        # current specific weakness name

    # Cloze scratch
    ss.setdefault("fp_cloze_text", None)
    ss.setdefault("fp_cloze_segments", None)
    ss.setdefault("fp_cloze_answers", None)
    ss.setdefault("fp_cloze_fills", None)
    ss.setdefault("fp_cloze_flags", None)

    # Ratings
    ss.setdefault("fp_last_rating", None)


def _fp_title():
    s, m, iq, dp = st.session_state.get("active_dotpoint", ("Subject", "Module", "IQ", "Dotpoint"))
    return f"{s} → {m} → {iq}", dp


def _general_fp_questions(dp_text: str) -> List[str]:
    return [
        f"Explain the first principles behind: **{dp_text}**. Start from definitions, then laws/relationships.",
        "List the key variables and how they interact. Provide a very simple, concrete example.",
    ]


def _specific_fp_questions(topic: str) -> List[str]:
    return [
        f"In your own words, explain **{topic}** and why learners commonly struggle with it.",
        f"Give two short examples for **{topic}**, and state one pitfall + a fix.",
    ]


def _cloze_from_weakness(weak: str, specific: bool) -> Tuple[List[str], List[str], List[str]]:
    """
    Build a simple bracketed cloze and return (segments, answers, bank).
    """
    if not weak:
        weak = "this topic"

    if specific:
        s = f"{weak} often requires [stepwise] [reasoning] using [definitions] and [laws]. Start by [identifying] variables, then [relate] them."
    else:
        s = f"{weak} is about [understanding] [core] [ideas]. A useful strategy is [recall], [apply], then [reflect]."

    parts = re.split(r"\[([^\]]+)\]", s)  # seg0, ans0, seg1, ans1, seg2, ...
    segs, ans = [], []
    for i, p in enumerate(parts):
        if i % 2 == 0:
            segs.append(p)
        else:
            ans.append(p)

    if len(segs) == len(ans):  # ensure segs = answers+1
        segs.append("")

    # bank = answers + a couple distractors
    distractors = ["assumptions", "units", "notation", "context", "estimate"]
    bank = list(dict.fromkeys(ans + random.sample(distractors, k=min(3, len(distractors)))))

    return segs, ans, bank


# ------------------------- Pages -------------------------
def page_exam_mode_placeholder():
    st.title("Exam Mode (placeholder)")
    st.write("This will generate HSC-style questions, show a sample answer, and let you tag weaknesses for targeted loops.")
    if st.button("Back to Home"):
        st.session_state["route"] = "home"
        st.rerun()


def _btn(label: str, key: Optional[str] = None, primary: bool = False):
    return st.button(label, key=key, type=("primary" if primary else "secondary"), use_container_width=True)


def page_fp_flow():
    """
    Main FP flow. Stages:
      - fp_general_q  -> general first-principles questions (+ optional skip to Exam mode)
      - weak_general  -> user lists general weaknesses (semicolon)
      - cloze_general -> cloze for current general weakness
      - cloze_review  -> rating + (optional) add specifics
      - weak_specific -> user lists specifics for current general weakness
      - fp_specific   -> first-principles questions on specific weakness
      - cloze_specific-> cloze for specific weakness; then back to weak_specific for next specific
      - fp_more       -> more general FP if needed, then decision
      - decision      -> next dotpoint / quit / exam mode
    """
    ensure_fp_state()
    ss = st.session_state
    header, dp_text = _fp_title()

    # ----- fp_general_q -----
    if ss["fp_stage"] == "fp_general_q":
        st.title("First-Principles (General)")
        st.caption(header)
        q = _general_fp_questions(dp_text)

        with st.form(key="fp_general_form"):
            a1 = st.text_area("Q1", q[0], height=160)
            a2 = st.text_area("Q2", q[1], height=160)
            col = st.columns([1,1,1])
            with col[0]:
                direct_exam = st.checkbox("Skip to Exam Mode (optional)", value=False)
            with col[1]:
                rating = st.slider("Rate your current understanding (0–10)", 0, 10, 6)
            submitted = st.form_submit_button("Continue", type="primary")

        if submitted:
            ss["fp_direct_exam"] = direct_exam
            ss["fp_last_rating"] = rating
            if direct_exam:
                ss["route"] = "exam_mode"
                st.rerun()
            else:
                ss["fp_stage"] = "weak_general"
                st.rerun()
        return

    # ----- weak_general -----
    if ss["fp_stage"] == "weak_general":
        st.title("Weakness Report — General")
        st.caption("List up to five general weaknesses (semicolon-separated).")
        defaults = "; ".join(ss.get("fp_weak_list", []))
        text = st.text_area("General weaknesses", value=defaults, height=120,
                            placeholder="e.g., osmosis; equilibrium Kc; vectors")

        proceed = _btn("Continue", primary=True)
        if proceed:
            ss["fp_weak_list"] = [w.strip() for w in (text or "").split(";") if w.strip()][:5]
            ss["fp_ptr"] = 0
            ss["fp_cur_general"] = ss["fp_weak_list"][0] if ss["fp_weak_list"] else None
            # prep a cloze for the first general weakness
            ss["fp_cloze_text"] = None
            ss["fp_stage"] = "cloze_general" if ss["fp_cur_general"] else "fp_more"
            st.rerun()
        return

    # ----- cloze_general -----
    if ss["fp_stage"] == "cloze_general":
        st.title("Cloze — General Weakness")
        st.caption(f"Target: **{ss['fp_cur_general']}**")

        if ss["fp_cloze_text"] is None:
            segs, ans, bank = _cloze_from_weakness(ss["fp_cur_general"], specific=False)
            ss["fp_cloze_segments"] = segs
            ss["fp_cloze_answers"] = ans
            ss["fp_cloze_fills"] = [None] * len(ans)
            ss["fp_cloze_text"] = "ready"
            ss["fp_cloze_flags"] = None

        fills, flags = _render_dnd_cloze(
            ss["fp_cloze_segments"], ss["fp_cloze_answers"], bank=[],
            initial_fills=ss["fp_cloze_fills"]
        )
        ss["fp_cloze_fills"] = fills
        ss["fp_cloze_flags"] = flags

        col = st.columns([1,1,1])
        if col[1].button("Submit Cloze", type="primary", use_container_width=True):
            st.experimental_set_query_params()  # nudge rerender without callback rerun
            ss["fp_stage"] = "cloze_review"
            st.rerun()
        return

    # ----- cloze_review -----
    if ss["fp_stage"] == "cloze_review":
        st.title("Cloze Review")
        flags = ss.get("fp_cloze_flags") or []
        correct = sum(1 for f in flags if f)
        total = len(flags)
        st.info(f"Score: {correct}/{total}")

        colA, colB = st.columns([1,1])
        with colA:
            rating = st.slider("Rate your understanding now (0–10)", 0, 10, 7, key=f"clz_rate_{ss['fp_ptr']}")
        with colB:
            add_specs = st.text_input("Add **specific** weaknesses (semicolon)", key=f"clz_specs_{ss['fp_ptr']}",
                                      placeholder="e.g., reverse osmosis; boundary conditions")

        col = st.columns([1,1,1])
        if col[1].button("Continue"):
            # store specifics into map
            specs = [w.strip() for w in (add_specs or "").split(";") if w.strip()]
            cur = ss["fp_cur_general"]
            if specs:
                m = ss.get("fp_specific_map", {})
                m.setdefault(cur, [])
                # de-dup
                for s in specs:
                    if s not in m[cur]:
                        m[cur].append(s)
                ss["fp_specific_map"] = m
                ss["fp_specific_queue"] = m[cur][:]
                ss["fp_cur_specific"] = ss["fp_specific_queue"].pop(0)
                ss["fp_stage"] = "weak_specific"
            else:
                # no specifics, proceed to more general FP or next general later
                ss["fp_last_rating"] = rating
                ss["fp_stage"] = "fp_more"
            st.rerun()
        return

    # ----- weak_specific -----
    if ss["fp_stage"] == "weak_specific":
        st.title("Weakness Report — Specific")
        cur = ss["fp_cur_general"]
        st.caption(f"General: **{cur}** — Add/confirm specifics (semicolon-separated).")
        existing = ss.get("fp_specific_map", {}).get(cur, [])
        defaults = "; ".join(existing)
        text = st.text_input("Specific weaknesses", value=defaults,
                             placeholder="e.g., reverse osmosis; diffusion vs facilitated diffusion")

        if _btn("Continue", primary=True):
            specs = [w.strip() for w in (text or "").split(";") if w.strip()]
            m = ss.get("fp_specific_map", {})
            m[cur] = specs[:]
            ss["fp_specific_map"] = m
            ss["fp_specific_queue"] = specs[:]
            ss["fp_cur_specific"] = ss["fp_specific_queue"].pop(0) if ss["fp_specific_queue"] else None
            ss["fp_stage"] = "fp_specific" if ss["fp_cur_specific"] else "fp_more"
            st.rerun()
        return

    # ----- fp_specific -----
    if ss["fp_stage"] == "fp_specific":
        cur_gen = ss["fp_cur_general"]
        cur_spec = ss["fp_cur_specific"]
        st.title("First-Principles (Specific)")
        st.caption(f"Target: **{cur_gen}** / **{cur_spec}**")
        q = _specific_fp_questions(cur_spec)

        with st.form(key=f"fp_spec_form_{cur_spec}"):
            a1 = st.text_area("Q1", q[0], height=150)
            a2 = st.text_area("Q2", q[1], height=150)
            rating = st.slider("Rate your understanding (0–10)", 0, 10, 7)
            submitted = st.form_submit_button("Continue", type="primary")

        if submitted:
            ss["fp_last_rating"] = rating
            # after specific FP, do a specific cloze
            segs, ans, bank = _cloze_from_weakness(cur_spec, specific=True)
            ss["fp_cloze_segments"] = segs
            ss["fp_cloze_answers"] = ans
            ss["fp_cloze_fills"] = [None] * len(ans)
            ss["fp_cloze_flags"] = None
            ss["fp_stage"] = "cloze_specific"
            st.rerun()
        return

    # ----- cloze_specific -----
    if ss["fp_stage"] == "cloze_specific":
        cur_spec = ss["fp_cur_specific"]
        st.title("Cloze — Specific")
        st.caption(f"Specific target: **{cur_spec}**")

        fills, flags = _render_dnd_cloze(
            st.session_state["fp_cloze_segments"],
            st.session_state["fp_cloze_answers"],
            bank=[],
            initial_fills=st.session_state["fp_cloze_fills"]
        )
        st.session_state["fp_cloze_fills"] = fills
        st.session_state["fp_cloze_flags"] = flags

        col = st.columns([1,1,1])
        if col[1].button("Submit Cloze", type="primary", use_container_width=True):
            # proceed back to weak_specific to pull next specific or advance to general
            if st.session_state["fp_specific_queue"]:
                st.session_state["fp_cur_specific"] = st.session_state["fp_specific_queue"].pop(0)
                st.session_state["fp_stage"] = "fp_specific"
            else:
                # done with specifics → continue general flow
                st.session_state["fp_stage"] = "fp_more"
            st.rerun()
        return

    # ----- fp_more -----
    if ss["fp_stage"] == "fp_more":
        st.title("More First-Principles (General)")
        st.caption("If you still feel shaky, answer a couple more to consolidate.")
        q = [
            "State two ‘gotchas’ in this area and how to avoid them.",
            "Write a one-minute explanation for a friend."
        ]
        with st.form(key="fp_more_form"):
            a1 = st.text_area("Q1", q[0], height=140)
            a2 = st.text_area("Q2", q[1], height=140)
            rating = st.slider("Rate your understanding (0–10)", 0, 10, 8)
            submitted = st.form_submit_button("Continue", type="primary")

        if submitted:
            ss["fp_last_rating"] = rating
            # Move to next general weakness if any, else decision page
            if ss["fp_ptr"] < len(ss["fp_weak_list"]) - 1:
                ss["fp_ptr"] += 1
                ss["fp_cur_general"] = ss["fp_weak_list"][ss["fp_ptr"]]
                ss["fp_cloze_text"] = None
                ss["fp_stage"] = "cloze_general"
            else:
                ss["fp_stage"] = "decision"
            st.rerun()
        return

    # ----- decision -----
    if ss["fp_stage"] == "decision":
        st.title("What next?")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Next dotpoint", use_container_width=True):
                # Rotate to next selected dotpoint (MVP)
                sel = list(st.session_state.get("sel_dotpoints", []))
                if sel:
                    try:
                        i = sel.index(st.session_state["active_dotpoint"])
                        st.session_state["active_dotpoint"] = sel[(i + 1) % len(sel)]
                    except Exception:
                        st.session_state["active_dotpoint"] = sel[0]
                # Reset FP state for the new dotpoint
                _reset_for_new_dotpoint()
                st.rerun()
        with c2:
            if st.button("Exam mode", use_container_width=True):
                st.session_state["route"] = "exam_mode"
                st.rerun()
        with c3:
            if st.button("Quit", use_container_width=True):
                st.session_state["route"] = "home"
                st.rerun()
        return


def _reset_for_new_dotpoint():
    ss = st.session_state
    ss["fp_stage"] = "fp_general_q"
    ss["fp_ptr"] = 0
    ss["fp_attempts"] = 0
    ss["fp_direct_exam"] = False
    ss["fp_weak_list"] = []
    ss["fp_specific_map"] = {}
    ss["fp_cur_general"] = None
    ss["fp_specific_queue"] = []
    ss["fp_cur_specific"] = None
    ss["fp_cloze_text"] = None
    ss["fp_cloze_segments"] = None
    ss["fp_cloze_answers"] = None
    ss["fp_cloze_fills"] = None
    ss["fp_cloze_flags"] = None
    ss["fp_last_rating"] = None
