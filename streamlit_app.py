import json
import os
import re
from typing import Dict, List, Optional, Tuple

import streamlit as st

# ================== PAGE + STYLE (no title, no footer/menu) ==================
st.set_page_config(page_title="", layout="centered")
st.markdown(
    """
    <style>
      header {visibility: hidden;} /* hide default Streamlit header */
      .stAppDeployButton {display: none;}
      #MainMenu {visibility: hidden;} footer {visibility: hidden;} /* hide footer/menu */
      .block-container { max-width: 820px; margin: auto; padding-top: 0.8rem; }
      .stTextArea textarea, .stTextInput input { font-size: 1.0rem; }
      .dotpoint { font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem; }
      .box-label { font-weight: 600; color: #666; }
      .fpq { font-size: 1.02rem; margin: 0.4rem 0 0.2rem 0; }
      .thin-divider { border-top: 1px solid #e6e6e6; margin: 0.6rem 0 0.6rem 0; }
      .btnrow div button { width: 100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================== LOAD SYLLABUS (replace with your data source) ==================
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    with open("syllabus.json", "r") as f:
        return json.load(f)

syllabus = load_syllabus()

# ================== OPENAI CLIENT (optional) ==================
def safe_secret(key: str) -> Optional[str]:
    try:
        return st.secrets[key]
    except Exception:
        return None

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY") or safe_secret("OPENAI_API_KEY")
    if not api_key:
        return None, None, None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # model choice: mini for FP quality, nano for cheap lists
        model_mini = "gpt-5-mini"
        model_nano = "gpt-5-nano"
        return client, model_mini, model_nano
    except Exception:
        return None, None, None

client, MODEL_MINI, MODEL_NANO = get_openai_client()

def chat_json(messages: List[Dict], model: str, temperature: float = 0.2) -> Dict:
    """Call OpenAI; expect JSON back. Return {} on failure or if no client."""
    if client is None:
        return {}
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        text = resp.choices[0].message.content.strip()
        # strip code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            if lines and lines[0].lower().startswith("json"):
                lines = lines[1:]
            text = "\n".join(lines).strip()
        return json.loads(text)
    except Exception:
        return {}

# ================== AI HELPERS ==================
def generate_fp_question(dotpoint: str) -> str:
    """One concise FP question (quality-first)."""
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Write ONE concise first-principles question that probes fundamentals (not trivia).
JSON: {{"question":"..."}}
"""},
        ],
        model=MODEL_MINI or "gpt-5-mini",
        temperature=0.2,
    )
    return payload.get("question") or f"What are the fundamental principles behind: {dotpoint}?"

def suggested_lists(dotpoint: str, user_answer: str) -> Dict:
    """Cheap suggested weakness/strength lists, each ≤5 short items."""
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only. Max 5 items per list. Each item 2–6 words."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Student answer: "{user_answer}"

Propose TWO lists:
1) suggested_weaknesses (≤5 short items; semicolon-friendly)
2) suggested_strengths (≤5 short items)

JSON:
{{"suggested_weaknesses":["..."],"suggested_strengths":["..."]}}
"""},
        ],
        model=MODEL_NANO or "gpt-5-nano",
        temperature=0.2,
    )
    if not payload:
        return {
            "suggested_weaknesses": ["missed definition", "thin example"],
            "suggested_strengths": ["clear terms", "good structure"],
        }
    # Trim to max 5
    payload["suggested_weaknesses"] = payload.get("suggested_weaknesses", [])[:5]
    payload["suggested_strengths"] = payload.get("suggested_strengths", [])[:5]
    return payload

def generate_cloze_for_weakness(dotpoint: str, weakness: str) -> str:
    """
    Produce 1 cloze sentence with [[blank]] markers targeting the weakness.
    Keep it short and aligned to the dotpoint. One or more [[...]] allowed.
    """
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Target weakness: "{weakness}"

Write ONE short cloze sentence that directly tests this weakness.
Mark blanks with [[like this]]. Avoid multiple sentences.

JSON: {{"cloze":"Water moves down a [[concentration gradient]] across a [[selectively permeable membrane]]."}}
"""},
        ],
        model=MODEL_MINI or "gpt-5-mini",
        temperature=0.2,
    )
    return (payload.get("cloze") or "Diffusion is the net movement of particles from [[higher concentration]] to [[lower concentration]].").strip()

