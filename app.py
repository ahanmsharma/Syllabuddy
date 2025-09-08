import json
import os
from typing import Dict, List, Optional

import streamlit as st
from openai import OpenAI

# -------------------- PAGE / STYLE --------------------
st.set_page_config(page_title="Syllabuddy", layout="centered")
st.markdown(
    """
    <style>
      .block-container { max-width: 860px; margin: auto; }
      .stTextArea textarea { font-size: 0.98rem; line-height: 1.45; }
      .stTextInput input { font-size: 0.98rem; }
      .label { font-weight: 600; color: #666; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📘 Syllabuddy")
st.caption("Minimalist, one-question-at-a-time study flow (user-first; AI is secondary).")

# -------------------- LOAD SYLLABUS --------------------
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    with open("syllabus.json", "r") as f:
        return json.load(f)

syllabus = load_syllabus()

# -------------------- OPENAI CLIENT --------------------
def get_client() -> Optional[OpenAI]:
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

client = get_client()

# -------------------- SIDEBAR: SETTINGS --------------------
with st.sidebar:
    st.header("Navigation")
    subject = st.selectbox("Subject", list(syllabus.keys()))
    module = st.selectbox("Module", list(syllabus[subject].keys()))
    iq = st.selectbox("Inquiry Question", list(syllabus[subject][module].keys()))
    dotpoint = st.radio("Dotpoint", syllabus[subject][module][iq])

    st.divider()
    st.header("AI Settings")
    st.caption("Use **mini** for high-quality outputs; **nano** for cheap, short lists.")
    # If OpenAI model names differ in your account, edit here without touching code
    MODEL_MINI = st.text_input("Model (mini – high quality)", value="gpt-5-mini")
    MODEL_NANO = st.text_input("Model (nano – cheap lists)", value="gpt-5-nano")
    temp = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
    show_ai_json = st.toggle("Show raw AI JSON (debug)", value=False)

    st.divider()
    st.caption(f"API key detected: {'✅' if client else '❌'}")

# -------------------- AI HELPERS --------------------
def chat_json(messages: List[Dict], model: str, temperature: float = 0.2) -> Dict:
    """
    Call OpenAI chat and parse JSON content.
    Returns {} on failure or if client is missing.
    """
    if client is None:
        return {}
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        text = resp.choices[0].message.content.strip()

        # Allow for code-fenced JSON
        if text.startswith("```"):
            # remove fences
            lines = text.strip().splitlines()
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

def generate_fp_question(dotpoint_text: str) -> str:
    """
    High-quality FP questions → use MINI.
    """
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {
                "role": "user",
                "content": f"""
Given the syllabus dotpoint: "{dotpoint_text}"
Write ONE concise first-principles question that probes fundamentals (not trivia).
Return JSON: {{"question":"..."}}
""",
            },
        ],
        model=MODEL_MINI,
        temperature=temp,
    )
    return payload.get("question") or f"What are the fundamental principles behind: {dotpoint_text}?"

def model_answer_with_highlights(dotpoint_text: str, user_answer: str) -> Dict:
    """
    High-quality model answer + highlights → use MINI.
    Returns: {"model_answer":"...", "highlights":["...","..."]}
    """
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only. Keep 'highlights' to 3–6 short phrases."},
            {
                "role": "user",
                "content": f"""
Dotpoint: "{dotpoint_text}"
Student answer (for context): "{user_answer}"

Provide:
- a concise model answer (2–6 sentences)
- 3–6 short highlighted key phrases (not full sentences)

JSON schema:
{{"model_answer":"...","highlights":["...","..."]}}
""",
            },
        ],
        model=MODEL_MINI,
        temperature=temp,
    )
    if not payload:
        return {
            "model_answer": "Model answer placeholder (AI disabled or failed).",
            "highlights": ["key idea 1", "key idea 2", "key idea 3"],
        }
    return payload

def suggested_lists(dotpoint_text: str, user_answer: str) -> Dict:
    """
    Cheap suggested lists (weaknesses/strengths) → use NANO.
    Returns: {"suggested_weaknesses":[...<=5],"suggested_strengths":[...<=5]}
    """
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only. Max 5 items per list. Each item 2–6 words."},
            {
                "role": "user",
                "content": f"""
Dotpoint: "{dotpoint_text}"
Student answer: "{user_answer}"

Propose TWO lists:
1) suggested_weaknesses (≤5 short items; semicolon-friendly)
2) suggested_strengths (≤5 short items)

