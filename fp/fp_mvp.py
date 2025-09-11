# fp/fp_mvp.py
from __future__ import annotations
import re
import random
from typing import Dict, List, Tuple, Optional

import streamlit as st

# ================= Theme-aware CSS =================
FP_CSS = """
<style>
:root{
  --bg:#ffffff; --text:#111827; --muted:#6b7280;
  --ok:#16a34a; --bad:#dc2626; --border:#e5e7eb;
  --card:#ffffff; --cardTint:#f8fafc; --inputBg:#ffffff; --inputText:#111827;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0b1220; --text:#e5e7eb; --muted:#94a3b8;
    --ok:#22c55e; --bad:#ef4444; --border:#334155;
    --card:#0f172a; --cardTint:#111827;
    --inputBg:#0b1220; --inputText:#e5e7eb;
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
.dp-title{ font-weight:800; font-size:1.14rem; margin:.25rem 0 .75rem 0; color:var(--text); }
.subtle{ color:var(--muted); }
.hl{ color:var(--muted); font-weight:600; }

/* Inputs readable in dark mode */
textarea, input[type="text"]{
  background: var(--inputBg) !important;
  color: var(--inputText) !important;
}

/* Per-blank review row */
.blank-row{
  border:2px solid var(--border); border-radius:10px; padding:10px; margin-bottom:10px;
}
.blank-row.ok{ border-color: var(--ok); }
.blank-row.bad{ border-color: var(--bad); }
.blank-lab{ font-weight:700; color:var(--muted); }
.blank-you{ margin-top:4px; }
.blank-correct{ margin-top:2px; color:var(--muted); }
</style>
"""
st.markdown(FP_CSS, unsafe_allow_html=True)

# ============== Public entrypoints ==============
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
    elif stage == "fp_general_review":
        _stage_fp_general_review()
    elif stage == "report_general":
        _stage_report_general()
    elif stage == "cloze_general":
        _stage_cloze(is_specific=False)
    elif stage == "cloze_general_review":
        _stage_cloze_review(is_specific=False)
    elif stage == "weakness_review_general":
        _stage_weakness_review_general()
    elif stage == "report_specific":
        _stage_report_specific()
    elif stage == "fp_specific_q":
        _stage_fp_specific_question(s, m, iq, dotpoint)
    elif stage == "fp_specific_review":
        _stage_fp_specific_review()
    elif stage == "cloze_specific":
        _stage_cloze(is_specific=True)
    elif stage == "cloze_specific_review":
        _stage_cloze_review(is_specific=True)
    elif stage == "weakness_review_specific":
        _stage_weakness_review_specific()
    elif stage == "fp_more":
        _stage_fp_more()
    elif stage == "decision":
        _stage_decision()
    else:
        st.session_state._fp["stage"] = "fp_general"
        st.rerun()

# ============== Internal state/model ==============
def _reset_all():
    st.session_state._fp = {
        "queue": [], "q_idx": 0,
        "stage": "fp_general",
        "fp_q": None,
        "direct_exam": False,
        "user_blurt": "",
        "fp_general_rating": None,
        "fp_general_model_answer": None,

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
        "spec_q_rating": None,
        "spec_q_model_answer": None,

        # cloze scratch
        "current_cloze": None,
        "cloze_specificity": 0,
        "correct_flags": None,
        "last_cloze_result": None,
        "_segs": None, "_ans": None, "_bank": None, "_fills": None,
        "cloze_rating": None,

        # ratings log
        "ratings": [],
    }