# ================== CLOZE RENDERING ==================
BLANK_PATTERN = re.compile(r"\[\[(.+?)\]\]")

def parse_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    """
    Returns (segments, answers)
    segments: alternating text segments between blanks (len = n_blanks+1)
    answers: list of expected answers for each [[...]] (in order)
    """
    answers = BLANK_PATTERN.findall(cloze)
    parts = BLANK_PATTERN.split(cloze)  # text, ans1, text, ans2, text...
    segments = [parts[0]]
    # Every odd index in parts is an answer; even indices are text segments
    for i in range(1, len(parts), 2):
        # we don't include the answer in segments; instead we add a "" slot later
        # but we need the following text segment
        if i + 1 < len(parts):
            segments.append(parts[i + 1])
        else:
            segments.append("")
    return segments, answers

def render_cloze_inputs(cloze: str, key_prefix: str = "cloze") -> Tuple[List[str], List[str], bool]:
    """
    Render cloze with text inputs as blanks.
    Returns (answers_expected, answers_user, submitted_flag).
    """
    segments, expected = parse_cloze(cloze)
    with st.form(key=f"{key_prefix}_form", clear_on_submit=False):
        st.write("")  # small spacer
        # Build a single line with inline inputs
        cols = []
        user_answers: List[str] = []
        # We'll display as: seg0 [input0] seg1 [input1] seg2 ...
        # To keep it responsive, put it in a markdown with inputs stacked beneath
        # But we can approximate inline by just showing the sentence and then inputs labelled 1..n
        st.markdown(f"**Fill the blanks:**  \n{BLANK_PATTERN.sub('_____', cloze)}")

        for idx, ans in enumerate(expected, start=1):
            val = st.text_input(f"Blank {idx}", key=f"{key_prefix}_{idx}")
            user_answers.append(val or "")

        submitted = st.form_submit_button("Submit cloze")
    return expected, user_answers, submitted

def check_cloze(expected: List[str], user_answers: List[str]) -> Tuple[int, int, List[bool]]:
    correct_flags = []
    for exp, got in zip(expected, user_answers):
        ok = exp.strip().lower() == (got or "").strip().lower()
        correct_flags.append(ok)
    return sum(correct_flags), len(expected), correct_flags

# ================== STATE ==================
if "stage" not in st.session_state:
    st.session_state.stage = "fp"  # 'fp' -> 'report' -> 'cloze' -> ...
if "selected" not in st.session_state:
    st.session_state.selected = {"subject": None, "module": None, "iq": None, "dotpoint": None}
if "fp_q" not in st.session_state:
    st.session_state.fp_q = None
if "user_blurt" not in st.session_state:
    st.session_state.user_blurt = ""
if "reports" not in st.session_state:
    st.session_state.reports = {"weaknesses": "", "strengths": ""}
if "weak_list" not in st.session_state:
    st.session_state.weak_list = []
if "weak_index" not in st.session_state:
    st.session_state.weak_index = 0
if "current_cloze" not in st.session_state:
    st.session_state.current_cloze = None

# ================== NAV: choose dotpoint (sidebar only) ==================
with st.sidebar:
    subject = st.selectbox("Subject", list(syllabus.keys()))
    module = st.selectbox("Module", list(syllabus[subject].keys()))
    iq = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()))
    dotpoint = st.radio("Dotpoint", syllabus[subject][module][iq])
    # Reset flow when dotpoint changes
    changed = (
        st.session_state.selected["dotpoint"] is not None
        and st.session_state.selected["dotpoint"] != dotpoint
    )
    st.session_state.selected = {"subject": subject, "module": module, "iq": iq, "dotpoint": dotpoint}
    if changed:
        st.session_state.stage = "fp"
        st.session_state.fp_q = None
        st.session_state.user_blurt = ""
        st.session_state.reports = {"weaknesses": "", "strengths": ""}
        st.session_state.weak_list = []
        st.session_state.weak_index = 0
        st.session_state.current_cloze = None
        st.experimental_rerun()

