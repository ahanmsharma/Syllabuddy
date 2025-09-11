# fp/fp_mvp.py
from __future__ import annotations
import re
import random
from typing import Dict, List, Tuple, Optional

import streamlit as st

# ========== Public entrypoints ==========
def ensure_fp_state():
    """Create stable FP state container if missing."""
    if "_fp" not in st.session_state:
        _reset_all()

def begin_fp_from_selection():
    """
    Build a DP queue from st.session_state['sel_dotpoints'] and route to 'fp_run'.
    Expects items as tuples: (subject, module, iq, dotpoint).
    """
    ensure_fp_state()
    dps = list(st.session_state.get("sel_dotpoints", set()))
    dps.sort()
    if not dps:
        st.warning("No dotpoints selected yet. Use Select/Cram → Review first.")
        return
    st.session_state._fp["queue"] = dps
    st.session_state._fp["q_idx"] = 0
    _reset_for_current_dp()
    st.session_state["route"] = "fp_run"
    st.rerun()

def page_fp_run():
    """The single-screen FP engine for the current dotpoint in the queue."""
    ensure_fp_state()
    _guard_queue()
    dp = _current_dp()
    if not dp:
        st.success("All selected dotpoints complete. Great work!")
        if st.button("Back to Home"):
            st.session_state["route"] = "home"
            st.rerun()
        return

    s, m, iq, dotpoint = dp
    st.markdown(f"### {dotpoint}")
    stage = st.session_state._fp["stage"]

    if stage == "fp_general":
        _stage_fp_general(s, m, iq, dotpoint)
    elif stage == "report_general":
        _stage_report_general()
    elif stage == "cloze_general":
        _stage_cloze(is_specific=False)
    elif stage == "report_specific":
        _stage_report_specific()
    elif stage == "fp_specific":
        _stage_fp_specific(s, m, iq, dotpoint)
    elif stage == "cloze_specific":
        _stage_cloze(is_specific=True)
    elif stage == "fp_more":
        _stage_fp_more()
    elif stage == "decision":
        _stage_decision()
    else:
        st.session_state._fp["stage"] = "fp_general"
        st.rerun()


# ========== Internal state/model ==========
def _reset_all():
    st.session_state._fp = {
        # queue of dotpoints
        "queue": [],       # List[(s,m,iq,dp)]
        "q_idx": 0,        # which dotpoint
        # per-DP flow state
        "stage": "fp_general",
        "fp_q": None,
        "direct_exam": False,
        "user_blurt": "",
        "reports": {"weaknesses": "", "strengths": ""},
        # general weaknesses
        "general_list": [],
        "general_idx": 0,
        "cur_general": None,
        # specifics per general
        "spec_map": {},       # general -> List[str]
        "spec_queue": [],
        "cur_specific": None,
        # cloze scratch
        "current_cloze": None,
        "cloze_specificity": 0,
        "correct_flags": None,
        "last_cloze_result": None,
        "_segs": None,
        "_ans": None,
        "_bank": None,
        "_fills": None,
    }

def _reset_for_current_dp():
    fp = st.session_state._fp
    fp.update({
        "stage": "fp_general",
        "fp_q": None,
        "direct_exam": False,
        "user_blurt": "",
        "reports": {"weaknesses": "", "strengths": ""},
        "general_list": [],
        "general_idx": 0,
        "cur_general": None,
        "spec_map": {},
        "spec_queue": [],
        "cur_specific": None,
        "current_cloze": None,
        "cloze_specificity": 0,
        "correct_flags": None,
        "last_cloze_result": None,
        "_segs": None,
        "_ans": None,
        "_bank": None,
        "_fills": None,
    })

def _guard_queue():
    if not st.session_state._fp["queue"]:
        return
    qi = st.session_state._fp["q_idx"]
    if qi < 0:
        st.session_state._fp["q_idx"] = 0
    if qi >= len(st.session_state._fp["queue"]):
        st.session_state._fp["q_idx"] = len(st.session_state._fp["queue"]) - 1

def _current_dp() -> Optional[Tuple[str,str,str,str]]:
    q = st.session_state._fp["queue"]
    if not q:
        return None
    return q[st.session_state._fp["q_idx"]]

