from __future__ import annotations
import os
import re
import random
from typing import Dict, List, Tuple, Optional

import streamlit as st

# ================= Theme-aware CSS (dark-mode safe) =================
FP_CSS = """
<style>
:root{
  --bg:#ffffff; --text:#111827; --muted:#4b5563;
  --ok:#16a34a; --bad:#dc2626; --border:#e5e7eb;
  --card:#ffffff; --cardTint:#f8fafc; --inputBg:#ffffff; --inputText:#111827;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0b1220; --text:#e5e7eb; --muted:#94a3b8;
    --ok:#22c55e; --bad:#ef4444; --border:#334155;
    --card:#0f172a; --cardTint:#101826;
    --inputBg:#0b1220; --inputText:#e5e7eb;
  }
}

/* make our containers readable in dark */
.fp-card, .cloze-card, .ai-box, .weak-box {
  border:2px solid var(--border); border-radius:12px; padding:12px;
  background:var(--card); color:var(--text);
}

.dp-title{ font-weight:800; font-size:1.14rem; margin:.25rem 0 .75rem 0; color:var(--text); }
.subtle{ color:var(--muted); }

textarea, input[type="text"]{
  background: var(--inputBg) !important;
  color: var(--inputText) !important;
  border:1px solid var(--border) !important;
}

/* Global full-page frame after cloze submit */
.global-frame{
  position:fixed; inset:0; pointer-events:none; z-index:9999;
  border:6px solid transparent; border-radius:0;
}
.global-frame.good{ border-color: var(--ok); }
.global-frame.mixed{
  border-image-slice:1; border-style:solid; border-width:6px;
  border-image-source: linear-gradient(90deg, var(--bad) var(--badpct,30%), var(--ok) var(--badpct,30%));
}

/* Per-blank inline review (fallback/typed mode) */
.blank-row{
  border:2px solid var(--border); border-radius:10px; padding:10px; margin-bottom:10px;
}
.blank-row.ok{ border-color: var(--ok); }
.blank-row.bad{ border-color: var(--bad); }
.blank-lab{ font-weight:700; color:var(--muted); }
.blank-you{ margin-top:4px; }
.blank-correct{ margin-top:2px; color:var(--muted); }

/* Section headers on page */
.section-title { font-weight:800; margin:10px 0 6px 0; color:var(--text); }
</style>
"""
st.markdown(FP_CSS, unsafe_allow_html=True)

# ================= Public entrypoints =================
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
    """Single-screen FP engine for current dotpoint; keeps review inline."""
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
    elif stage == "cloze_general":
        _stage_cloze(is_specific=False, subject=s, dotpoint=dotpoint)
    elif stage == "cloze_specific":
        _stage_cloze(is_specific=True, subject=s, dotpoint=dotpoint)
    elif stage == "fp_specific_q":
        _stage_fp_specific_question(s, m, iq, dotpoint)
    elif stage == "fp_more":
        _stage_fp_more()
    elif stage == "decision":
        _stage_decision()
    else:
        st.session_state._fp["stage"] = "fp_general"
        st.rerun()

# ================= Internal state/model =================
def _reset_all():
    st.session_state._fp = {
        "queue": [], "q_idx": 0,
        "stage": "fp_general",

        # FP general
        "fp_q": None,
        "user_blurt": "",
        "fp_general_model_answer": None,
        "fp_general_rating": None,
        "fp_ai_wk": "",
        "fp_ai_st": "",
        "direct_exam": False,

        # general weaknesses list
        "general_list": [],
        "general_idx": 0,
        "cur_general": None,

        # specifics
        "spec_map": {},       # general -> [specifics]
        "spec_queue": [],
        "cur_specific": None,

        # follow-ups
        "follow_qs": [],
        "follow_idx": 0,

        # cloze
        "current_cloze": None,
        "cloze_specificity": 0,   # 0=general 1=specific
        "_segs": None, "_ans": None, "_bank": None, "_fills": None,
        "correct_flags": None,
        "cloze_score": None,
        "cloze_rating": None,
        "cloze_ai_wk": "",
        "cloze_ai_st": "",

        "ratings": [],
    }

