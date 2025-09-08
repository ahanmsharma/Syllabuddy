import json
import os
import re
import random
from typing import Dict, List, Optional, Tuple
import streamlit as st

# ================== FLAGS ==================
# Keep API disabled by default (placeholders only). Switch to False when you want live models.
FORCE_PLACEHOLDERS = True

# ================== PAGE / STYLE ==================
st.set_page_config(page_title="", layout="wide")
st.markdown(
    """
    <style>
      header {visibility: hidden;}
      #MainMenu {visibility: hidden;} footer {visibility: hidden;}

      .block-container { max-width: 1220px; margin: auto; padding-top: .2rem; }
      .dotpoint { font-weight: 700; font-size: 1.35rem; margin: .25rem 0 .65rem 0; }
      .fpq { font-size: 1.18rem; margin: 0 0 .5rem 0; }
      .box-label { font-weight: 600; color: #555; margin: .25rem 0 .35rem 0; }
      .thin-divider { border-top: 1px solid #e6e6e6; margin: .7rem 0; }

      .cloze-sentence { font-size: 1.10rem; line-height: 1.6; }
      .cloze-blank { display:inline-block; min-width: 140px; padding: 4px 8px; border-bottom: 2px solid #999; margin: 0 .25rem; }
      .chip { display:inline-block; border: 1px solid #ccc; border-radius: 999px; padding: 4px 10px; margin: 4px 6px 0 0; cursor: pointer; }
      .chip:hover { background: #f5f5f5; }
      .chips-wrap { margin-top: .35rem; }
      .inline-label { font-size: 0.9rem; color: #777; margin-right: .4rem; }
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

# ================== OPTIONAL OPENAI (kept, but bypassed if FORCE_PLACEHOLDERS) ==================
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

# ================== HELPERS: FP / Reports / Cloze ==================
def heuristic_fp(dotpoint: str) -> str:
    return (
        f"From first principles, explain the mechanism for “{dotpoint}”, "
        f"state key assumptions and limiting cases, and justify each step "
        f"so that the result would still be correct under small variations in conditions."
    )

def generate_fp_question(dotpoint: str) -> str:
    if FORCE_PLACEHOLDERS or client is None:
        return heuristic_fp(dotpoint)
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
One *first-principles* question only.

Dotpoint: "{dotpoint}"

- Probe mechanism/derivation/causal chain
- Mention assumptions or limits if relevant
- One sentence; exam-ready

JSON: {{"question":"..."}}
"""}],
        model=MODEL_MINI, temperature=0.2
    )
    return payload.get("question") or heuristic_fp(dotpoint)

def suggested_lists(dotpoint: str, user_answer: str) -> Dict:
    if FORCE_PLACEHOLDERS or client is None:
        return {
            "suggested_weaknesses": ["unclear mechanism", "definition gap", "weak example"],
            "suggested_strengths": ["correct terms", "coherent structure"]
        }
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only. ≤5 items per list, 2–6 words each."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Student answer: "{user_answer}"

Return:
{{"suggested_weaknesses":["..."],"suggested_strengths":["..."]}}
"""}],
        model=MODEL_NANO, temperature=0.2
    )
    if not payload:
        return {"suggested_weaknesses": ["definition gap"], "suggested_strengths": ["clear terms"]}
    payload["suggested_weaknesses"] = payload.get("suggested_weaknesses", [])[:5]
    payload["suggested_strengths"] = payload.get("suggested_strengths", [])[:5]
    return payload

BLANK_PATTERN = re.compile(r"\[\[(.+?)\]\]")

def _placeholder_cloze() -> str:
    return "Diffusion is net movement from [[higher concentration]] to [[lower concentration]] across a [[semi-permeable membrane]]."

def generate_cloze(dotpoint: str, weakness: str, specificity: int = 0) -> str:
    """
    specificity: 0 = broad, 1 = narrower scaffold for same weakness
    """
    if FORCE_PLACEHOLDERS or client is None:
        if specificity == 0:
            return _placeholder_cloze()
        else:
            return "Facilitated diffusion uses [[membrane proteins]] to move substances down a [[concentration gradient]] without [[ATP hydrolysis]]."
    payload = chat_json(
        [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": f"""
Dotpoint: "{dotpoint}"
Target weakness: "{weakness}"
Specificity level: {specificity}  # 0 broad, 1 narrower

Write ONE cloze sentence with key terms as [[blanks]] (1–4 blanks). Short and precise.