# ========== FP prompts & cloze ==========
def _smart_fp(dotpoint: str, subject: str) -> str:
    subj = (subject or "").lower()
    if subj in ("physics", "chemistry"):
        return (f"Starting from definitions and conservation laws, derive/explain the key relation for “{dotpoint}”. "
                f"State assumptions, show each step of reasoning, and discuss limiting cases.")
    if subj == "biology":
        return (f"Using first principles (structure→function), explain the mechanism behind “{dotpoint}”, "
                f"identify necessary conditions, and predict outcomes if a key assumption is violated.")
    return (f"From first principles, explain and derive: “{dotpoint}”. Include assumptions and edge cases.")

def _placeholder_report(ans: str) -> Dict:
    return {
        "suggested_weaknesses": ["definition gap", "unclear mechanism", "weak example"],
        "suggested_strengths": ["correct terms", "coherent structure"]
    }

_BLANK_RE = re.compile(r"\[\[(.+?)\]\]")

def _placeholder_cloze(level:int=0) -> str:
    if level == 0:
        return (
            "Diffusion is the net movement of particles from [[higher concentration]] to [[lower concentration]]. "
            "The rate increases with [[temperature]] due to greater [[kinetic energy]], and decreases with larger [[molecular size]]. "
            "Across membranes, diffusion occurs through the [[phospholipid bilayer]] for [[nonpolar or small]] molecules."
        )
    return (
        "Facilitated diffusion employs [[membrane proteins]] such as [[channel proteins]] or [[carrier proteins]] "
        "to move solutes down a [[concentration gradient]] without [[ATP hydrolysis]]. "
        "Saturation arises when all [[binding sites]] are occupied."
    )

def _split_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = _BLANK_RE.findall(cloze)
    parts = _BLANK_RE.split(cloze)
    segments = [parts[0]]
    for i in range(1, len(parts), 2):
        segments.append(parts[i+1] if i+1 < len(parts) else "")
    return segments, answers

# ---------- DnD component (fallback to text inputs if not found) ----------
def _get_component():
    # late import to avoid global dependency in other pages
    import streamlit.components.v1 as components
    import pathlib
    BUILD_DIR = str(pathlib.Path(__file__).resolve().parent.parent / "frontend" / "build")
    if pathlib.Path(BUILD_DIR).exists():
        try:
            return components.declare_component("dnd_cloze", path=BUILD_DIR)
        except Exception:
            return None
    return None

def _render_cloze(segments, answers, fills, bank, key, show_feedback=False):
    comp = _get_component()
    if comp:
        return comp(
            segments=segments,
            answers=answers,
            initialBank=bank,
            initialFills=fills,
            showFeedback=show_feedback,
            pageFrame="none",
            badPct=30,
            key=key,
            default=None,
        )
    # fallback inputs
    st.info("Cloze DnD component not found — using typed blanks.")
    new_fills = list(fills)
    for i in range(len(answers)):
        st.write(segments[i])
        new_fills[i] = st.text_input(f"Blank {i+1}", value=new_fills[i] or "", key=f"{key}_txt_{i}")
    st.write(segments[-1])
    flags = [(a.strip().lower() == (new_fills[i] or "").strip().lower()) for i, a in enumerate(answers)]
    return {"bank": bank, "fills": new_fills, "correct": flags}

# ========== Stages ==========
def _stage_fp_general(s, m, iq, dotpoint):
    fp = st.session_state._fp
    if not fp["fp_q"]:
        fp["fp_q"] = _smart_fp(dotpoint, s)
    st.write(fp["fp_q"])

    with st.form("fp_general_form"):
        blurt = st.text_area("Your answer (general FP)", key="fp_blurt", height=300,
                             placeholder="Type everything you can from first principles…")
        c1, c2 = st.columns(2)
        with c1:
            fp["direct_exam"] = st.checkbox("Skip straight to Exam Mode (optional)", value=False, key="exam_skip_chk")
        with c2:
            st.slider("Self-rating before weaknesses (0–10)", 0, 10, 6, key="pre_rate")
        submitted = st.form_submit_button("Continue", type="primary")

    if submitted:
        fp["user_blurt"] = blurt or ""
        if fp["direct_exam"]:
            st.success("Exam Mode placeholder — will generate HSC-style Qs + sample answers.")
            if st.button("Return to FP"):
                fp["direct_exam"] = False
                st.rerun()
            return
        sug = _placeholder_report(fp["user_blurt"])
        fp["reports"] = {
            "weaknesses": "; ".join(sug["suggested_weaknesses"]),
            "strengths": "; ".join(sug["suggested_strengths"]),
        }
        fp["stage"] = "report_general"
        st.rerun()