def _reset_for_current_dp():
    fp = st.session_state._fp
    fp.update({
        "stage": "fp_general",
        "fp_q": None,
        "user_blurt": "",
        "fp_general_model_answer": None,
        "fp_general_rating": None,
        "fp_ai_wk": "", "fp_ai_st": "",
        "direct_exam": False,

        "general_list": [], "general_idx": 0, "cur_general": None,
        "spec_map": {}, "spec_queue": [], "cur_specific": None,
        "follow_qs": [], "follow_idx": 0,

        "current_cloze": None, "cloze_specificity": 0,
        "_segs": None, "_ans": None, "_bank": None, "_fills": None,
        "correct_flags": None,
        "cloze_score": None, "cloze_rating": None,
        "cloze_ai_wk": "", "cloze_ai_st": "",
    })

def _guard_queue():
    q = st.session_state._fp["queue"]
    if not q: return
    st.session_state._fp["q_idx"] = max(0, min(st.session_state._fp["q_idx"], len(q)-1))

def _current_dp() -> Optional[Tuple[str,str,str,str]]:
    q = st.session_state._fp["queue"]
    if not q: return None
    return q[st.session_state._fp["q_idx"]]

# ================= Prompts / Answers / AI =================
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
    """Placeholder model answer (deterministic)."""
    if mode == "specific":
        return (f"**Model answer (specific):** Define the sub-idea precisely, outline the stepwise causal chain, "
                f"and connect it back to “{dotpoint}”. Include one tight micro-example and the key assumption.")
    subj = (subject or "").lower()
    if subj in ("physics", "chemistry"):
        return (f"**Model answer:** Start from definitions and conservation principles. Derive the governing relation for "
                f"“{dotpoint}”, justify each step, and note limiting cases.")
    if subj == "biology":
        return (f"**Model answer:** Describe structures involved, causal mechanism, and necessary conditions for "
                f"“{dotpoint}”. Predict outcomes if a condition is removed.")
    return (f"**Model answer:** Define the principle, develop it logically, and show a compact example for “{dotpoint}”.")    

def _ai_weak_strengths(text: str) -> Dict[str,List[str]]:
    """
    Try gpt-5-nano for 3 weaknesses + 2 strengths (semicolon short);
    fallback to a simple deterministic stub if no key.
    """
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
    try:
        from openai import OpenAI  # OpenAI v1
        if not api_key:
            raise RuntimeError("no key")
        client = OpenAI(api_key=api_key)
        prompt = (
            "Summarize the *top 3 weaknesses* and *top 2 strengths* in this answer. "
            "Return as 'weak: w1; w2; w3' and 'strong: s1; s2' with short phrases.\n\n"
            f"Answer:\n{text}\n"
        )
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=120,
        )
        out = resp.choices[0].message.content.strip()
        weak, strong = [], []
        for line in out.splitlines():
            if line.lower().startswith("weak"):
                weak = [p.strip(" ;") for p in line.split(":",1)[1].split(";") if p.strip()]
            if line.lower().startswith("strong"):
                strong = [p.strip(" ;") for p in line.split(":",1)[1].split(";") if p.strip()]
        if not weak: weak = ["term precision","linking steps","edge cases"]
        if not strong: strong = ["structure","clear assumptions"]
        return {"weak": weak[:3], "strong": strong[:2]}
    except Exception:
        return {"weak": ["term precision","linking steps","edge cases"],
                "strong": ["structure","clear assumptions"]}

# ================= Cloze helpers =================
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
    parts = _BLANK_RE.split(cloze)  # [seg0, ans1, seg1, ans2, seg2, ...]
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

def _render_cloze(segments, answers, fills, bank, key, show_feedback=False, page_frame="none", bad_pct=30):
    comp = _get_component()
    if comp:
        # Uses your previous DnD props; feedback stays on same page.
        return comp(
            segments=segments,
            answers=answers,
            initialBank=bank,
            initialFills=fills,
            showFeedback=show_feedback,
            pageFrame=page_frame,
            badPct=bad_pct,
            key=key,
            default=None,
        )
    # Fallback typed blanks (keeps inline review)
    new_fills = list(fills)
    for i in range(len(answers)):
        st.write(segments[i])
        new_fills[i] = st.text_input(f"Blank {i+1}", value=new_fills[i] or "", key=f"{key}_txt_{i}")
    st.write(segments[-1])
    flags = [(a.strip().lower() == (new_fills[i] or "").strip().lower()) for i, a in enumerate(answers)]
    return {"bank": bank, "fills": new_fills, "correct": flags}

