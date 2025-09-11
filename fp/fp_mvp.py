# fp/fp_mvp.py
from __future__ import annotations
import re
import random
from typing import Dict, List, Tuple, Optional

import streamlit as st

# ========== Theme-aware CSS (global-frame + cloze card) ==========
FP_CSS = """
<style>
:root{
  --bg:#ffffff; --text:#111827; --muted:#6b7280;
  --ok:#16a34a; --bad:#dc2626; --border:#e5e7eb;
  --card:#ffffff; --cardTint:#f8fafc;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0b1220; --text:#e5e7eb; --muted:#94a3b8;
    --ok:#22c55e; --bad:#ef4444; --border:#334155;
    --card:#0f172a; --cardTint:#111827;
  }
}
.global-frame{
  position:fixed; inset:0; pointer-events:none; z-index:9999;
  border:6px solid transparent; border-radius:0;
}
.global-frame.good{ border-color: var(--ok); }
.global-frame.mixed{
  border-image-slice:1; border-style:solid; border-width:6px;
  border-image-source: linear-gradient(90deg, var(--bad) var(--badpct,30%), var(--ok) var(--badpct,30%));
}
.cloze-card{
  border:2px solid var(--border); border-radius:12px; padding:12px;
  background:var(--card); color:var(--text);
}
.cloze-card.good{ border-color: var(--ok); }
.cloze-card.mixed{
  border-image-slice:1; border-style:solid; border-width:2px;
  border-image-source: linear-gradient(90deg, var(--bad) var(--badpct,30%), var(--ok) var(--badpct,30%));
}
.hl{ color:var(--muted); font-weight:600; }
.dp-title{ font-weight:800; font-size:1.1rem; margin:.25rem 0 .75rem 0; color:var(--text); }
.subtle{ color:var(--muted); }
</style>
"""
st.markdown(FP_CSS, unsafe_allow_html=True)

# ========== Public entrypoints ==========
def ensure_fp_state():
    if "_fp" not in st.session_state:
        _reset_all()

def begin_fp_from_selection():
    """Build queue from sel_dotpoints → route to fp_run."""
    ensure_fp_state()
    dps = list(st.session_state.get("sel_dotpoints", set()))
    dps.sort()
    if not dps:
        st.warning("No dotpoints selected. Use Select/Review first.")
        return
    st.session_state._fp["queue"] = dps
    st.session_state._fp["q_idx"] = 0
    _reset_for_current_dp()
    st.session_state["route"] = "fp_run"
    st.rerun()

def page_fp_run():
    """Single-screen FP engine for current dotpoint."""
    ensure_fp_state()
    _guard_queue()
    dp = _current_dp()
    if not dp:
        st.success("All selected dotpoints complete. 🎉")
        if st.button("Back to Home"):
            st.session_state["route"] = "home"
            st.rerun()
        return

    s, m, iq, dotpoint = dp
    st.markdown(f'<div class="dp-title">{dotpoint}</div>', unsafe_allow_html=True)
    stage = st.session_state._fp["stage"]

    if stage == "fp_general":
        _stage_fp_general(s, m, iq, dotpoint)
    elif stage == "report_general":
        _stage_report_general()
    elif stage == "cloze_general":
        _stage_cloze(is_specific=False)
    elif stage == "post_cloze_general":
        _stage_post_cloze_general()
    elif stage == "report_specific":
        _stage_report_specific()
    elif stage == "fp_specific_q":
        _stage_fp_specific_question(s, m, iq, dotpoint)
    elif stage == "cloze_specific":
        _stage_cloze(is_specific=True)
    elif stage == "post_cloze_specific":
        _stage_post_cloze_specific()
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
        "queue": [], "q_idx": 0,
        "stage": "fp_general",
        "fp_q": None,
        "direct_exam": False,
        "user_blurt": "",

        "reports": {"weaknesses":"", "strengths":""},
        # general weaknesses
        "general_list": [],
        "general_idx": 0,
        "cur_general": None,
        # specifics per general
        "spec_map": {},         # general -> List[str]
        "spec_queue": [],
        "cur_specific": None,

        # follow-ups one-by-one
        "follow_qs": [],
        "follow_idx": 0,

        # cloze scratch
        "current_cloze": None,
        "cloze_specificity": 0,
        "correct_flags": None,
        "last_cloze_result": None,
        "_segs": None, "_ans": None, "_bank": None, "_fills": None,

        # ratings
        "ratings": [],  # list of dicts per step
    }

