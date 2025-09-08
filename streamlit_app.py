import json
import os
import re
from typing import Dict, List, Optional, Tuple

import streamlit as st

# ================== PAGE / STYLE (minimal, bigger UI, no title) ==================
st.set_page_config(page_title="", layout="centered")
st.markdown(
    """
    <style>
      header {visibility: hidden;} /* hide default header */
      #MainMenu {visibility: hidden;} footer {visibility: hidden;} /* hide footer */
      .block-container { max-width: 980px; margin: auto; padding-top: .2rem; }
      .dotpoint { font-weight: 700; font-size: 1.25rem; margin: .2rem 0 .6rem 0; }
      .fpq { font-size: 1.15rem; margin: 0 0 .4rem 0; }
      .box-label { font-weight: 600; color: #555; margin-bottom: .25rem; }
      .thin-divider { border-top: 1px solid #e6e6e6; margin: .6rem 0; }
      .stTextArea textarea { font-size: 1.05rem; line-height: 1.5; }
      .stTextInput input { font-size: 1.05rem; }
      .btnrow div button { width: 100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ================== LOAD SYLLABUS ==================
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    with open("syllabus.json", "r") as f:
        return json.load(f)

syllabus = load_syllabus()

# ================== OPENAI CLIENT (mini for quality, nano for lists) ==================
def _safe_secret(key: str) -> Optional[str]:
    try:
        return st.secrets[key]
    except Exception:
        return None

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY") or _safe_secret("OPENAI_API_KEY")
    if not api_key:
        return None, None, None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        MODEL_MINI = "gpt-5-mini"
        MODEL_NANO = "gpt-5-nano"
        return client, MODEL_MINI, MODEL_NANO
    except Exception:
        return None, None, None

client, MODEL_MINI, MODEL_NANO = get_openai_client()

def chat_json(messages: List[Dict], model: str, temperature: float = 0.2) -> Dict:
    if client is None:
        return {}
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
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
    """
    Produce ONE high-quality first-principles question:
    - probes mechanism/causality/derivation (not recall)
    - references constraints, assumptions, edge cases
    - clean, exam-ready wording
    """
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
You are writing a single *first-principles* question for HSC students.

Dotpoint: "{dotpoint}"

Requirements for the question:
- Ask for fundamentals: mechanism / derivation / cause→effect.
- Avoid generic stems like "What are the first principles...".
- Include constraints/assumptions or boundary conditions if helpful.
- Keep it concise (1 sentence), exam-ready, no meta text.

Respond JSON: {{"question":"..."}}
"""}
        ],
        model=MODEL_MINI or "gpt-5-mini",
        temperature=0.2,
    )
    fallback = (
        f"From first principles, explain the underlying mechanism, assumptions, and limiting conditions for: {dotpoint}."
    )
    return payload.get("question") or fallback

def suggested_lists(dotpoint: str, user_answer: str) -> Dict:
    """
    Cheap suggested weakness/strength lists (≤5 items each).
    """
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only. Max 5 items per list. Each item 2–6 words."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Student answer: "{user_answer}"

Propose TWO lists:
1) suggested_weaknesses (≤5; semicolon-friendly; short phrases)
2) suggested_strengths (≤5; short phrases)