def _render_fallback_review(ans: List[str], fills: List[Optional[str]]):
    for i, a in enumerate(ans):
        yours = (fills[i] or "").strip()
        ok = (yours.lower() == a.strip().lower())
        klass = "ok" if ok else "bad"
        st.markdown(f'<div class="blank-row {klass}">', unsafe_allow_html=True)
        st.markdown(f'<div class="blank-lab">Blank {i+1}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="blank-you"><b>Your answer:</b> {yours if yours else "<i>(empty)</i>"}', unsafe_allow_html=True)
        st.markdown(f'<div class="blank-correct"><b>Correct:</b> {a}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ================= Stages =================
def _stage_fp_general(s, m, iq, dotpoint):
    fp = st.session_state._fp
    if not fp["fp_q"]:
        fp["fp_q"] = _smart_fp(dotpoint, s)

    # FP prompt
    st.markdown('<div class="fp-card">', unsafe_allow_html=True)
    st.write(fp["fp_q"])
    with st.form("fp_general_form"):
        blurt = st.text_area("Your answer", key="fp_blurt", height=280, placeholder="Type your answer here…")
        direct_exam = st.checkbox("Skip to Exam Mode (optional)", value=False)
        submitted = st.form_submit_button("Submit", type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        fp["user_blurt"] = blurt or ""
        fp["direct_exam"] = bool(direct_exam)
        # Inline model answer + rating + AI weaknesses (ON THE SAME PAGE)
        model = _model_answer(dotpoint, s, "general")
        st.markdown('<div class="ai-box">', unsafe_allow_html=True)
        st.markdown(model, unsafe_allow_html=True)
        fp["fp_general_rating"] = st.slider("Rate your understanding (0–10)", 0, 10, 6, key="rate_fp_gen")
        ai = _ai_weak_strengths(fp["user_blurt"])
        fp["fp_ai_wk"] = "; ".join(ai["weak"])
        fp["fp_ai_st"] = "; ".join(ai["strong"])
        st.markdown('</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Focus these weaknesses next", type="primary", use_container_width=True, key="fp_next_focus"):
                # Build initial general list from AI (editable later via cloze page box)
                fp["general_list"] = [w.strip() for w in fp["fp_ai_wk"].split(";") if w.strip()][:5]
                fp["general_idx"] = 0
                fp["cur_general"] = fp["general_list"][0] if fp["general_list"] else None
                fp["ratings"].append({"stage":"fp_general", "score": fp["fp_general_rating"]})
                if fp["direct_exam"]:
                    st.info("Exam Mode placeholder (HSC-style questions + sample answers).")
                    if st.button("Return to FP"):
                        fp["direct_exam"] = False
                        st.rerun()
                    return
                fp["stage"] = "cloze_general" if fp["cur_general"] else "fp_more"
                st.rerun()
        with c2:
            if st.button("Move on", use_container_width=True, key="fp_next_moveon"):
                fp["ratings"].append({"stage":"fp_general", "score": fp["fp_general_rating"]})
                if fp["direct_exam"]:
                    st.info("Exam Mode placeholder (HSC-style questions + sample answers).")
                    if st.button("Return to FP"):
                        fp["direct_exam"] = False
                        st.rerun()
                    return
                # go to general cloze with empty/general tag
                fp["general_list"] = [fp["fp_ai_wk"].split(";")[0]] if fp["fp_ai_wk"] else []
                fp["general_idx"] = 0
                fp["cur_general"] = fp["general_list"][0] if fp["general_list"] else None
                fp["stage"] = "cloze_general" if fp["cur_general"] else "fp_more"
                st.rerun()

def _stage_cloze(is_specific: bool, subject: str, dotpoint: str):
    """All cloze review/feedback stays on THIS page after Submit."""
    fp = st.session_state._fp

    # Prepare cloze once per stage
    if not fp["current_cloze"]:
        txt = _placeholder_cloze(level=1 if is_specific else 0)
        segs, ans = _split_cloze(txt)
        bank = ans[:]; random.shuffle(bank)
        fp.update({
            "current_cloze": txt, "_segs": segs, "_ans": ans, "_bank": bank,
            "_fills": [None]*len(ans), "correct_flags": None,
            "cloze_score": None, "cloze_rating": None, "cloze_ai_wk": "", "cloze_ai_st": ""
        })

    segs, ans, bank, fills = fp["_segs"], fp["_ans"], fp["_bank"], fp["_fills"]

    target_label = (fp["cur_specific"] if is_specific else (fp["cur_general"] or "this topic"))
    st.caption(f"Targeting: {target_label} ({'specific' if is_specific else 'general'})")

    # Compute frame/feedback values if already graded
    page_frame = "none"
    bad_pct = 30
    if fp["correct_flags"] is not None:
        c = sum(fp["correct_flags"]); total = len(fp["correct_flags"]) or 1
        bad_pct = int((total - c) / total * 100)
        page_frame = "good" if c == total else "mixed"

    # Render DnD (or fallback) — stays here after submit
    comp_state = _render_cloze(
        segments=segs,
        answers=ans,
        fills=fills,
        bank=bank,
        key=f"dnd_{'spec' if is_specific else 'gen'}_{fp['general_idx']}",
        show_feedback=(fp["correct_flags"] is not None),
        page_frame=page_frame,
        bad_pct=bad_pct,
    )
    if comp_state:
        fp["_bank"]  = comp_state.get("bank", bank)
        fp["_fills"] = comp_state.get("fills", fills)
        if comp_state.get("correct") is not None and fp["correct_flags"] is None:
            fp["correct_flags"] = comp_state.get("correct")

    # Submit grades inline and reveal feedback on THIS page
    submitted = st.button("Submit", type="primary", key=f"submit_{'spec' if is_specific else 'gen'}")
    if submitted and fp["correct_flags"] is None:
        got = [(x or "") for x in fp["_fills"]]
        fp["correct_flags"] = [a.strip().lower() == g.strip().lower() for a, g in zip(ans, got)]
        c = sum(fp["correct_flags"]); total = len(fp["correct_flags"]) or 1
        fp["cloze_score"] = f"{c}/{total}"
        # trigger AI wk/st on the same page (based on got/answers)
        joined = " | ".join(got)
        ai = _ai_weak_strengths(joined)
        fp["cloze_ai_wk"] = "; ".join(ai["weak"])
        fp["cloze_ai_st"] = "; ".join(ai["strong"])
        st.rerun()

    # If graded, draw page border and show review box + rating + wk box
    if fp["correct_flags"] is not None:
        c = sum(fp["correct_flags"]); total = len(fp["correct_flags"]) or 1
        bad_pct = int((total - c) / total * 100)
        frame_class = "good" if c == total else "mixed"
        st.markdown(f'<div class="global-frame {frame_class}" style="--badpct:{bad_pct}%"></div>', unsafe_allow_html=True)

        st.markdown('<div class="cloze-card">', unsafe_allow_html=True)
        st.subheader(f"Cloze score: {fp['cloze_score']}")
        # If we are on fallback typed mode, also show per-blank breakdown:
        if _get_component() is None:
            _render_fallback_review(ans, fp["_fills"])
        st.markdown('</div>', unsafe_allow_html=True)

        # Rating + AI weaknesses/strengths combined (same screen)
        st.markdown('<div class="weak-box">', unsafe_allow_html=True)
        fp["cloze_rating"] = st.slider("Rate your understanding (0–10)", 0, 10, 7,
                                       key=f"rate_cloze_{'spec' if is_specific else 'gen'}")
        colA, colB = st.columns(2)
        with colA:
            wk_edit = st.text_area("AI Weaknesses (edit as needed)",
                                   value=fp["cloze_ai_wk"], key=f"wk_edit_{'spec' if is_specific else 'gen'}",
                                   height=120)
        with colB:
            st_edit = st.text_area("AI Strengths (edit as needed)",
                                   value=fp["cloze_ai_st"], key=f"st_edit_{'spec' if is_specific else 'gen'}",
                                   height=120)
        st.markdown('</div>', unsafe_allow_html=True)

        # Branching buttons
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔎 Focus this (specifics first)" if not is_specific else "Continue specifics",
                         type="primary", use_container_width=True, key=f"focus_{'spec' if is_specific else 'gen'}"):
                st.session_state._fp["ratings"].append({
                    "stage": f"cloze_{'spec' if is_specific else 'gen'}",
                    "score": fp["cloze_rating"],
                    "raw": fp["cloze_score"],
                })
                if not is_specific:
                    # Start specifics based on weakness box
                    specs = [w.strip() for w in (wk_edit or "").split(";") if w.strip()]
                    fp["spec_queue"] = specs[:]
                    fp["cur_specific"] = fp["spec_queue"].pop(0) if fp["spec_queue"] else None
                    fp["follow_qs"] = _followup_questions_for(fp["cur_specific"] or (fp["cur_general"] or "this topic"))
                    fp["follow_idx"] = 0
                    # reset cloze scratch for specific later
                    fp.update({"current_cloze": None, "_segs": None, "_ans": None, "_bank": None, "_fills": None, "correct_flags": None})
                    if fp["cur_specific"]:
                        fp["stage"] = "fp_specific_q"
                    else:
                        # no specific → move on to more FP or next general
                        fp["stage"] = "fp_more"
                else:
                    # Continue specifics if queue remains; else move on
                    if fp["spec_queue"]:
                        fp["cur_specific"] = fp["spec_queue"].pop(0)
                        fp["follow_qs"] = _followup_questions_for(fp["cur_specific"])
                        fp["follow_idx"] = 0
                        fp.update({"current_cloze": None, "_segs": None, "_ans": None, "_bank": None, "_fills": None, "correct_flags": None})
                        fp["stage"] = "fp_specific_q"
                    else:
                        fp["stage"] = "fp_more"
                st.rerun()
        with c2:
            if st.button("➡️ Move on", use_container_width=True, key=f"move_{'spec' if is_specific else 'gen'}"):
                st.session_state._fp["ratings"].append({
                    "stage": f"cloze_{'spec' if is_specific else 'gen'}",
                    "score": fp["cloze_rating"],
                    "raw": fp["cloze_score"],
                })
                if not is_specific:
                    # Skip specifics; next general or finish
                    fp["stage"] = "fp_more"
                else:
                    fp["stage"] = "fp_more"
                st.rerun()

def _stage_fp_specific_question(s, m, iq, dotpoint):
    """One question at a time; inline model answer + rating on submit."""
    fp = st.session_state._fp
    cur_gen = fp["cur_general"] or "this topic"
    cur_spec = fp["cur_specific"] or cur_gen
    qlist = fp.get("follow_qs", [])
    idx = fp.get("follow_idx", 0)
    if idx >= len(qlist):
        # After finishing follow-ups, do a specific cloze
        fp.update({
            "current_cloze": None, "cloze_specificity": 1,
            "_segs": None, "_ans": None, "_bank": None, "_fills": None,
            "correct_flags": None
        })
        fp["stage"] = "cloze_specific"
        st.rerun()
        return

    st.markdown(f"**Specific FP:** _{cur_gen} → {cur_spec}_")
    st.write(qlist[idx])  # question text (not a textbox)

    with st.form(key=f"fp_spec_q_{idx}"):
        ans = st.text_area("Your answer", height=160, key=f"spec_q_ans_{idx}")
        submitted = st.form_submit_button("Submit", type="primary")

    if submitted:
        # Inline model answer + rating on the same page
        st.markdown(_model_answer(dotpoint, s, mode="specific"), unsafe_allow_html=True)
        r = st.slider("Rate this answer (0–10)", 0, 10, 7, key=f"spec_q_rate_{idx}")
        if st.button("Next", type="primary"):
            fp["ratings"].append({"stage":"fp_specific_q", "q_index": idx, "score": r})
            fp["follow_idx"] = idx + 1
            st.rerun()
        return

def _stage_fp_more():
    fp = st.session_state._fp
    st.markdown("**Quick consolidation (optional)**")
    with st.form(key="fp_more_form"):
        st.text_area("Write a one-minute explanation for a friend.", height=120)
        rate = st.slider("Rate your overall understanding (0–10)", 0, 10, 8, key="more_rate")
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        fp["ratings"].append({"stage":"fp_more", "score": rate})
        # Next general in list?
        if fp["general_list"] and fp["general_idx"] < len(fp["general_list"]) - 1:
            fp["general_idx"] += 1
            fp["cur_general"] = fp["general_list"][fp["general_idx"]]
            fp.update({
                "spec_queue": [], "cur_specific": None,
                "follow_qs": [], "follow_idx": 0,
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

# ================= Follow-up generator =================
def _followup_questions_for(weakness: str) -> List[str]:
    w = weakness or "this topic"
    return [
        f"Explain {w} in your own words, then give a simple example.",
        f"List two common mistakes in {w} and how to avoid them."
    ]