def _stage_report_general():
    fp = st.session_state._fp
    c1, c2 = st.columns(2, gap="large")
    with c1:
        wk = st.text_area("Weaknesses (general) — edit", value=fp["reports"]["weaknesses"],
                          key="wk_edit_gen", height=200)
    with c2:
        stg = st.text_area("Strengths — edit", value=fp["reports"]["strengths"],
                           key="stg_edit_gen", height=200)

    if st.button("Continue", type="primary"):
        fp["general_list"] = [w.strip() for w in (wk or "").split(";") if w.strip()][:5]
        fp["reports"]["strengths"] = stg or ""
        fp["general_idx"] = 0
        fp["cur_general"] = fp["general_list"][0] if fp["general_list"] else None
        # reset cloze
        fp.update({
            "current_cloze": None, "cloze_specificity": 0, "correct_flags": None,
            "_segs": None, "_ans": None, "_bank": None, "_fills": None
        })
        fp["stage"] = "cloze_general" if fp["cur_general"] else "fp_more"
        st.rerun()

def _stage_cloze(is_specific: bool):
    fp = st.session_state._fp
    # prepare cloze once
    if not fp["current_cloze"]:
        txt = _placeholder_cloze(level=1 if is_specific else 0)
        segs, ans = _split_cloze(txt)
        bank = ans[:]; random.shuffle(bank)
        fp.update({
            "current_cloze": txt, "_segs": segs, "_ans": ans, "_bank": bank,
            "_fills": [None] * len(ans), "correct_flags": None
        })

    segs, ans, bank, fills = fp["_segs"], fp["_ans"], fp["_bank"], fp["_fills"]
    label = fp["cur_specific"] if is_specific else (fp["cur_general"] or "this topic")
    st.caption(f"Targeting: {label} ({'specific' if is_specific else 'general'})")

    comp_state = _render_cloze(segs, ans, fills, bank, key=f"dnd_{'spec' if is_specific else 'gen'}_{fp['general_idx']}",
                               show_feedback=(fp["correct_flags"] is not None))
    if comp_state:
        fp["_bank"]  = comp_state.get("bank", bank)
        fp["_fills"] = comp_state.get("fills", fills)
        fp["correct_flags"] = comp_state.get("correct", fp["correct_flags"])

    if st.button("Submit", type="primary"):
        if fp["correct_flags"] is None:
            got = [ (x or "") for x in fp["_fills"] ]
            fp["correct_flags"] = [ a.strip().lower() == g.strip().lower() for a, g in zip(ans, got) ]
        st.rerun()

    if fp["correct_flags"] is not None:
        c = sum(fp["correct_flags"]); total = len(fp["correct_flags"]) or 1
        st.info(f"Cloze score: {c}/{total}")
        if st.button("Continue"):
            fp["last_cloze_result"] = (c, total)
            # wipe cloze scratch
            fp.update({
                "current_cloze": None, "_segs": None, "_ans": None, "_bank": None, "_fills": None,
                "correct_flags": None
            })
            fp["stage"] = "report_specific" if not is_specific else "fp_more"
            st.rerun()

def _stage_report_specific():
    fp = st.session_state._fp
    cur = fp["cur_general"] or "this topic"
    st.caption(f"Add specifics for: **{cur}**")
    defaults = "; ".join(fp["spec_map"].get(cur, []))
    specs_text = st.text_input("Specific weaknesses (semicolon-separated)", value=defaults,
                               key=f"specs_{cur}", placeholder="e.g., reverse osmosis; boundary conditions")
    if st.button("Continue", type="primary"):
        specs = [w.strip() for w in (specs_text or "").split(";") if w.strip()]
        fp["spec_map"][cur] = specs[:]
        fp["spec_queue"] = specs[:]
        fp["cur_specific"] = fp["spec_queue"].pop(0) if fp["spec_queue"] else None
        fp["stage"] = "fp_specific" if fp["cur_specific"] else "fp_more"
        st.rerun()