JSON: {{"cloze":"..."}}
"""}],
        model=MODEL_MINI, temperature=0.2
    )
    return (payload.get("cloze") or _placeholder_cloze()).strip()

def parse_cloze(cloze: str) -> Tuple[List[str], List[str]]:
    answers = BLANK_PATTERN.findall(cloze)
    parts = BLANK_PATTERN.split(cloze)  # text, ans1, text, ans2, text...
    segments = [parts[0]]
    for i in range(1, len(parts), 2):
        segments.append(parts[i + 1] if i + 1 < len(parts) else "")
    return segments, answers

# ================== INLINE CLOZE W/ CHIPS ==================
def render_inline_cloze(cloze: str, key_prefix: str = "cloze") -> Tuple[List[str], List[str], bool]:
    """
    Renders the cloze as a sentence with inline text_inputs for each [[blank]] AND
    displays scrambled chips you can click to auto-fill the next empty blank.
    Returns (expected_answers, user_answers, submitted)
    """
    segments, expected = parse_cloze(cloze)

    # Prepare shuffled chips (unique, case preserved)
    chips = expected[:]
    random.shuffle(chips)

    with st.form(key=f"{key_prefix}_form", clear_on_submit=False):
        # Inline sentence: text + inputs
        st.markdown('<div class="cloze-sentence">', unsafe_allow_html=True)
        # Build the row: seg0 [input1] seg1 [input2] ...
        # We simulate inline by writing markdown segments and rendering inputs right after.
        # To visually keep it inline, we style inputs as "cloze-blank" via label text + CSS (approx).
        user_vals: List[str] = []
        for i, _exp in enumerate(expected, start=1):
            # Print leading segment
            st.write(segments[i-1], unsafe_allow_html=False)
            # Inline input (label is visible for a11y but short)
            v = st.text_input(f"Blank {i}", key=f"{key_prefix}_{i}", label_visibility="visible", placeholder="type here")
            user_vals.append(v or "")
        # trailing segment
        st.write(segments[-1], unsafe_allow_html=False)
        st.markdown('</div>', unsafe_allow_html=True)

        # Chips row (click-to-fill next empty)
        st.markdown('<div class="chips-wrap"><span class="inline-label">Words:</span>', unsafe_allow_html=True)
        chip_cols = st.columns(min(6, max(1, len(chips))))
        for idx, token in enumerate(chips):
            col = chip_cols[idx % len(chip_cols)]
            with col:
                if st.form_submit_button(token):  # button per chip inside the same form
                    # Fill next empty
                    for j in range(len(expected)):
                        keyj = f"{key_prefix}_{j+1}"
                        if not st.session_state.get(keyj):
                            st.session_state[keyj] = token
                            break
                    # Re-render form state
                    st.stop()
        st.markdown('</div>', unsafe_allow_html=True)

        submitted = st.form_submit_button("Submit cloze")

    return expected, [st.session_state.get(f"{key_prefix}_{i}", "") for i in range(1, len(expected)+1)], submitted

def score_cloze(expected: List[str], got: List[str]) -> Tuple[int, int, List[bool]]:
    flags = []
    for exp, x in zip(expected, got):
        flags.append(exp.strip().lower() == (x or "").strip().lower())
    return sum(flags), len(expected), flags

# ================== STATE ==================
if "stage" not in st.session_state:
    st.session_state.stage = "fp"  # 'fp' -> 'report' -> 'cloze' -> 'post_cloze'
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
if "cloze_specificity" not in st.session_state:
    st.session_state.cloze_specificity = 0
if "last_cloze_result" not in st.session_state:
    st.session_state.last_cloze_result = None  # (correct,total)

# ================== SIDEBAR NAV (collapsible) ==================
with st.sidebar:
    st.header("Navigation")
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
        st.session_state.cloze_specificity = 0
        st.session_state.last_cloze_result = None
        st.rerun()

# ================== MAIN ==================
st.markdown(f'<div class="dotpoint">{st.session_state.selected["dotpoint"]}</div>', unsafe_allow_html=True)

# ----- FP stage -----
if st.session_state.stage == "fp":
    if not st.session_state.fp_q:
        st.session_state.fp_q = generate_fp_question(st.session_state.selected["dotpoint"])
    st.markdown(f'<div class="fpq">{st.session_state.fp_q}</div>', unsafe_allow_html=True)

    with st.form(key="fp_form", clear_on_submit=False):
        blurt = st.text_area("Your answer", key="fp_blurt", height=360, label_visibility="collapsed", placeholder="Type your answer here…")
        submitted = st.form_submit_button("Submit")
    if submitted:
        st.session_state.user_blurt = blurt or ""
        sug = suggested_lists(st.session_state.selected["dotpoint"], st.session_state.user_blurt)
        st.session_state.reports = {
            "weaknesses": "; ".join(sug.get("suggested_weaknesses", [])),
            "strengths": "; ".join(sug.get("suggested_strengths", [])),
        }
        st.session_state.stage = "report"
        st.rerun()

# ----- REPORT stage -----
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
            st.session_state.stage = "cloze" if st.session_state.weak_list else "fp"
            st.rerun()

# ----- CLOZE stage (inline blanks + chips) -----
elif st.session_state.stage == "cloze":
    if st.session_state.weak_index >= len(st.session_state.weak_list):
        st.success("All listed weaknesses processed. (Next: FP follow-ups / rating / exam.)")
        st.session_state.stage = "fp"
        st.rerun()

    current_weak = st.session_state.weak_list[st.session_state.weak_index]
    if not st.session_state.current_cloze:
        st.session_state.current_cloze = generate_cloze(
            st.session_state.selected["dotpoint"],
            current_weak,
            specificity=st.session_state.cloze_specificity,
        )

    st.markdown(f'<div class="box-label">Targeting: {current_weak}</div>', unsafe_allow_html=True)
    expected, user_vals, submitted = render_inline_cloze(
        st.session_state.current_cloze, key_prefix=f"clz_{st.session_state.weak_index}"
    )
    if submitted:
        correct, total, flags = score_cloze(expected, user_vals)
        st.session_state.last_cloze_result = (correct, total)
        if correct == total:
            st.success("Perfect.")
        else:
            wrongs = [str(i+1) for i, ok in enumerate(flags) if not ok]
            st.error(f"Incorrect blanks: {', '.join(wrongs)}.")
        # move to post-cloze rating stage
        st.session_state.stage = "post_cloze"
        st.rerun()

# ----- POST-CLOZE: rating + add weaknesses -> branch to next activity -----
elif st.session_state.stage == "post_cloze":
    # Show result
    if st.session_state.last_cloze_result:
        c, t = st.session_state.last_cloze_result
        st.info(f"Cloze score: {c}/{t}")

    # Rate understanding of this cloze
    colA, colB = st.columns([1,1])
    with colA:
        rating = st.slider("Rate your understanding of this topic (0–10)", 0, 10, 6, key="cloze_rating")
    with colB:
        more_w = st.text_input("Add more weaknesses (semicolon-separated):", key="more_wk")

    # Action: continue
    go = st.columns(3)[1].button("Continue", use_container_width=True)
    if go:
        # Merge new weaknesses (dedupe, keep ≤5 total)
        add_list = [w.strip() for w in (more_w or "").split(";") if w.strip()]
        merged = st.session_state.weak_list[:]
        for w in add_list:
            if w not in merged:
                merged.append(w)
        st.session_state.weak_list = merged[:5]

        # Branching:
        if rating <= 6:
            # Stay on same weakness; create a more specific cloze
            st.warning("Targeting with a more specific cloze.")
            st.session_state.cloze_specificity = min(1, st.session_state.cloze_specificity + 1)
            st.session_state.current_cloze = None
            st.session_state.stage = "cloze"
            st.rerun()
        else:
            # Progress to FP follow-ups for the same weakness (placeholder for now)
            st.session_state.cloze_specificity = 0
            st.session_state.current_cloze = None
            st.session_state.stage = "fp_followups"
            st.rerun()

# ----- FP FOLLOW-UPS (per-weakness; placeholder Qs now) -----
elif st.session_state.stage == "fp_followups":
    current_weak = st.session_state.weak_list[st.session_state.weak_index] if st.session_state.weak_list else "this topic"
    st.markdown(f"**Follow-up first-principles questions for:** _{current_weak}_")
    # Placeholder FP follow-ups (you can add AI generation later)
    qlist = [
        f"Derive the key relationship involved in {current_weak}, starting from definitions and conservation laws.",
        f"Explain how the mechanism would change for an extreme boundary case in {current_weak}."
    ]
    for q in qlist:
        st.write("• " + q)

    # After follow-ups, advance to next weakness (for now)
    if st.button("Next weakness"):
        st.session_state.weak_index += 1
        st.session_state.current_cloze = None
        st.session_state.cloze_specificity = 0
        # More weaknesses left? back to cloze; else back to FP (later: rating/exam stage)
        if st.session_state.weak_index < len(st.session_state.weak_list):
            st.session_state.stage = "cloze"
        else:
            st.success("All weaknesses cleared for now. (Next: overall rating / exam mode in a later step.)")
            st.session_state.stage = "fp"
        st.rerun()

# ----- Fallback -----
else:
    st.session_state.stage = "fp"
    st.rerun()