JSON:
{{"suggested_weaknesses":["..."],"suggested_strengths":["..."]}}
"""}
        ],
        model=MODEL_NANO or "gpt-5-nano",
        temperature=0.2,
    )
    if not payload:
        return {
            "suggested_weaknesses": ["missed definition", "thin example"],
            "suggested_strengths": ["clear terms", "good structure"],
        }
    payload["suggested_weaknesses"] = payload.get("suggested_weaknesses", [])[:5]
    payload["suggested_strengths"] = payload.get("suggested_strengths", [])[:5]
    return payload

def generate_cloze_for_weakness(dotpoint: str, weakness: str) -> str:
    """
    One cloze sentence with [[blank]] markers targeting the weakness.
    Short, precise, aligns to dotpoint; allow multiple blanks.
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
"""}
        ],
        model=MODEL_MINI or "gpt-5-mini",
        temperature=0.2,
    )
    return (payload.get("cloze") or "Diffusion is the net movement from [[higher concentration]] to [[lower concentration]] across a [[semi-permeable membrane]].").strip()

# ================== CLOZE PARSING/RENDERING ==================
BLANK_PATTERN = re.compile(r"\[\[(.+?)\]\]")

def parse_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_PATTERN.findall(cloze)
    parts = BLANK_PATTERN.split(cloze)  # text, ans1, text, ans2, text...
    segments = [parts[0]]
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            segments.append(parts[i + 1])
        else:
            segments.append("")
    return segments, answers

def render_cloze_inputs(cloze: str, key_prefix: str = "cloze") -> Tuple[List[str], List[str], bool]:
    segments, expected = parse_cloze(cloze)
    with st.form(key=f"{key_prefix}_form", clear_on_submit=False):
        st.markdown(f"**Fill the blanks:**  \n{BLANK_PATTERN.sub('_____', cloze)}")
        user_answers: List[str] = []
        for idx, _ in enumerate(expected, start=1):
            # Non-empty label (hidden visually with 'collapsed')
            val = st.text_input(f"Blank {idx}", key=f"{key_prefix}_{idx}", label_visibility="visible")
            user_answers.append(val or "")
        submitted = st.form_submit_button("Submit cloze")
    return expected, user_answers, submitted

def check_cloze(expected: List[str], user_answers: List[str]) -> Tuple[int, int, List[bool]]:
    flags = []
    for exp, got in zip(expected, user_answers):
        ok = exp.strip().lower() == (got or "").strip().lower()
        flags.append(ok)
    return sum(flags), len(expected), flags

# ================== STATE ==================
if "stage" not in st.session_state:
    st.session_state.stage = "fp"  # 'fp' -> 'report' -> 'cloze'
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

# ================== NAV (sidebar only) ==================
with st.sidebar:
    subject = st.selectbox("Subject", list(syllabus.keys()))
    module = st.selectbox("Module", list(syllabus[subject].keys()))
    iq = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()))
    dotpoint = st.radio("Dotpoint", syllabus[subject][module][iq])

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
        st.rerun()

# ================== MAIN (single thing per screen) ==================
# Dotpoint at top
st.markdown(f'<div class="dotpoint">{st.session_state.selected["dotpoint"]}</div>', unsafe_allow_html=True)

# -- FP stage: one FP question + one big textarea + Submit
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        st.session_state.fp_q = generate_fp_question(st.session_state.selected["dotpoint"])

    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form(key="fp_form", clear_on_submit=False):
        # Non-empty label, hidden visually via collapsed
        user_blurt = st.text_area("Your answer", key="fp_blurt", height=320, label_visibility="collapsed", placeholder="Type your answer here…")
        submitted = st.form_submit_button("Submit")
    if submitted:
        st.session_state.user_blurt = user_blurt or ""
        sug = suggested_lists(st.session_state.selected["dotpoint"], st.session_state.user_blurt)
        st.session_state.reports = {
            "weaknesses": "; ".join(sug.get("suggested_weaknesses", [])),
            "strengths": "; ".join(sug.get("suggested_strengths", [])),
        }
        st.session_state.stage = "report"
        st.rerun()

# -- REPORT stage: two editable boxes only
elif st.session_state.stage == "report":
    st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="box-label">AI Weakness report</div>', unsafe_allow_html=True)
        wk = st.text_area("Weakness report", value=st.session_state.reports["weaknesses"], key="wk_edit", height=240, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="box-label">AI Strength report</div>', unsafe_allow_html=True)
        stg = st.text_area("Strength report", value=st.session_state.reports["strengths"], key="stg_edit", height=240, label_visibility="collapsed")

    center = st.columns(3)[1]
    with center:
        if st.button("Continue", use_container_width=True):
            weak_list = [w.strip() for w in (wk or "").split(";") if w.strip()]
            st.session_state.weak_list = weak_list[:5]
            st.session_state.reports["weaknesses"] = "; ".join(st.session_state.weak_list)
            st.session_state.reports["strengths"] = stg or ""
            st.session_state.weak_index = 0
            st.session_state.current_cloze = None
            if st.session_state.weak_list:
                st.session_state.stage = "cloze"
            else:
                st.session_state.stage = "fp"  # or strength-check; keep simple now
            st.rerun()

# -- CLOZE stage: targeted cloze for current weakness
elif st.session_state.stage == "cloze":
    if st.session_state.weak_index >= len(st.session_state.weak_list):
        st.success("All listed weaknesses processed. (Next: add FP follow-ups / rating / exam per your flow.)")
        st.session_state.stage = "fp"
        st.rerun()

    current_weak = st.session_state.weak_list[st.session_state.weak_index]
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = generate_cloze_for_weakness(
            st.session_state.selected["dotpoint"], current_weak
        )

    st.markdown(f'<div class="box-label">Targeting: {current_weak}</div>', unsafe_allow_html=True)
    expected, user_ans, submitted = render_cloze_inputs(
        st.session_state.current_cloze, key_prefix=f"clz_{st.session_state.weak_index}"
    )
    if submitted:
        correct, total, flags = check_cloze(expected, user_ans)
        if correct == total:
            st.success("Perfect.")
            st.session_state.weak_index += 1
            st.session_state.current_cloze = None
            st.rerun()
        else:
            wrongs = [str(i+1) for i, ok in enumerate(flags) if not ok]
            st.error(f"Incorrect blanks: {', '.join(wrongs)}.")
            if st.button("Reveal answers"):
                shown = " / ".join([f"[{i+1}] {exp}" for i, exp in enumerate(expected)])
                st.info(f"Answers: {shown}")

# -- fallback
else:
    st.session_state.stage = "fp"
    st.rerun()