def _reset_for_current_dp():
    fp = st.session_state._fp
    fp.update({
        "stage": "fp_general",
        "fp_q": None,
        "direct_exam": False,
        "user_blurt": "",
        "reports": {"weaknesses":"", "strengths":""},
        "general_list": [], "general_idx": 0, "cur_general": None,
        "spec_map": {}, "spec_queue": [], "cur_specific": None,
        "follow_qs": [], "follow_idx": 0,
        "current_cloze": None, "cloze_specificity": 0, "correct_flags": None,
        "last_cloze_result": None, "_segs": None, "_ans": None, "_bank": None, "_fills": None,
        "ratings": [],
    })

def _guard_queue():
    q = st.session_state._fp["queue"]
    if not q: return
    if st.session_state._fp["q_idx"] >= len(q):
        st.session_state._fp["q_idx"] = len(q)-1
    if st.session_state._fp["q_idx"] < 0:
        st.session_state._fp["q_idx"] = 0

def _current_dp() -> Optional[Tuple[str,str,str,str]]:
    q = st.session_state._fp["queue"]
    if not q:
        return None
    return q[st.session_state._fp["q_idx"]]

# ========== Prompts / Cloze ==========
def _smart_fp(dotpoint: str, subject: str) -> str:
    subj = (subject or "").lower()
    if subj in ("physics", "chemistry"):
        return (f"From first principles (definitions, conservation laws), explain/derive the key relation for “{dotpoint}”. "
                f"State assumptions, show steps, and discuss limiting cases.")
    if subj == "biology":
        return (f"Using structure→function logic, explain the mechanism behind “{dotpoint}”. "
                f"Identify necessary conditions and predict what happens if one is violated.")
    return (f"From first principles, explain and derive: “{dotpoint}”. Include assumptions and edge cases.")

def _placeholder_report(ans: str) -> Dict:
    # lightweight, deterministic for MVP
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

# component loader (DnD). Falls back to typed blanks if build/ missing.
def _get_component():
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
    # fallback typed blanks (dark-mode text is handled by global CSS colors)
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
        blurt = st.text_area("Your answer", key="fp_blurt", height=280,
                             placeholder="Type your answer here…")
        pref = st.checkbox("Skip straight to Exam Mode (optional)", value=False)
        submitted = st.form_submit_button("Continue", type="primary")

    if submitted:
        fp["user_blurt"] = blurt or ""
        fp["direct_exam"] = bool(pref)
        if fp["direct_exam"]:
            st.info("Exam Mode placeholder (HSC-style questions + sample answers).")
            if st.button("Return to FP"):
                fp["direct_exam"] = False
                st.rerun()
            return
        sug = _placeholder_report(fp["user_blurt"])
        fp["reports"] = {"weaknesses": "; ".join(sug["suggested_weaknesses"]),
                         "strengths": "; ".join(sug["suggested_strengths"])}
        fp["stage"] = "report_general"
        st.rerun()

