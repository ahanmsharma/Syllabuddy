import json
import os
import re
import random
from typing import Dict, List, Optional, Tuple
import streamlit as st
from streamlit_sortables import sort_items  # NEW: true drag & drop

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

      /* Cloze sentence */
      .cloze-row { display:flex; flex-wrap:wrap; align-items:center; gap:.25rem; font-size:1.12rem; line-height:1.7; }
      .seg { white-space:pre-wrap; }
      .dropzone {
        min-width: 10ch; max-width: 32ch;
        min-height: 2.2rem;
        display:inline-flex; align-items:center; justify-content:center;
        padding: 2px 8px;
        border: 2px dashed #9aa0a6; border-radius: 8px;
        background:#fafafa;
      }
      .dropzone.filled { border-style: solid; background:#eef7ff; border-color:#5b9bff; }
      .dropzone.correct { border-color:#16a34a; }
      .dropzone.wrong { border-color:#dc2626; }
      .bank { display:flex; flex-wrap:wrap; gap:8px; }
      .bank-label { font-size:.95rem; color:#666; margin-bottom:.25rem; }
      .feedback { border: 3px solid transparent; border-radius: 12px; padding: 12px; }
      .feedback.good { border-color: #22c55e; }
      .feedback.mixed {
        border-image-slice:1; border-width:3px; border-style:solid;
        border-image-source: linear-gradient(90deg, #dc2626 var(--badpct,30%), #22c55e var(--badpct,30%));
      }
      .tick { color:#16a34a; font-weight:700; margin-left:6px; }
      .cross { color:#dc2626; font-weight:700; margin-left:6px; }
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

BLANK_RE = re.compile(r"\[\[(.+?)\]\]")

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

def split_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_RE.findall(cloze)
    parts = BLANK_RE.split(cloze)  # [seg0, ans1, seg1, ans2, seg2...]
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
    st.session_state.nav_guard = None
    st.session_state.dnd_lists = None  # dict: {"bank":[...], "blank1":[..], "blank2":[..] ...}
    st.session_state.correct_flags = None

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

    if current_dp is not None and current_dp != target_tuple and st.session_state.stage in ("fp","report","cloze","post_cloze","fp_followups"):
        st.session_state.nav_guard = {"target": target_tuple}
    else:
        st.session_state.selected_dp = target_tuple

# Guard UI
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
        rating_tmp = st.slider("Mark complete (rate 0–10)", 0, 10, 7)
        if st.button("Save & schedule", use_container_width=True):
            # TODO: persist rating + SRS
            reset_flow()
            st.session_state.selected_dp = st.session_state.nav_guard["target"]
            st.session_state.nav_guard = None
            st.rerun()
    with colg[2]:
        if st.button("Cancel", use_container_width=True):
            st.session_state.nav_guard = None
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
def go_stage(name: str):
    st.session_state.stage = name
    st.rerun()

# ----- FP -----
def do_fp():
    if not st.session_state.get("fp_q"):
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
        go_stage("report")

# ----- REPORT -----
def do_report():
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
            st.session_state.dnd_lists = None
            st.session_state.correct_flags = None
            if st.session_state.weak_list:
                go_stage("cloze")
            else:
                go_stage("fp")

# ----- CLOZE (true DnD with streamlit-sortables, persistent feedback until Continue) -----
def init_cloze_lists(answers: List[str]):
    # Build list-of-lists for sortables: first is the bank, then one list per blank
    bank = answers[:]  # start with all tokens in bank (scrambled)
    random.shuffle(bank)
    lists = [bank] + [[] for _ in answers]
    return lists

def do_cloze():
    if st.session_state.weak_index >= len(st.session_state.weak_list):
        st.success("All listed weaknesses processed. (Next: FP follow-ups / rating / exam.)")
        go_stage("fp")
    current_weak = st.session_state.weak_list[st.session_state.weak_index]

    # Prepare cloze
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = generate_cloze(dotpoint, current_weak, st.session_state.cloze_specificity)
        st.session_state.correct_flags = None
        st.session_state.feedback_class = None

    segs, answers = split_cloze(st.session_state.current_cloze)
    n_blanks = len(answers)
    if st.session_state.dnd_lists is None:
        st.session_state.dnd_lists = init_cloze_lists(answers)

    st.markdown(f'<div class="box-label">Targeting: {current_weak}</div>', unsafe_allow_html=True)

    # If we already submitted, show feedback border & ticks/crosses; else plain
    if st.session_state.correct_flags is not None:
        c = sum(st.session_state.correct_flags)
        bad_pct = int((n_blanks - c) / max(1, n_blanks) * 100)
        klass = "good" if c == n_blanks else "mixed"
        st.markdown(f'<div class="feedback {klass}" style="--badpct:{bad_pct}%">', unsafe_allow_html=True)

    # Inline row: seg0, drop1, seg1, drop2, ...
    st.markdown('<div class="cloze-row">', unsafe_allow_html=True)

    # Render BANK at top (label + sortables)
    st.markdown('<div class="bank-label">Words</div>', unsafe_allow_html=True)
    dnd_input = [lst[:] for lst in st.session_state.dnd_lists]  # deep copy for component
    dnd_result = sort_items(
        dnd_input,
        multi_containers=True,
        direction="horizontal",
        key=f"dnd_{st.session_state.weak_index}",
        # NOTE: streamlit-sortables options are intentionally simple for reliability on Cloud
    )
    # dnd_result is list-of-lists: [bank, blank1, blank2, ...]
    # Persist it:
    st.session_state.dnd_lists = [lst[:] for lst in dnd_result]

    # Now draw the sentence underneath with dropzone styles + ✓/✗ if submitted
    # Recompose inline visuals: seg + drop + seg + drop ...
    # (We just show visuals; actual lists are managed by sort_items above)
    st.markdown("</div>", unsafe_allow_html=True)  # close cloze-row

    # Visualize sentence with computed fills
    fills = [ (st.session_state.dnd_lists[i+1][0] if len(st.session_state.dnd_lists[i+1])>0 else "") for i in range(n_blanks) ]

    # Draw sentence with blanks as styled spans and correctness marks (if submitted)
    st.markdown('<div class="cloze-row">', unsafe_allow_html=True)
    for i in range(n_blanks):
        st.markdown(f'<span class="seg">{segs[i]}</span>', unsafe_allow_html=True)
        val = fills[i]
        filled = bool(val)
        ok = None
        if st.session_state.correct_flags is not None:
            ok = (val.strip().lower() == answers[i].strip().lower())
        dz_classes = ["dropzone"]
        if filled: dz_classes.append("filled")
        if ok is True: dz_classes.append("correct")
        if ok is False: dz_classes.append("wrong")
        mark = ""
        if ok is True: mark = '<span class="tick">✓</span>'
        if ok is False: mark = '<span class="cross">✗</span>'
        show = val if val else " "
        st.markdown(f'<span class="{" ".join(dz_classes)}">{show}{mark}</span>', unsafe_allow_html=True)
    st.markdown(f'<span class="seg">{segs[-1]}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Submit button (always at bottom)
    submit = st.button("Submit", type="primary", use_container_width=True)
    if submit:
        got = fills
        flags = [ (a.strip().lower() == (g or "").strip().lower()) for a, g in zip(answers, got) ]
        st.session_state.correct_flags = flags
        # Keep cloze visible with marks; do NOT advance — user must press Continue
        st.rerun()

    # If we have feedback, show Continue button to proceed to post-cloze (rating, etc.)
    if st.session_state.correct_flags is not None:
        cont = st.button("Continue", use_container_width=True)
        if cont:
            # move to post_cloze
            st.session_state.last_cloze_result = (sum(st.session_state.correct_flags), n_blanks)
            go_stage("post_cloze")

    if st.session_state.correct_flags is not None:
        st.markdown('</div>', unsafe_allow_html=True)  # close feedback box if open

# ----- POST-CLOZE (rating + add weaknesses -> branch) -----
def do_post_cloze():
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
        # Merge new weaknesses, dedupe, cap 5
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
            st.session_state.dnd_lists = None
            st.session_state.correct_flags = None
            go_stage("cloze")
        else:
            st.session_state.cloze_specificity = 0
            st.session_state.current_cloze = None
            st.session_state.dnd_lists = None
            st.session_state.correct_flags = None
            go_stage("fp_followups")

# ----- FP FOLLOW-UPS (placeholder) -----
def do_fp_followups():
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
        st.session_state.dnd_lists = None
        st.session_state.correct_flags = None
        st.session_state.cloze_specificity = 0
        if st.session_state.weak_index < len(st.session_state.weak_list):
            go_stage("cloze")
        else:
            st.success("All weaknesses cleared. (Next: overall rating / exam mode).")
            go_stage("fp")

# ================== ROUTER ==================
stage = st.session_state.stage
if stage == "fp":
    do_fp()
elif stage == "report":
    do_report()
elif stage == "cloze":
    do_cloze()
elif stage == "post_cloze":
    do_post_cloze()
elif stage == "fp_followups":
    do_fp_followups()
else:
    go_stage("fp")