JSON:
{{"suggested_weaknesses":["..."],"suggested_strengths":["..."]}}
""",
            },
        ],
        model=MODEL_NANO,
        temperature=temp,
    )
    if not payload:
        return {
            "suggested_weaknesses": ["missed definition", "thin example"],
            "suggested_strengths": ["clear structure", "correct terms"],
        }
    return payload

# -------------------- SESSION STATE --------------------
if "fp_q" not in st.session_state:
    st.session_state.fp_q = None
if "model_bundle" not in st.session_state:
    st.session_state.model_bundle = None
if "report_suggestion" not in st.session_state:
    st.session_state.report_suggestion = None

# -------------------- MAIN UI --------------------
st.subheader("📍 Dotpoint")
st.info(dotpoint)

# 1) USER ANSWERS FIRST
st.markdown("### Step 1 — Your answer (blurting)")
user_answer = st.text_area(
    "Write everything you know. (You first, then AI shows a model answer)",
    key="user_blurt",
    height=160,
)

c1, c2 = st.columns(2)
with c1:
    if st.button("Generate first-principles question", use_container_width=True):
        st.session_state.fp_q = generate_fp_question(dotpoint)
with c2:
    if st.button("Clear question", use_container_width=True):
        st.session_state.fp_q = None

if st.session_state.fp_q:
    st.markdown("#### First-principles question")
    st.write(st.session_state.fp_q)

# 2) AI MODEL ANSWER + HIGHLIGHTS
if st.button("Show model answer + highlights", type="primary", use_container_width=True):
    if not user_answer.strip():
        st.warning("Please write your answer first.")
    else:
        st.session_state.model_bundle = model_answer_with_highlights(dotpoint, user_answer)
        st.session_state.report_suggestion = suggested_lists(dotpoint, user_answer)

if st.session_state.model_bundle:
    st.markdown("### Model answer")
    st.success(st.session_state.model_bundle.get("model_answer", ""))
    st.markdown("**Highlights**")
    for h in st.session_state.model_bundle.get("highlights", []):
        st.markdown(f"- ✅ **{h}**")

    if show_ai_json and st.session_state.report_suggestion:
        with st.expander("AI JSON (debug)"):
            st.json(st.session_state.report_suggestion)

# 3) USER WEAKNESSES + AI SUGGESTED REPORT (NANO)
st.markdown("---")
st.markdown("### Step 2 — Mark your weaknesses & strengths (you’re in control)")
default_weak = ""
default_str = ""
if st.session_state.report_suggestion:
    default_weak = "; ".join(st.session_state.report_suggestion.get("suggested_weaknesses", []))
    default_str = "; ".join(st.session_state.report_suggestion.get("suggested_strengths", []))

weaknesses = st.text_input("Your weaknesses (semicolon-separated):", value=default_weak)
strengths = st.text_input("Your strengths (semicolon-separated):", value=default_str)

cc1, cc2 = st.columns(2)
with cc1:
    rating = st.slider("Rate your understanding (0–10)", 0, 10, 6)
with cc2:
    next_step = st.selectbox(
        "Next step",
        ["Stop for now", "Optional strength check (1–2 Qs)", "Go to Exam Mode"],
    )

st.markdown("---")

# 4) SAVE STEP (persistence hooks come later w/ SQLite)
if st.button("Save & Continue", use_container_width=True):
    st.session_state.last_saved = {
        "dotpoint": dotpoint,
        "user_answer": user_answer,
        "rating": rating,
        "weaknesses": [w.strip() for w in weaknesses.split(";") if w.strip()],
        "strengths": [s.strip() for s in strengths.split(";") if s.strip()],
        "fp_question": st.session_state.fp_q,
    }
    st.success("Saved current step.")
    if next_step == "Optional strength check (1–2 Qs)":
        st.info("Strength check placeholder — next iteration will add targeted questions here.")
    elif next_step == "Go to Exam Mode":
        st.info("Exam Mode placeholder — next iteration will pull HSC-style questions and sample answers.")
    else:
        st.stop()

st.caption("Next up: per-weakness cloze + FP follow-ups, Exam Mode, and SRS scheduling.")