def _stage_report_general():
    fp = st.session_state._fp
    c1, c2 = st.columns(2, gap="large")
    with c1:
        wk = st.text_area("Weaknesses (general) — edit",
                          value=fp["reports"]["weaknesses"], key="wk_edit_gen", height=160)
    with c2:
        stg = st.text_area("Strengths — edit",
                           value=fp["reports"]["strengths"], key="stg_edit_gen", height=160)
    if st.button("Continue", type="primary"):
        fp["general_list"] = [w.strip() for w in (wk or "").split(";") if w.strip()][:5]
        fp["reports"]["strengths"] = stg or ""
        fp["general_idx"] = 0
        fp["cur_general"] = fp["general_list"][0] if fp["general_list"] else None
        fp.update({
            "current_cloze": None, "cloze_specificity": 0, "correct_flags": None,
            "_segs": None, "_ans": None, "_bank": None, "_fills": None
        })
        fp["stage"] = "cloze_general" if fp["cur_general"] else "fp_more"
        st.rerun()

def _stage_cloze(is_specific: bool):
    fp = st.session_state._fp
    # prepare once
    if not fp["current_cloze"]:
        txt = _placeholder_cloze(level=1 if is_specific else 0)
        segs, ans = _split_cloze(txt)
        bank = ans[:]; random.shuffle(bank)
        fp.update({
            "current_cloze": txt, "_segs": segs, "_ans": ans, "_bank": bank,
            "_fills": [None]*len(ans), "correct_flags": None
        })

    segs, ans, bank, fills = fp["_segs"], fp["_ans"], fp["_bank"], fp["_fills"]
    label = fp["cur_specific"] if is_specific else (fp["cur_general"] or "this topic")
    st.caption(f"Targeting: {label} ({'specific' if is_specific else 'general'})")

    comp_state = _render_cloze(segs, ans, fills, bank,
                               key=f"dnd_{'spec' if is_specific else 'gen'}_{fp['general_idx']}",
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

    # Feedback (green/red frame + card), then go to rating page
    if fp["correct_flags"] is not None:
        c = sum(fp["correct_flags"]); total = len(fp["correct_flags"]) or 1
        bad_pct = int((total - c) / total * 100)
        frame_class = "good" if c == total else "mixed"
        st.markdown(f'<div class="global-frame {frame_class}" style="--badpct:{bad_pct}%"></div>', unsafe_allow_html=True)
        klass = "good" if c == total else "mixed"
        st.markdown(
            f'<div class="cloze-card {klass}" style="--badpct:{bad_pct}%">'
            f'<span class="hl">Cloze review:</span> Score {c}/{total}. '
            f'Green/red borders reflect correctness (dark-mode friendly).'
            f'</div>', unsafe_allow_html=True
        )
        fp["last_cloze_result"] = (c, total)
        fp["stage"] = "post_cloze_specific" if is_specific else "post_cloze_general"
        st.rerun()

def _stage_post_cloze_general():
    fp = st.session_state._fp
    c, t = fp["last_cloze_result"] if fp["last_cloze_result"] else (0,0)
    st.info(f"Cloze score (general): {c}/{t}")
    rating = st.slider("Rate your understanding of this general target (0–10)", 0, 10, 7, key="rate_gen_cloze")
    more_w = st.text_input("Add (or refine) general weaknesses (semicolon-separated)", key="add_gen_w")
    if st.button("Continue", type="primary"):
        fp["ratings"].append({"stage":"post_cloze_general", "score": rating})
        # merge new general weaknesses (cap 5)
        add_list = [w.strip() for w in (more_w or "").split(";") if w.strip()]
        merged = fp["general_list"][:]
        for w in add_list:
            if w not in merged:
                merged.append(w)
        fp["general_list"] = merged[:5]
        # next: collect specifics for this general
        fp["stage"] = "report_specific"
        st.rerun()

def _stage_report_specific():
    fp = st.session_state._fp
    cur = fp["cur_general"] or "this topic"
    st.caption(f"Add specific weaknesses for: **{cur}**")
    defaults = "; ".join(fp["spec_map"].get(cur, []))
    specs_text = st.text_input("Specific weaknesses (semicolon-separated)", value=defaults,
                               key=f"specs_{cur}", placeholder="e.g., reverse osmosis; boundary conditions")
    if st.button("Continue", type="primary"):
        specs = [w.strip() for w in (specs_text or "").split(";") if w.strip()]
        fp["spec_map"][cur] = specs[:]
        fp["spec_queue"] = specs[:]
        fp["cur_specific"] = fp["spec_queue"].pop(0) if fp["spec_queue"] else None
        # Build follow-up list (one at a time)
        fp["follow_qs"] = _followup_questions_for(fp["cur_specific"] or cur)
        fp["follow_idx"] = 0
        fp["stage"] = "fp_specific_q" if fp["cur_specific"] else "fp_more"
        st.rerun()

def _stage_fp_specific_question(s, m, iq, dotpoint):
    """Show ONE question at a time (question text is NOT in a textbox)."""
    fp = st.session_state._fp
    cur_gen = fp["cur_general"] or "this topic"
    cur_spec = fp["cur_specific"] or cur_gen
    qlist = fp.get("follow_qs", [])
    idx = fp.get("follow_idx", 0)
    if idx >= len(qlist):
        # after finishing follow-ups, do a specific cloze
        txt = _placeholder_cloze(level=1)
        segs, ans = _split_cloze(txt)
        bank = ans[:]; random.shuffle(bank)
        fp.update({
            "current_cloze": txt, "_segs": segs, "_ans": ans, "_bank": bank,
            "_fills": [None]*len(ans), "correct_flags": None
        })
        fp["stage"] = "cloze_specific"
        st.rerun()
        return

    st.markdown(f"**Specific FP:** _{cur_gen} → {cur_spec}_")
    st.write(qlist[idx])  # question text (not in a textbox)
    with st.form(key=f"fp_spec_q_{idx}"):
        ans = st.text_area("Your answer", height=160, key=f"spec_q_ans_{idx}")
        rate = st.slider("Rate this specific question (0–10)", 0, 10, 7, key=f"spec_q_rate_{idx}")
        nexted = st.form_submit_button("Next", type="primary")
    if nexted:
        fp["ratings"].append({"stage":"fp_specific_q", "q_index": idx, "score": rate})
        fp["follow_idx"] = idx + 1
        st.rerun()

def _stage_cloze_specific():
    _stage_cloze(is_specific=True)

def _stage_post_cloze_specific():
    fp = st.session_state._fp
    c, t = fp["last_cloze_result"] if fp["last_cloze_result"] else (0,0)
    st.info(f"Cloze score (specific): {c}/{t}")
    rating = st.slider("Rate your understanding of this specific target (0–10)", 0, 10, 7, key="rate_spec_cloze")
    # After specific cloze we go to quick consolidation
    if st.button("Continue", type="primary"):
        fp["ratings"].append({"stage":"post_cloze_specific", "score": rating})
        fp["stage"] = "fp_more"
        st.rerun()

def _stage_fp_more():
    fp = st.session_state._fp
    st.markdown("**Quick consolidation (optional)**")
    with st.form(key="fp_more_form"):
        st.text_area("Write a one-minute explanation for a friend.", height=120)
        rate = st.slider("Rate your overall understanding (0–10)", 0, 10, 8, key="more_rate")
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        fp["ratings"].append({"stage":"fp_more", "score": rate})
        # Next general? Or done → decision
        if fp["general_idx"] < len(fp["general_list"]) - 1:
            fp["general_idx"] += 1
            fp["cur_general"] = fp["general_list"][fp["general_idx"]]
            # reset specifics for new general
            fp["spec_queue"] = []
            fp["cur_specific"] = None
            fp["follow_qs"] = []
            fp["follow_idx"] = 0
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
            st.info("HSC-style questions + sample answers (to come).")
    with c3:
        if st.button("Quit to Home", use_container_width=True):
            st.session_state["route"] = "home"
            st.rerun()

# ========== Helpers ==========
def _followup_questions_for(weakness: str) -> List[str]:
    w = weakness or "this topic"
    # Two clean, one-at-a-time prompts
    return [
        f"Explain {w} in your own words, then give a simple example.",
        f"List two common mistakes in {w} and how to avoid them."
    ]
