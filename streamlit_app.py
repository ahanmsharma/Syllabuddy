import json
import os
import re
from typing import Dict, List, Optional, Tuple
import streamlit as st

# ================== GLOBAL FLAGS ==================
# Force placeholders (disable AI calls even if OPENAI_API_KEY exists)
FORCE_PLACEHOLDERS = True

# ================== PAGE / STYLE ==================
st.set_page_config(page_title="", layout="centered")
st.markdown(
    """
    <style>
      header {visibility: hidden;}
      #MainMenu {visibility: hidden;} footer {visibility: hidden;}
      .block-container { max-width: 980px; margin: auto; padding-top: .2rem; }
      .dotpoint { font-weight: 700; font-size: 1.25rem; margin: .6rem 0 .6rem 0; }
      .fpq { font-size: 1.15rem; margin: 0 0 .4rem 0; }
      .box-label { font-weight: 600; color: #555; margin-bottom: .25rem; }
      .thin-divider { border-top: 1px solid #e6e6e6; margin: .6rem 0; }
      .stTextArea textarea { font-size: 1.05rem; line-height: 1.5; }
      .stTextInput input { font-size: 1.05rem; }
      .topnav .stSelectbox > div > div { font-size: 0.95rem; }
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

# ================== OPTIONAL OPENAI (kept, but bypassed when FORCE_PLACEHOLDERS) ==================
def _safe_secret(key: str) -> Optional[str]:
    try:
        return st.secrets[key]
    except Exception:
        return None

def get_openai_client():
    if FORCE_PLACEHOLDERS:
        return None, None, None
    api_key = os.getenv("OPENAI_API_KEY") or _safe_secret("OPENAI_API_KEY")
    if not api_key:
        return None, None, None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        return client, "gpt-5-mini", "gpt-5-nano"
    except Exception:
        return None, None, None

client, MODEL_MINI, MODEL_NANO = get_openai_client()

def chat_json(messages, model: str, temperature: float = 0.2) -> Dict:
    if client is None:
        return {}
    try:
        resp = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
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

# ================== HELPER: FP QUESTION (good placeholder) ==================
def heuristic_fp_question(dotpoint: str) -> str:
    """
    Higher-quality fallback FP question without AI:
    - asks mechanism/causality/assumptions/limits
    - avoids generic 'what are the first principles' wording
    """
    return (
        f"Using first principles, explain the underlying mechanism for “{dotpoint}”, "
        f"stating key assumptions and boundary conditions, and describe how the outcome changes "
        f"when those assumptions are violated."
    )

def generate_fp_question(dotpoint: str) -> str:
    if FORCE_PLACEHOLDERS or client is None:
        return heuristic_fp_question(dotpoint)
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
You are writing a single first-principles question for HSC students.

Dotpoint: "{dotpoint}"

- Probe mechanism / derivation / cause→effect.
- Include assumptions or limiting cases where relevant.
- One sentence, exam-ready, no meta.

Return JSON: {{"question":"..."}}
"""}],
        model=MODEL_MINI, temperature=0.2
    )
    return payload.get("question") or heuristic_fp_question(dotpoint)

# ================== HELPER: Suggested lists (weak/strong) ==================
def suggested_lists(dotpoint: str, user_answer: str) -> Dict:
    if FORCE_PLACEHOLDERS or client is None:
        return {
            "suggested_weaknesses": ["missed definition", "unclear mechanism", "weak example"],
            "suggested_strengths": ["correct terms", "coherent structure"]
        }
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only. Max 5 items per list. Each item 2–6 words."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Student answer: "{user_answer}"

Propose TWO lists:
1) suggested_weaknesses (≤5; semicolon-friendly short phrases)
2) suggested_strengths (≤5; short phrases)

JSON:
{{"suggested_weaknesses":["..."],"suggested_strengths":["..."]}}
"""}],
        model=MODEL_NANO, temperature=0.2
    )
    if not payload:
        return {"suggested_weaknesses": ["missed definition"], "suggested_strengths": ["clear terms"]}
    payload["suggested_weaknesses"] = payload.get("suggested_weaknesses", [])[:5]
    payload["suggested_strengths"] = payload.get("suggested_strengths", [])[:5]
    return payload

# ================== HELPER: Cloze ==================
BLANK_PATTERN = re.compile(r"\[\[(.+?)\]\]")

def generate_cloze_for_weakness(dotpoint: str, weakness: str) -> str:
    if FORCE_PLACEHOLDERS or client is None:
        # simple deterministic cloze for now
        return "Diffusion is net movement from [[higher concentration]] to [[lower concentration]] across a [[semi-permeable membrane]]."
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Target weakness: "{weakness}"

Write ONE short cloze sentence. Mark blanks with [[like this]]. Avoid multiple sentences.

JSON: {{"cloze":"Water moves down a [[concentration gradient]] across a [[selectively permeable membrane]]."}}
"""}],
        model=MODEL_MINI, temperature=0.2
    )
    return (payload.get("cloze") or "Diffusion is net movement from [[higher concentration]] to [[lower concentration]] across a [[semi-permeable membrane]].").strip()

