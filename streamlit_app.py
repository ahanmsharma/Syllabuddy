import json
import os
import re
import random
from typing import Dict, List, Optional, Tuple
import streamlit as st

# ================== FLAGS ==================
FORCE_PLACEHOLDERS = True  # keep AI off while you refine UX

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
      .thin-divider { border-top: 1px solid #e6e6e6; margin: .7rem 0; }

      /* Cloze inline styling */
      .cloze-wrap { font-size: 1.12rem; line-height: 1.7; display: flex; flex-wrap: wrap; align-items: center; }
      .seg { margin-right: .25rem; }
      .blank {
        display:inline-flex; align-items:center; justify-content:center;
        min-width: 8ch; padding: 2px 8px; border-bottom: 2px solid #9aa0a6;
        margin: 0 .25rem; border-radius: 6px;
        background: #fafafa;
        transition: background .15s ease, border-color .15s ease;
      }
      .blank.filled { background: #eef7ff; border-color: #5b9bff; }
      .blank.correct { border-color: #16a34a; }
      .blank.wrong { border-color: #dc2626; }
      .tick { color: #16a34a; font-weight: 700; margin-left: 6px; }
      .cross { color: #dc2626; font-weight: 700; margin-left: 6px; }

      .chips { margin-top: .5rem; display:flex; flex-wrap: wrap; gap: 8px; }
      .chip {
        display:inline-flex; align-items:center; gap:6px;
        border:1px solid #d0d7de; border-radius: 999px;
        padding: 4px 10px; cursor:pointer; user-select: none; background: #fff;
      }
      .chip:hover { background: #f7fafc; }

      /* Feedback border container */
      .feedback { border: 3px solid transparent; border-radius: 12px; padding: 12px; }
      .feedback.good { animation: flashGreen 2.2s ease 1; border-color: #22c55e; }
      .feedback.mixed { border-image-slice: 1; border-width: 3px; border-style: solid;
                        border-image-source: linear-gradient(90deg, #dc2626 var(--badpct,30%), #22c55e var(--badpct,30%));
                        animation: flashMix 2.2s ease 1; }
      @keyframes flashGreen { 0%{box-shadow:0 0 0 0 rgba(34,197,94,.35)} 60%{box-shadow:0 0 0 6px rgba(34,197,94,.0)} 100%{box-shadow:none} }
      @keyframes flashMix   { 0%{box-shadow:0 0 0 0 rgba(220,38,38,.25)} 60%{box-shadow:0 0 0 6px rgba(220,38,38,.0)} 100%{box-shadow:none} }

      .rating-row { margin-top: .4rem; }
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

# ================== OPTIONAL OPENAI (disabled while FORCE_PLACEHOLDERS) ==================
def _safe_secret(key: str) -> Optional[str]:
    try: return st.secrets[key]
    except Exception: return None

def get_openai_client():
    if FORCE_PLACEHOLDERS: return None, None, None
    api_key = os.getenv("OPENAI_API_KEY") or _safe_secret("OPENAI_API_KEY")
    if not api_key: return None, None, None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        return client, "gpt-5-mini", "gpt-5-nano"
    except Exception:
        return None, None, None

client, MODEL_MINI, MODEL_NANO = get_openai_client()

def chat_json(messages, model: str, temperature: float = 0.2) -> Dict:
    if client is None: return {}
    try:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            if lines and lines[0].lower().startswith("json"): lines = lines[1:]
            text = "\n".join(lines).strip()
        return json.loads(text)
    except Exception:
        return {}

# ================== HELPERS: FP / Lists / Cloze ==================
def heuristic_fp(dotpoint: str) -> str:
    return (
        f"From first principles, derive/explain the mechanism for “{dotpoint}”, "
        f"state key assumptions and limiting cases, and justify each step with causal reasoning."
    )

def generate_fp_question(dotpoint: str) -> str:
    if FORCE_PLACEHOLDERS or client is None:
        return heuristic_fp(dotpoint)
    payload = chat_json([
        {"role":"system","content":"Return JSON only."},
        {"role":"user","content":f"""One first-principles question. Dotpoint: "{dotpoint}"
- Probe mechanism/derivation/causal chain
- Mention assumptions or limits if relevant
- One sentence; exam-ready
JSON: {{"question":"..."}}"""}], model=MODEL_MINI, temperature=0.2)
    return payload.get("question") or heuristic_fp(dotpoint)

def suggested_lists(dotpoint: str, user_answer: str) -> Dict:
    if FORCE_PLACEHOLDERS or client is None:
        return {"suggested_weaknesses":["definition gap","unclear mechanism","weak example"],
                "suggested_strengths":["correct terms","coherent structure"]}
    payload = chat_json([
        {"role":"system","content":"Return JSON only. ≤5 items per list, 2–6 words each."},
        {"role":"user","content":f'Dotpoint: "{dotpoint}" Student answer: "{user_answer}" JSON: {{"suggested_weaknesses":["..."],"suggested_strengths":["..."]}}'}],
        model=MODEL_NANO, temperature=0.2)
    if not payload: return {"suggested_weaknesses":["definition gap"], "suggested_strengths":["clear terms"]}
    payload["suggested_weaknesses"] = payload.get("suggested_weaknesses", [])[:5]
    payload["suggested_strengths"]  = payload.get("suggested_strengths",  [])[:5]
    return payload

BLANK_PATTERN = re.compile(r"\[\[(.+?)\]\]")

def placeholder_cloze(level:int=0) -> str:
    if level==0:
        return "Diffusion is net movement from [[higher concentration]] to [[lower concentration]] across a [[semi-permeable membrane]]."
    return "Facilitated diffusion uses [[membrane proteins]] to move molecules down a [[concentration gradient]] without [[ATP hydrolysis]]."

def generate_cloze(dotpoint: str, weakness: str, specificity: int = 0) -> str:
    if FORCE_PLACEHOLDERS or client is None:
        return placeholder_cloze(specificity)
    payload = chat_json([
        {"role":"system","content":"Return JSON only."},
        {"role":"user","content":f"""Dotpoint: "{dotpoint}"
Target weakness: "{weakness}"
Specificity: {specificity}  # 0 broad, 1 narrower
One cloze sentence with 1–4 [[blanks]]; short and precise.
JSON: {{"cloze":"..."}}"""}], model=MODEL_MINI, temperature=0.2)
    return (payload.get("cloze") or placeholder_cloze(specificity)).strip()

def parse_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_PATTERN.findall(cloze)
    parts = BLANK_PATTERN.split(cloze)  # [seg0, ans1, seg1, ans2, seg2...]
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
    st.session_state.last_cloze_result = None
    st.session_state.inline_fills = {}   # blank_index -> token string
    st.session_state.bank_tokens = []    # available chips
    st.session_state.nav_guard = None    # {"target": (subject,module,iq,dotpoint)}

if "stage" not in st.session_state:
    reset_flow()

# ================== SIDEBAR NAV + GUARD ==================
with st.sidebar:
    st.header("Navigation")
    subject = st.selectbox("Subject", list(syllabus.keys()), key="nav_subj")
    module  = st.selectbox("Module",  list(syllabus[subject].keys()), key="nav_mod")
    iq      = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()), key="nav_iq")
    chosen_dp = st.radio("Dotpoint", syllabus[subject][module][iq], key="nav_dp")

    current_dp = st.session_state.get("selected_dp")
    target_tuple = (subject, module, iq, chosen_dp)

    # If attempting to change away from current dp mid-activity, raise guard
    if current_dp is not None and current_dp != target_tuple and st.session_state.stage in ("fp","report","cloze","post_cloze","fp_followups"):
        st.session_state.nav_guard = {"target": target_tuple}
    else:
        # set current selection (first time or same dp)
        st.session_state.selected_dp = target_tuple

# Guard UI on main area if pending navigation
if st.session_state.nav_guard:
    st.markdown('<div class="guard">', unsafe_allow_html=True)
    st.markdown("### Heads up")
    st.write("You’re leaving this dotpoint before finishing. What should I do?")
    colg = st.columns([1,1,1])
    with colg[0]:
        if st.button("Save as incomplete (SRS next)", use_container_width=True):
            # TODO: record incomplete + schedule in SRS
            reset_flow()
            st.session_state.selected_dp = st.session_state.nav_guard["target"]
            st.session_state.nav_guard = None
            st.rerun()
    with colg[1]:
        rating_tmp = st.slider("Mark complete (rate 0–10)", 0, 10, 7)
        if st.button("Save & schedule", use_container_width=True):
            # TODO: record complete+rating and schedule in SRS
            reset_flow()
            st.session_state.selected_dp = st.session_state.nav_guard["target"]
            st.session_state.nav_guard = None
            st.rerun()
    with colg[2]:
        if st.button("Cancel", use_container_width=True):
            # cancel navigation attempt
            st.session_state.nav_guard = None
            # revert sidebar radios to current selection
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

# ================== MAIN TOP ==================
st.markdown(f'<div class="dotpoint">{dotpoint}</div>', unsafe_allow_html=True)

# ================== STAGES ==================
# ----- FP -----
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        st.session_state.fp_q = generate_fp_question(dotpoint)
    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form(key="fp_form", clear_on_submit=False):
        blurt = st.text_area("Your answer", key="fp_blurt", height=360, label_visibility="collapsed", placeholder="Type your answer here…")
        submit = st.form_submit_button("Submit")
    if submit:
        st.session_state.user_blurt = blurt or ""
        sug = suggested_lists(dotpoint, st.session_state.user_blurt)
        st.session_state.reports = {"weaknesses":"; ".join(sug.get("suggested_weaknesses",[])),
                                    "strengths":"; ".join(sug.get("suggested_strengths",[]))}
        st.session_state.stage = "report"
        st.rerun()

# ----- REPORT -----
elif st.session_state.stage == "report":
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="box-label">AI Weakness report</div>', unsafe_allow_html=True)
        wk = st.text_area("Weakness report", value=st.session_state.reports["weaknesses"], key="wk_edit", height=260, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="box-label">AI Strength report</div>', unsafe_allow_html=True)
        stg = st.text_area("Strength report", value=st.session_state.reports["strengths"], key="stg_edit", height=260, label_visibility="collapsed")

    mid = st.columns(3)[1]
    with mid:
        if st.button("Continue", use_container_width=True):
            wl = [w.strip() for w in (wk or "").split(";") if w.strip()]
            st.session_state.weak_list = wl[:5]
            st.session_state.reports["weaknesses"] = "; ".join(st.session_state.weak_list)
            st.session_state.reports["strengths"] = stg or ""
            st.session_state.weak_index = 0
            st.session_state.current_cloze = None
            st.session_state.cloze_specificity = 0
            st.session_state.inline_fills = {}
            st.session_state.bank_tokens = []
            st.session_state.stage = "cloze" if st.session_state.weak_list else "fp"
            st.rerun()

# ----- CLOZE (inline blanks + click-to-place chips, single bottom submit) -----
elif st.session_state.stage == "cloze":
    if st.session_state.weak_index >= len(st.session_state.weak_list):
        st.success("All listed weaknesses processed. (Next: FP follow-ups / rating / exam.)")
        st.session_state.stage = "fp"
        st.rerun()

    current_weak = st.session_state.weak_list[st.session_state.weak_index]
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = generate_cloze(dotpoint, current_weak, st.session_state.cloze_specificity)
        # seed tokens for this cloze
        _, answers = parse_cloze(st.session_state.current_cloze)
        st.session_state.bank_tokens = random.sample(answers, k=len(answers))  # scramble
        st.session_state.inline_fills = {i+1: "" for i in range(len(answers))}

    # Inline rendering
    segments, answers = parse_cloze(st.session_state.current_cloze)
    st.markdown(f'<div class="box-label">Targeting: {current_weak}</div>', unsafe_allow_html=True)
    with st.container(border=True, key=f"clozebox_{st.session_state.weak_index}"):
        st.markdown('<div class="cloze-wrap">', unsafe_allow_html=True)

        # Build a row of alternating segment text and inline blanks
        # Use columns in small chunks to keep things inline visually
        for i, _ans in enumerate(answers, start=1):
            # segment text
            st.write(segments[i-1], unsafe_allow_html=False)
            # inline blank (display current fill)
            current_val = st.session_state.inline_fills.get(i, "")
            disp = current_val if current_val else " "
            colb = st.columns([1])[0]
            # show as markdown span with CSS; below it, tiny buttons to clear/fill are in chips area
            st.markdown(f'<span class="blank {"filled" if current_val else ""}">{disp}</span>', unsafe_allow_html=True)
        # trailing segment
        st.write(segments[-1], unsafe_allow_html=False)
        st.markdown('</div>', unsafe_allow_html=True)

        # Chips below (click to place into next empty or re-add from blanks)
        st.markdown('<div class="chips">', unsafe_allow_html=True)
        chip_cols = st.columns(min(6, max(1, len(st.session_state.bank_tokens))))
        for idx, tok in enumerate(st.session_state.bank_tokens):
            with chip_cols[idx % len(chip_cols)]:
                if st.button(tok, key=f"chip_{idx}", use_container_width=False):
                    # place into next empty blank
                    for j in range(1, len(answers)+1):
                        if not st.session_state.inline_fills[j]:
                            st.session_state.inline_fills[j] = tok
                            # remove from bank
                            st.session_state.bank_tokens.pop(idx)
                            st.rerun()
                            break
        st.markdown('</div>', unsafe_allow_html=True)

        # Let user “drag off into nothing”: click a filled blank to return token to bank
        # Render small “clear” buttons inline for blanks (simulating remove)
        clear_cols = st.columns(len(answers))
        for j in range(1, len(answers)+1):
            with clear_cols[j-1]:
                if st.session_state.inline_fills[j]:
                    if st.button(f"↩︎ {st.session_state.inline_fills[j]}", key=f"clr_{j}", help="Remove from blank"):
                        st.session_state.bank_tokens.append(st.session_state.inline_fills[j])
                        st.session_state.inline_fills[j] = ""
                        st.rerun()

        # Single submit at bottom
        submitted = st.button("Submit", type="primary", use_container_width=True)

    if submitted:
        got = [st.session_state.inline_fills[i] for i in range(1, len(answers)+1)]
        correct_flags = [a.strip().lower()==g.strip().lower() for a,g in zip(answers, got)]
        num_correct = sum(correct_flags)
        st.session_state.last_cloze_result = (num_correct, len(answers))

        # Visual correctness overlay (✓/✗ next to each filled blank)
        # Re-render the sentence with correctness marks
        bad_pct = 0 if len(answers)==0 else int((len(answers)-num_correct)/len(answers)*100)
        container_class = "good" if num_correct==len(answers) else "mixed"
        st.markdown(f'<div class="feedback {container_class}" style="--badpct:{bad_pct}%">', unsafe_allow_html=True)

        st.markdown('<div class="cloze-wrap">', unsafe_allow_html=True)
        for i, ans in enumerate(answers, start=1):
            st.write(segments[i-1], unsafe_allow_html=False)
            g = st.session_state.inline_fills[i]
            ok = ans.strip().lower()==g.strip().lower()
            mark = '<span class="tick">✓</span>' if ok else '<span class="cross">✗</span>'
            klass = "blank filled " + ("correct" if ok else "wrong")
            show = g if g else " "
            st.markdown(f'<span class="{klass}">{show}{mark}</span>', unsafe_allow_html=True)
        st.write(segments[-1], unsafe_allow_html=False)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Move to post-cloze (rating + add weaknesses)
        st.session_state.stage = "post_cloze"
        st.rerun()

# ----- POST-CLOZE (rating + add weaknesses -> branch) -----
elif st.session_state.stage == "post_cloze":
    if st.session_state.last_cloze_result:
        c, t = st.session_state.last_cloze_result
        st.info(f"Cloze score: {c}/{t}")

    colA, colB = st.columns([1,1])
    with colA:
        rating = st.slider("Rate your understanding (0–10)", 0, 10, 6, key="cloze_rating")
    with colB:
        more_w = st.text_input("Add more weaknesses (semicolon-separated):", key="more_wk")

    go = st.columns(3)[1].button("Continue", use_container_width=True)
    if go:
        # Merge in new weaknesses, dedupe, cap 5
        add_list = [w.strip() for w in (more_w or "").split(";") if w.strip()]
        merged = st.session_state.weak_list[:]
        for w in add_list:
            if w not in merged:
                merged.append(w)
        st.session_state.weak_list = merged[:5]

        if rating <= 6:
            # another, more specific cloze on same weakness
            st.session_state.cloze_specificity = min(1, st.session_state.cloze_specificity + 1)
            st.session_state.current_cloze = None
            st.session_state.inline_fills = {}
            st.session_state.bank_tokens = []
            st.session_state.stage = "cloze"
            st.rerun()
        else:
            # follow-up FP questions for this weakness (placeholder)
            st.session_state.cloze_specificity = 0
            st.session_state.current_cloze = None
            st.session_state.stage = "fp_followups"
            st.rerun()

# ----- FP FOLLOW-UPS (placeholder text) -----
elif st.session_state.stage == "fp_followups":
    current_weak = st.session_state.weak_list[st.session_state.weak_index] if st.session_state.weak_list else "this topic"
    st.markdown(f"**Follow-up first-principles questions for:** _{current_weak}_")
    qlist = [
        f"Derive the governing relationship for {current_weak}, starting only from definitions and conservation principles.",
        f"Explain how {current_weak} behaves under an extreme boundary case, and justify each step of your reasoning."
    ]
    for q in qlist: st.write("• " + q)

    if st.button("Next weakness"):
        st.session_state.weak_index += 1
        st.session_state.current_cloze = None
        st.session_state.inline_fills = {}
        st.session_state.bank_tokens = []
        st.session_state.cloze_specificity = 0
        if st.session_state.weak_index < len(st.session_state.weak_list):
            st.session_state.stage = "cloze"
        else:
            # TODO: overall dotpoint rating + exam mode handoff
            st.success("All weaknesses cleared. (Next: overall rating / exam mode).")
            st.session_state.stage = "fp"
        st.rerun()

# ----- Fallback -----
else:
    st.session_state.stage = "fp"
    st.rerun()