# ================== MAIN FLOW ==================
# Dotpoint at top (only)
st.markdown(f'<div class="dotpoint">{st.session_state.selected["dotpoint"]}</div>', unsafe_allow_html=True)

# -------- Stage: FP (first-principles Q only, single textbox + submit) --------
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        # Generate the FP question now (or keep last)
        st.session_state.fp_q = generate_fp_question(st.session_state.selected["dotpoint"])

    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form(key="fp_form", clear_on_submit=False):
        user_blurt = st.text_area("", key="fp_blurt", height=220, label_visibility="collapsed")
        submitted = st.form_submit_button("Submit")
    if submitted:
        st.session_state.user_blurt = user_blurt or ""
        # Build suggested lists
        sug = suggested_lists(st.session_state.selected["dotpoint"], st.session_state.user_blurt)
        default_weak = "; ".join(sug.get("suggested_weaknesses", []))
        default_str = "; ".join(sug.get("suggested_strengths", []))
        st.session_state.reports = {"weaknesses": default_weak, "strengths": default_str}
        st.session_state.stage = "report"
        st.experimental_rerun()

# -------- Stage: REPORT (two boxes, editable, nothing else) --------
elif st.session_state.stage == "report":
    st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="box-label">AI Weakness report</div>', unsafe_allow_html=True)
        wk = st.text_area("", value=st.session_state.reports["weaknesses"], key="wk_edit", height=180, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="box-label">AI Strength report</div>', unsafe_allow_html=True)
        stg = st.text_area("", value=st.session_state.reports["strengths"], key="stg_edit", height=180, label_visibility="collapsed")

    # Confirm -> proceed to cloze on first weakness (if any)
    col = st.columns(3)
    with col[1]:
        if st.button("Continue", use_container_width=True):
            # Normalize user-edited weaknesses to list
            weak_list = [w.strip() for w in (wk or "").split(";") if w.strip()]
            st.session_state.weak_list = weak_list[:5]  # keep ≤5
            st.session_state.reports["weaknesses"] = "; ".join(st.session_state.weak_list)
            st.session_state.reports["strengths"] = stg or ""
            st.session_state.weak_index = 0
            if st.session_state.weak_list:
                st.session_state.stage = "cloze"
            else:
                # If no weaknesses, you could proceed to strength-check or exam mode; for now go back to fp
                st.session_state.stage = "fp"
            st.experimental_rerun()

# -------- Stage: CLOZE (target current weakness; inline inputs; submit) --------
elif st.session_state.stage == "cloze":
    # If we ran out of weaknesses, decide next stage (later: strength-challenge or exam)
    if st.session_state.weak_index >= len(st.session_state.weak_list):
        # Placeholder: after all weaknesses, you can route to FP follow-ups or next stage
        st.success("All listed weaknesses processed. (Next: follow your flowchart: FP follow-ups / rating / exam...)")
        # Reset to FP for now (you will extend here)
        st.session_state.stage = "fp"
        st.experimental_rerun()

    current_weak = st.session_state.weak_list[st.session_state.weak_index]
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = generate_cloze_for_weakness(
            st.session_state.selected["dotpoint"], current_weak
        )

    st.markdown(f'<div class="box-label">Targeting: {current_weak}</div>', unsafe_allow_html=True)

    expected, user_ans, submitted = render_cloze_inputs(
        st.session_state.current_cloze, key_prefix=f"cloze_{st.session_state.weak_index}"
    )
    if submitted:
        correct, total, flags = check_cloze(expected, user_ans)
        if correct == total:
            st.success("Perfect.")
            # advance to next weakness
            st.session_state.weak_index += 1
            st.session_state.current_cloze = None
            st.experimental_rerun()
        else:
            # show which blanks are wrong; stay on this cloze
            wrongs = [str(i+1) for i, ok in enumerate(flags) if not ok]
            st.error(f"Incorrect blanks: {', '.join(wrongs)}. Try again or adjust your weakness list.")

            # Optional: provide a "Reveal answer" button
            if st.button("Reveal answers"):
                shown = " / ".join([f"[{i+1}] {exp}" for i, exp in enumerate(expected)])
                st.info(f"Answers: {shown}")

# -------- Fallback --------
else:
    st.session_state.stage = "fp"
    st.experimental_rerun()