def parse_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_PATTERN.findall(cloze)
    parts = BLANK_PATTERN.split(cloze)
    segments = [parts[0]]
    for i in range(1, len(parts), 2):
        segments.append(parts[i + 1] if i + 1 < len(parts) else "")
    return segments, answers

def render_cloze_inputs(cloze: str, key_prefix: str = "cloze") -> Tuple[List[str], List[str], bool]:
    segments, expected = parse_cloze(cloze)
    with st.form(key=f"{key_prefix}_form", clear_on_submit=False):
        st.markdown(f"**Fill the blanks:**  \n{BLANK_PATTERN.sub('_____', cloze)}")
        user_answers: List[str] = []
        for idx, _ in enumerate(expected, start=1):
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

# ================== TOP NAVIGATION (inline, not sidebar) ==================
st.markdown("#### ")  # small spacer

with st.container():
    st.markdown('<div class="topnav">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.4, 1.8])
    with col1:
        subject = st.selectbox("Subject", list(syllabus.keys()), key="nav_subject")
    with col2:
        module = st.selectbox("Module", list(syllabus[subject].keys()), key="nav_module")
    with col3:
        iq = st.selectbox("IQ", list(syllabus[subject][module].keys()), key="nav_iq")
    with col4:
        dotpoint = st.selectbox("Dotpoint", syllabus[subject][module][iq], key="nav_dotpoint")
    st.markdown('</div>', unsafe_allow_html=True)

# detect change and reset flow if dotpoint changed
prev_dp = st.session_state.selected["dotpoint"]
st.session_state.selected = {"subject": subject, "module": module, "iq": iq, "dotpoint": dotpoint}
if prev_dp is not None and prev_dp != dotpoint:
    st.session_state.stage = "fp"
    st.session_state.fp_q = None
    st.session_state.user_blurt = ""
    st.session_state.reports = {"weaknesses": "", "strengths": ""}
    st.session_state.weak_list = []
    st.session_state.weak_index = 0
    st.session_state.current_cloze = None
    st.rerun()

# ================== MAIN (single screen per stage) ==================
# Dotpoint at top
st.markdown(f'<div class="dotpoint">{st.session_state.selected["dotpoint"]}</div>', unsafe_allow_html=True)

# -- FP stage
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        st.session_state.fp_q = generate_fp_question(st.session_state.selected["dotpoint"])

    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form(key="fp_form", clear_on_submit=False):
        user_blurt = st.text_area(
            "Your answer",
            key="fp_blurt",
            height=340,
            label_visibility="collapsed",
            placeholder="Type your answer here…"
        )
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

# -- REPORT stage
elif st.session_state.stage == "report":
    st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="box-label">AI Weakness report</div>', unsafe_allow_html=True)
        wk = st.text_area("Weakness report", value=st.session_state.reports["weaknesses"],
                          key="wk_edit", height=260, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="box-label">AI Strength report</div>', unsafe_allow_html=True)
        stg = st.text_area("Strength report", value=st.session_state.reports["strengths"],
                           key="stg_edit", height=260, label_visibility="collapsed")

    mid = st.columns(3)[1]
    with mid:
        if st.button("Continue", use_container_width=True):
            weak_list = [w.strip() for w in (wk or "").split(";") if w.strip()]
            st.session_state.weak_list = weak_list[:5]
            st.session_state.reports["weaknesses"] = "; ".join(st.session_state.weak_list)
            st.session_state.reports["strengths"] = stg or ""
            st.session_state.weak_index = 0
            st.session_state.current_cloze = None
            st.session_state.stage = "cloze" if st.session_state.weak_list else "fp"
            st.rerun()

# -- CLOZE stage
elif st.session_state.stage == "cloze":
    if st.session_state.weak_index >= len(st.session_state.weak_list):
        st.success("All listed weaknesses processed. (Next: add FP follow-ups / rating / exam.)")
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