def _stage_fp_specific(s, m, iq, dotpoint):
    fp = st.session_state._fp
    cur_gen = fp["cur_general"] or "this topic"
    cur_spec = fp["cur_specific"] or "detail"
    st.markdown(f"**First-Principles (Specific):** _{cur_gen} / {cur_spec}_")
    q = _fp_followup_questions(cur_spec, s, dotpoint)
    with st.form(key=f"fp_spec_form_{cur_spec}"):
        st.text_area("Q1", q[0], height=140, key=f"spec_a1_{cur_spec}")
        st.text_area("Q2", q[1], height=140, key=f"spec_a2_{cur_spec}")
        st.slider("Rate your understanding (0–10)", 0, 10, 7, key=f"rate_{cur_spec}")
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        # prep specific cloze next
        txt = _placeholder_cloze(level=1)
        segs, ans = _split_cloze(txt)
        bank = ans[:]; random.shuffle(bank)
        fp.update({
            "current_cloze": txt, "_segs": segs, "_ans": ans, "_bank": bank,
            "_fills": [None] * len(ans), "correct_flags": None
        })
        fp["stage"] = "cloze_specific"
        st.rerun()

def _stage_fp_more():
    fp = st.session_state._fp
    st.markdown("**Quick consolidation (optional)**")
    with st.form(key="fp_more_form"):
        st.text_area("Q1", "State two ‘gotchas’ in this area and how to avoid them.", height=120)
        st.text_area("Q2", "Write a one-minute explanation for a friend.", height=120)
        st.slider("Rate your understanding (0–10)", 0, 10, 8, key="more_rate")
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        # next general or decision
        if fp["general_idx"] < len(fp["general_list"]) - 1:
            fp["general_idx"] += 1
            fp["cur_general"] = fp["general_list"][fp["general_idx"]]
            # reset specifics for new general
            fp["spec_queue"] = []
            fp["cur_specific"] = None
            # reset cloze scratch
            fp.update({
                "current_cloze": None, "_segs": None, "_ans": None, "_bank": None, "_fills": None,
                "correct_flags": None
            })
            fp["stage"] = "cloze_general"
        else:
            fp["stage"] = "decision"
        st.rerun()

def _stage_decision():
    fp = st.session_state._fp
    st.success("Weakness cycle complete for this dotpoint.")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Next dotpoint", use_container_width=True):
            if fp["q_idx"] < len(fp["queue"]) - 1:
                fp["q_idx"] += 1
                _reset_for_current_dp()
            else:
                st.success("All selected dotpoints done.")
                st.session_state["route"] = "home"
            st.rerun()
    with c2:
        if st.button("Exam mode (placeholder)", use_container_width=True):
            st.info("HSC-style questions + sample answers will appear here.")
    with c3:
        if st.button("Quit to Home", use_container_width=True):
            st.session_state["route"] = "home"
            st.rerun()

def _fp_followup_questions(weakness: str, subject: str, dotpoint: str) -> List[str]:
    subj = (subject or "").lower()
    if subj in ("physics","chemistry"):
        return [
            f"From definitions, derive or justify the relationship most sensitive to '{weakness}' in “{dotpoint}”. State assumptions.",
            f"Test '{weakness}' in an extreme case: predict behavior and explain each step causally."
        ]
    if subj == "biology":
        return [
            f"Explain the mechanism in “{dotpoint}” where '{weakness}' plays a role. Identify structures and conditions.",
            f"Predict an outcome if '{weakness}' is violated or removed, and justify physiologically."
        ]
    return [
        f"Derive or justify the principle connected to '{weakness}' in “{dotpoint}”.",
        f"Provide a boundary-case analysis focused on '{weakness}' and explain implications."
    ]