def _reset_for_current_dp():
    fp = st.session_state._fp
    fp.update({
        "stage": "fp_general",
        "fp_q": None,
        "direct_exam": False,
        "user_blurt": "",
        "fp_general_rating": None,
        "fp_general_model_answer": None,

        "reports": {"weaknesses":"", "strengths":""},
        "general_list": [], "general_idx": 0, "cur_general": None,
        "spec_map": {}, "spec_queue": [], "cur_specific": None,
        "follow_qs": [], "follow_idx": 0, "spec_q_rating": None, "spec_q_model_answer": None,

        "current_cloze": None, "cloze_specificity": 0, "correct_flags": None,
        "last_cloze_result": None, "_segs": None, "_ans": None, "_bank": None, "_fills": None,
        "cloze_rating": None,
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

# ============== Prompts / Model answers / Cloze ==============
def _smart_fp(dotpoint: str, subject: str) -> str:
    subj = (subject or "").lower()
    if subj in ("physics", "chemistry"):
        return (f"From first principles (definitions, conservation laws), explain/derive the key relation for “{dotpoint}”. "
                f"State assumptions, show steps, and discuss limiting cases.")
    if subj == "biology":
        return (f"Using structure→function logic, explain the mechanism behind “{dotpoint}”. "
                f"Identify necessary conditions and predict what happens if one is violated.")
    return (f"From first principles, explain and derive: “{dotpoint}”. Include assumptions and edge cases.")

def _model_answer(dotpoint: str, subject: str, mode: str = "general") -> str:
    """Placeholder AI model answer (keep deterministic for MVP)."""
    if mode == "specific":
        return (f"**Model answer (specific):** Clearly define the sub-idea, outline the stepwise reasoning, "
                f"and connect it to “{dotpoint}”. Include one worked micro-example and the key assumption.")
    subj = (subject or "").lower()
    if subj in ("physics", "chemistry"):
        return (f"**Model answer:** Start from definitions and conservation principles. Derive the governing relation for "
                f"“{dotpoint}”, justify each step, and note limiting cases (e.g., small angle/low concentration).")
    if subj == "biology":
        return (f"**Model answer:** Describe structures involved, causal mechanism, and necessary conditions for "
                f"“{dotpoint}”. Predict outcomes if a condition is removed, linking structure → function.")
    return (f"**Model answer:** Provide a definition, develop the principle logically, and illustrate with a compact example for “{dotpoint}”.")
    
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
    # fallback typed blanks (dark-mode styled via CSS above)
    new_fills = list(fills)
    for i in range(len(answers)):
        st.write(segments[i])
        new_fills[i] = st.text_input(f"Blank {i+1}", value=new_fills[i] or "", key=f"{key}_txt_{i}")
    st.write(segments[-1])
    flags = [(a.strip().lower() == (new_fills[i] or "").strip().lower()) for i, a in enumerate(answers)]
    return {"bank": bank, "fills": new_fills, "correct": flags}

# ============== Stages ==============
def _stage_fp_general(s, m, iq, dotpoint):
    fp = st.session_state._fp
    if not fp["fp_q"]:
        fp["fp_q"] = _smart_fp(dotpoint, s)

    st.write(fp["fp_q"])
    with st.form("fp_general_form"):
        blurt = st.text_area("Your answer", key="fp_blurt", height=280,
                             placeholder="Type your answer here…")
        direct_exam = st.checkbox("Skip to Exam Mode (optional)", value=False)
        submitted = st.form_submit_button("Submit", type="primary")

    if submitted:
        fp["user_blurt"] = blurt or ""
        fp["direct_exam"] = bool(direct_exam)
        fp["fp_general_model_answer"] = _model_answer(dotpoint, s, "general")

        # Move to review page: show model answer + immediate rating
        fp["stage"] = "fp_general_review"
        st.rerun()

def _stage_fp_general_review():
    fp = st.session_state._fp
    st.markdown(fp["fp_general_model_answer"], unsafe_allow_html=True)
    fp["fp_general_rating"] = st.slider("Rate your understanding (0–10)", 0, 10, 6, key="rate_fp_gen")
    cols = st.columns([1,1,1])
    with cols[1]:
        if st.button("Continue", type="primary", use_container_width=True):
            fp["ratings"].append({"stage":"fp_general", "score": fp["fp_general_rating"]})
            if fp["direct_exam"]:
                st.info("Exam Mode placeholder (HSC-style questions + sample answers).")
                if st.button("Return to FP"):
                    fp["direct_exam"] = False
                    st.rerun()
                return
            # proceed to weakness edit (general)
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
        # for fallback path we already computed 'correct' above; keep it if provided
        if comp_state.get("correct") is not None:
            fp["correct_flags"] = comp_state.get("correct")

    if st.button("Submit", type="primary"):
        if fp["correct_flags"] is None:
            got = [ (x or "") for x in fp["_fills"] ]
            fp["correct_flags"] = [ a.strip().lower() == g.strip().lower() for a, g in zip(ans, got) ]
        # Go to review screen
        fp["stage"] = "cloze_specific_review" if is_specific else "cloze_general_review"
        st.rerun()

def _render_cloze_review_table(ans: List[str], fills: List[Optional[str]]):
    """Show each blank with your answer vs correct, with green/red borders."""
    for i, a in enumerate(ans):
        you = (fills[i] or "").strip()
        ok = (you.lower() == a.strip().lower())
        klass = "ok" if ok else "bad"
        st.markdown(f'<div class="blank-row {klass}">', unsafe_allow_html=True)
        st.markdown(f'<div class="blank-lab">Blank {i+1}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="blank-you"><b>Your answer:</b> {you if you else "<i>(empty)</i>"}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="blank-correct"><b>Correct:</b> {a}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def _stage_cloze_review(is_specific: bool):
    fp = st.session_state._fp
    segs, ans, fills = fp["_segs"], fp["_ans"], fp["_fills"]
    flags = fp["correct_flags"] or [False]*len(ans)
    c = sum(flags); total = len(flags) or 1
    bad_pct = int((total - c) / total * 100)
    frame_class = "good" if c == total else "mixed"
    st.markdown(f'<div class="global-frame {frame_class}" style="--badpct:{bad_pct}%"></div>', unsafe_allow_html=True)

    st.subheader(f"Cloze score: {c}/{total}")
    klass = "good" if c == total else "mixed"
    st.markdown(
        f'<div class="cloze-card {klass}" style="--badpct:{bad_pct}%">'
        f'<span class="hl">Review each blank:</span> green = correct, red = incorrect.'
        f'</div>', unsafe_allow_html=True
    )
    _render_cloze_review_table(ans, fills)

    fp["cloze_rating"] = st.slider("Rate your understanding after this cloze (0–10)", 0, 10, 7,
                                   key=f"rate_cloze_{'spec' if is_specific else 'gen'}")
    cols = st.columns([1,1,1])
    with cols[1]:
        if st.button("Continue", type="primary", use_container_width=True):
            fp["ratings"].append({"stage": "cloze_specific" if is_specific else "cloze_general",
                                  "score": fp["cloze_rating"], "raw": f"{c}/{total}"})
            # Next goes to weakness review screen
            fp["stage"] = "weakness_review_specific" if is_specific else "weakness_review_general"
            st.rerun()

def _ai_weak_strengths_stub(context: str) -> Dict[str, List[str]]:
    """Very concise AI-like suggestions (deterministic)."""
    return {
        "weak": ["term precision", "linking steps", "edge cases"][:3],
        "strong": ["structure", "clear assumptions"][:2]
    }

def _stage_weakness_review_general():
    fp = st.session_state._fp
    cur = fp["cur_general"] or "this topic"
    st.subheader("Weakness review")
    stub = _ai_weak_strengths_stub(cur)
    left, right = st.columns(2)
    with left:
        st.markdown("**AI Weaknesses (edit):**")
        wk_text = st.text_area("weak", value="; ".join(stub["weak"]), key="wk_rev_gen", label_visibility="collapsed")
    with right:
        st.markdown("**AI Strengths (edit):**")
        stg_text = st.text_area("strong", value="; ".join(stub["strong"]), key="stg_rev_gen", label_visibility="collapsed")

    st.caption("Focus goes to your specific weaknesses first; or move on if satisfied.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔎 Focus this (specifics)", type="primary", use_container_width=True):
            fp["reports"]["weaknesses"] = wk_text
            fp["reports"]["strengths"] = stg_text
            fp["stage"] = "report_specific"
            st.rerun()
    with c2:
        if st.button("➡️ Move on", use_container_width=True):
            fp["stage"] = "fp_more"
            st.rerun()

def _stage_report_specific():
    fp = st.session_state._fp
    cur = fp["cur_general"] or "this topic"
    st.caption(f"Add specific weaknesses for: **{cur}**")
    specs_text = st.text_input("Specific weaknesses (semicolon-separated)", value="",
                               key=f"specs_{cur}", placeholder="e.g., reverse osmosis; boundary conditions")
    if st.button("Continue", type="primary"):
        specs = [w.strip() for w in (specs_text or "").split(";") if w.strip()]
        fp["spec_map"][cur] = specs[:]
        fp["spec_queue"] = specs[:]
        fp["cur_specific"] = fp["spec_queue"].pop(0) if fp["spec_queue"] else None
        fp["follow_qs"] = _followup_questions_for(fp["cur_specific"] or cur)
        fp["follow_idx"] = 0
        fp["stage"] = "fp_specific_q" if fp["cur_specific"] else "fp_more"
        st.rerun()

def _stage_fp_specific_question(s, m, iq, dotpoint):
    """One question at a time; model answer + rating on submit."""
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
        submitted = st.form_submit_button("Submit", type="primary")

    if submitted:
        # Show model answer + rating immediately
        st.markdown(_model_answer(dotpoint, s, mode="specific"), unsafe_allow_html=True)
        fp["spec_q_rating"] = st.slider("Rate this answer (0–10)", 0, 10, 7, key=f"spec_q_rate_{idx}")
        if st.button("Next", type="primary"):
            fp["ratings"].append({"stage":"fp_specific_q", "q_index": idx, "score": fp["spec_q_rating"]})
            fp["follow_idx"] = idx + 1
            st.rerun()
        return

def _stage_fp_specific_review():
    # (not used; we do review inline in _stage_fp_specific_question)
    pass

def _stage_cloze_specific():
    _stage_cloze(is_specific=True)

def _stage_weakness_review_specific():
    fp = st.session_state._fp
    cur = fp["cur_specific"] or fp["cur_general"] or "this topic"
    st.subheader("Weakness review (specific)")
    stub = _ai_weak_strengths_stub(cur)
    left, right = st.columns(2)
    with left:
        wk_text = st.text_area("weak", value="; ".join(stub["weak"]), key="wk_rev_spec", label_visibility="collapsed")
    with right:
        stg_text = st.text_area("strong", value="; ".join(stub["strong"]), key="stg_rev_spec", label_visibility="collapsed")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Continue specifics", type="primary", use_container_width=True):
            # More specifics in queue?
            if st.session_state._fp["spec_queue"]:
                st.session_state._fp["cur_specific"] = st.session_state._fp["spec_queue"].pop(0)
                st.session_state._fp["follow_qs"] = _followup_questions_for(st.session_state._fp["cur_specific"])
                st.session_state._fp["follow_idx"] = 0
                st.session_state._fp["stage"] = "fp_specific_q"
            else:
                st.session_state._fp["stage"] = "fp_more"
            st.rerun()
    with c2:
        if st.button("Move on", use_container_width=True):
            st.session_state._fp["stage"] = "fp_more"
            st.rerun()

def _stage_cloze_specific_review():
    _stage_cloze_review(is_specific=True)

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

# ============== Helpers ==============
def _followup_questions_for(weakness: str) -> List[str]:
    w = weakness or "this topic"
    # One-at-a-time prompts
    return [
        f"Explain {w} in your own words, then give a simple example.",
        f"List two common mistakes in {w} and how to avoid them."
    ]
