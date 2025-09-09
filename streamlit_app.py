# ===============================
# S Y L L A B U D D Y — stable baseline (single-click, clean back, boxed review scroll)
# ===============================

import json
import os
from typing import Dict, List, Set, Tuple, Optional

import streamlit as st

st.set_page_config(page_title="Syllabuddy", layout="wide")

# ---------- Global CSS ----------
st.markdown("""
<style>
  .block-container { max-width: 1200px; padding-top: 6px; margin: auto; }
  header {visibility: hidden;}
  #MainMenu {visibility: hidden;} footer {visibility: hidden;}

  /* Top bar */
  .topbar { display:flex; align-items:center; justify-content:space-between; margin: 0 0 8px 0; }
  .topbar-left { display:flex; align-items:center; gap:8px; }

  /* Buttons */
  .btn { padding:8px 12px; border-radius:10px; border:1px solid #d1d5db; background:#fff; font-weight:600; }
  .btn.primary { background:#3b82f6; color:#fff; border-color:#2563eb; }
  .btn.ghost { background:#f8fafc; }
  .btn.warn { background:#fee2e2; color:#991b1b; border-color:#fecaca; }

  /* Cards / grid */
  .grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(320px,1fr)); gap:16px; }
  .card { border:2px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; position:relative; }
  .card.selected { border-color:#3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset; }
  .card-title { font-weight:800; margin-bottom:.35rem; color:#111; }
  .card-sub { color:#4b5563; font-size:.95rem; margin-bottom:.5rem; }

  /* Review box: only middle scrolls */
  .scroll-wrap {
    display:flex; flex-direction:column; height:72vh;
    border:1px solid #e5e7eb; border-radius:12px; overflow:hidden; background:#fff;
  }
  .scroll-head {
    padding:12px 14px; font-weight:900; background:#f8fafc; border-bottom:1px solid #e5e7eb;
    position: sticky; top: 0; z-index: 2;
  }
  .scroll-body { flex:1; overflow:auto; padding:12px 14px; }
  .scroll-foot {
    padding:12px 14px; background:#f8fafc; border-top:1px solid #e5e7eb;
    position: sticky; bottom: 0; z-index: 2;
  }

  .dp-item {
    display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; margin-bottom:10px; background:#fff;
  }
  .dp-item.selected { border-color:#16a34a; box-shadow: inset 0 0 0 2px rgba(22,163,74,.2); }
</style>
""", unsafe_allow_html=True)

# ---------- Data ----------
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    # { Subject: { Module: { IQ: [dotpoints...] } } }
    if not os.path.exists("syllabus.json"):
        # minimal fallback so the app always runs
        return {
            "Biology": {
                "Module 6: Genetic Change": {
                    "IQ1: Mutations": [
                        "Describe point vs frameshift mutations",
                        "Explain mutagens and mutation rates"
                    ],
                    "IQ2: Biotechnology": [
                        "Outline PCR steps and applications",
                        "Summarise CRISPR-Cas9 mechanism"
                    ]
                }
            },
            "Chemistry": {
                "Module 5: Equilibrium": {
                    "IQ1: Le Chatelier": [
                        "Predict shifts for concentration, pressure, temperature changes",
                        "Relate Kc to reaction quotient Q"
                    ]
                }
            }
        }
    with open("syllabus.json", "r") as f:
        return json.load(f)

def explode_syllabus(data: Dict):
    subjects = list(data.keys())
    modules_by_subject = {s: list(data[s].keys()) for s in subjects}
    iqs_by_subject_module = {}
    dps_by_smi = {}
    for s in subjects:
        for m in data[s]:
            iqs = list(data[s][m].keys())
            iqs_by_subject_module[(s, m)] = iqs
            for iq in iqs:
                dps_by_smi[(s, m, iq)] = list(data[s][m][iq])
    return subjects, modules_by_subject, iqs_by_subject_module, dps_by_smi

SYL = load_syllabus()
SUBJECTS, MODS, IQS, DPS = explode_syllabus(SYL)

# ---------- State ----------
def ensure_state():
    st.session_state.setdefault("route", "home")

    # Selection & focus
    st.session_state.setdefault("sel_dotpoints", set())  # {(s,m,iq,dp)}
    st.session_state.setdefault("focus_subject", None)
    st.session_state.setdefault("focus_module", None)    # (s,m)
    st.session_state.setdefault("focus_iq", None)        # (s,m,iq)

    # Modes
    st.session_state.setdefault("cram_mode", False)
    st.session_state.setdefault("prioritization_mode", False)

    # AI selection scratch
    st.session_state.setdefault("ai_weakness_text", "")
    st.session_state.setdefault("ai_strength_text", "")
    st.session_state.setdefault("ai_suggested", [])
    st.session_state.setdefault("ai_chosen", set())

ensure_state()

def go(route: str):
    st.session_state["route"] = route
    st.rerun()

# ---------- Selection Helpers ----------
def is_subject_selected(subject: str) -> bool:
    return any(s == subject for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_module_selected(subject: str, module: str) -> bool:
    return any((s == subject and m == module) for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_iq_selected(subject: str, module: str, iq: str) -> bool:
    return any((s == subject and m == module and i == iq) for (s, m, i, dp) in st.session_state["sel_dotpoints"])

def add_all_modules(subject: str, on: bool):
    for m in MODS.get(subject, []):
        add_all_iqs(subject, m, on)

def add_all_iqs(subject: str, module: str, on: bool):
    for iq in IQS.get((subject, module), []):
        add_all_dps(subject, module, iq, on)

def add_all_dps(subject: str, module: str, iq: str, on: bool):
    for dp in DPS.get((subject, module, iq), []):
        item = (subject, module, iq, dp)
        if on:
            st.session_state["sel_dotpoints"].add(item)
        else:
            st.session_state["sel_dotpoints"].discard(item)

# ---------- UI Bits ----------
def topbar(title: str, back_to: Optional[str] = None):
    # Inline arrow + Back button; title high up
    c1, c2 = st.columns([1,6], vertical_alignment="center")
    with c1:
        if back_to:
            b1, b2 = st.columns([1,3])
            with b1:
                if st.button("⬅", key=f"arrow_{title}"):
                    go(back_to)
            with b2:
                if st.button("Back", key=f"back_{title}", use_container_width=True):
                    go(back_to)
    with c2:
        st.title(title)

def subject_cards(subjects: List[str], key_prefix: str, back_to: Optional[str]):
    if back_to:
        topbar("Choose Subject", back_to=back_to)
    else:
        st.title("Choose Subject")
    st.caption("Open drills down. Use Select/Unselect to include/exclude.")
    cols = st.columns(2)
    for i, s in enumerate(subjects):
        with cols[i % 2]:
            selected = is_subject_selected(s)
            css = "card selected" if selected else "card"
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">{s}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-sub">{len(MODS.get(s, []))} modules</div>', unsafe_allow_html=True)
            a, b = st.columns([3,2])
            with a:
                if st.button("Open", key=f"{key_prefix}_open_{i}", use_container_width=True):
                    st.session_state["focus_subject"] = s
                    if key_prefix == "cram": go("cram_modules")
                    else:                    go("srs_modules")
            with b:
                if st.button(("Unselect" if selected else "Select"),
                             key=f"{key_prefix}_sel_{i}", use_container_width=True):
                    add_all_modules(s, on=not selected)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def module_cards(subject: str, key_prefix: str, back_to: str):
    topbar(f"{subject} — Modules", back_to=back_to)
    st.caption("Open drills down. Use Select/Unselect to include/exclude.")
    modules = MODS.get(subject, [])
    cols = st.columns(2)
    for i, m in enumerate(modules):
        with cols[i % 2]:
            selected = is_module_selected(subject, m)
            css = "card selected" if selected else "card"
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">{m}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-sub">{len(IQS.get((subject, m), []))} inquiry questions</div>', unsafe_allow_html=True)
            a, b = st.columns([3,2])
            with a:
                if st.button("Open", key=f"{key_prefix}_mod_open_{i}", use_container_width=True):
                    st.session_state["focus_module"] = (subject, m)
                    if key_prefix == "cram": go("cram_iqs")
                    else:                    go("srs_iqs")
            with b:
                if st.button(("Unselect" if selected else "Select"),
                             key=f"{key_prefix}_mod_sel_{i}", use_container_width=True):
                    add_all_iqs(subject, m, on=not selected)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def iq_cards(subject: str, module: str, key_prefix: str, back_to: str):
    topbar(f"{subject} → {module} — IQs", back_to=back_to)
    st.caption("Open drills down. Use Select/Unselect to include/exclude.")
    iqs = IQS.get((subject, module), [])
    cols = st.columns(2)
    for i, iq in enumerate(iqs):
        with cols[i % 2]:
            selected = is_iq_selected(subject, module, iq)
            css = "card selected" if selected else "card"
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">{iq}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="card-sub">{len(DPS.get((subject, module, iq), []))} dotpoints</div>', unsafe_allow_html=True)
            a, b = st.columns([3,2])
            with a:
                if st.button("Open", key=f"{key_prefix}_iq_open_{i}", use_container_width=True):
                    st.session_state["focus_iq"] = (subject, module, iq)
                    if key_prefix == "cram": go("cram_dotpoints")
                    else:                    go("srs_dotpoints")
            with b:
                if st.button(("Unselect" if selected else "Select"),
                             key=f"{key_prefix}_iq_sel_{i}", use_container_width=True):
                    add_all_dps(subject, module, iq, on=not selected)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def dotpoint_cards(subject: str, module: str, iq: str, key_prefix: str, back_to: str):
    topbar(f"{subject} → {module} → {iq} — Dotpoints", back_to=back_to)
    st.caption("Click Toggle to include/exclude dotpoints.")
    dps = DPS.get((subject, module, iq), [])
    colA, colB = st.columns(2)
    for i, dp in enumerate(dps):
        selected = (subject, module, iq, dp) in st.session_state["sel_dotpoints"]
        with (colA if i % 2 == 0 else colB):
            css = "card selected" if selected else "card"
            st.markdown(f'<div class="{css}">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-title">{dp}</div>', unsafe_allow_html=True)
            if st.button("Toggle", key=f"{key_prefix}_dp_toggle_{i}", use_container_width=True):
                item = (subject, module, iq, dp)
                if selected: st.session_state["sel_dotpoints"].discard(item)
                else:        st.session_state["sel_dotpoints"].add(item)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("cram_review" if key_prefix == "cram" else "srs_review")

def review_box(title: str, rows: List[tuple], apply_label: str,
               submit_label: str, back_to: str, after_submit_route: str):
    # Boxed, inner-scrolling list (no parent wrappers!)
    topbar(title, back_to=back_to)
    st.markdown('<div class="scroll-wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="scroll-head">{title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="scroll-body">', unsafe_allow_html=True)

    temp = set(rows)
    for idx, (s, m, iq, dp) in enumerate(rows):
        sel = (s, m, iq, dp) in temp
        klass = "dp-item selected" if sel else "dp-item"
        st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
        st.write(f"**{s} → {m} → {iq}** — {dp}")
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("✅ Keep", key=f"keep_{idx}", use_container_width=True):
                temp.add((s, m, iq, dp))
        with c2:
            if st.button("❌ Remove", key=f"drop_{idx}", use_container_width=True):
                temp.discard((s, m, iq, dp))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # body

    st.markdown('<div class="scroll-foot">', unsafe_allow_html=True)
    left, mid, right = st.columns([1,1,1])
    with left:
        if st.button("← Back (keep selection)"):
            go(back_to)
    with mid:
        if st.button(apply_label, type="primary"):
            st.session_state["sel_dotpoints"] = set(temp)
            st.success("Selection updated.")
    with right:
        if st.button(submit_label, type="primary"):
            st.session_state["sel_dotpoints"] = set(temp)
            go(after_submit_route)
    st.markdown('</div>', unsafe_allow_html=True)  # foot
    st.markdown('</div>', unsafe_allow_html=True)  # wrap

# ---------- Pages ----------
def page_home():
    st.title("Syllabuddy")
    st.write("Stay on track with spaced repetition, prioritised cramming, and targeted practice.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Spaced Repetition", use_container_width=True):
            go("srs_menu")
    with c2:
        if st.button("Select Subject", use_container_width=True):
            go("select_subject_main")

def page_srs_menu():
    topbar("Spaced Repetition", back_to="home")
    due_count = max(1, len(st.session_state["sel_dotpoints"]))
    st.write(f"**All (Today):** {due_count} dotpoints due")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Start: All (SR order)", use_container_width=True, type="primary"):
            st.info("SRS Engine (All) — placeholder for now.")
    with c2:
        if st.button("Choose Subject (SR)", use_container_width=True):
            st.session_state["cram_mode"] = False
            go("srs_subjects")
    with c3:
        if st.button("Cram Mode (mass select)", use_container_width=True):
            st.session_state["cram_mode"] = True
            st.session_state["prioritization_mode"] = False
            go("cram_subjects")

def page_select_subject_main():
    topbar("Select Subject", back_to="home")
    st.write("Choose subjects/modules/IQs/dotpoints or try AI-based selection.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Manual selection", use_container_width=True, type="primary"):
            st.session_state["cram_mode"] = True
            st.session_state["prioritization_mode"] = False
            go("cram_subjects")
    with c2:
        if st.button("AI selection (enter weaknesses)", use_container_width=True):
            go("ai_select")

# ---- Manual selection (CRAM) ----
def page_cram_subjects():
    subject_cards(SUBJECTS, key_prefix="cram",
                  back_to=("srs_menu" if st.session_state["cram_mode"] else "select_subject_main"))
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("cram_review")

def page_cram_modules():
    s = st.session_state.get("focus_subject")
    if not s: go("cram_subjects")
    module_cards(s, key_prefix="cram", back_to="cram_subjects")

def page_cram_iqs():
    sm = st.session_state.get("focus_module")
    if not sm: go("cram_modules")
    s, m = sm
    iq_cards(s, m, key_prefix="cram", back_to="cram_modules")

def page_cram_dotpoints():
    smi = st.session_state.get("focus_iq")
    if not smi: go("cram_iqs")
    s, m, iq = smi
    dotpoint_cards(s, m, iq, key_prefix="cram", back_to="cram_iqs")

def page_cram_review():
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box("Review Selection (Cram)", rows, "Apply changes", "Submit & Continue",
               back_to="cram_subjects", after_submit_route="cram_how")

def page_cram_how():
    topbar("How to review", back_to="cram_review")
    mode = st.radio("Choose order:", ["SR order (spaced repetition)", "Prioritization (based on strengths/weaknesses)"])
    if mode.startswith("Prioritization"):
        st.subheader("Tell the AI")
        st.session_state["ai_weakness_text"] = st.text_area("What topics are you struggling with most?",
                                                            height=120, placeholder="e.g., diffusion vs osmosis; rates; energy changes")
        st.session_state["ai_strength_text"] = st.text_area("Where are your strengths?",
                                                            height=100, placeholder="e.g., definitions; diagrams")
        st.caption("These can flow into your tutor screens as initial weaknesses/strengths.")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Proceed", type="primary", use_container_width=True):
            st.session_state["prioritization_mode"] = mode.startswith("Prioritization")
            go("home")

# ---- SRS choose subject (same UI, different back) ----
def page_srs_subjects():
    subject_cards(SUBJECTS, key_prefix="srs", back_to="srs_menu")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go("srs_review")

def page_srs_modules():
    s = st.session_state.get("focus_subject")
    if not s: go("srs_subjects")
    module_cards(s, key_prefix="srs", back_to="srs_subjects")

def page_srs_iqs():
    sm = st.session_state.get("focus_module")
    if not sm: go("srs_modules")
    s, m = sm
    iq_cards(s, m, key_prefix="srs", back_to="srs_modules")

def page_srs_dotpoints():
    smi = st.session_state.get("focus_iq")
    if not smi: go("srs_iqs")
    s, m, iq = smi
    dotpoint_cards(s, m, iq, key_prefix="srs", back_to="srs_iqs")

def page_srs_review():
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box("Review Selection (SR)", rows, "Apply changes", "Submit & Continue",
               back_to="srs_subjects", after_submit_route="srs_menu")

# ---- AI selection (placeholder) ----
def page_ai_select():
    topbar("AI selection — enter weaknesses", back_to="select_subject_main")
    st.write("Type what you struggle with; we’ll propose dotpoints that match (placeholder suggestions for now).")
    st.session_state["ai_weakness_text"] = st.text_area("Weaknesses", key="ai_wk2", height=150,
                      placeholder="e.g., equilibrium constants; vectors; cell transport")
    if st.button("Get suggestions", type="primary"):
        suggestions = []
        for s in SUBJECTS:
            for m in MODS.get(s, []):
                for iq in IQS.get((s, m), []):
                    for dp in DPS.get((s, m, iq), []):
                        suggestions.append((s, m, iq, dp))
        st.session_state["ai_suggested"] = suggestions[:30]
        st.session_state["ai_chosen"] = set()
        go("ai_review")

def page_ai_review():
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.write("Click ✅ to keep or ❌ to remove. Green border = kept. The middle scrolls; header & footer stick.")

    chosen: Set[tuple] = set(st.session_state.get("ai_chosen", set()))
    suggestions = st.session_state.get("ai_suggested", [])

    st.markdown('<div class="scroll-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="scroll-head">AI suggested dotpoints</div>', unsafe_allow_html=True)
    st.markdown('<div class="scroll-body">', unsafe_allow_html=True)

    temp = []
    for idx, item in enumerate(suggestions):
        s, m, iq, dp = item
        sel = item in chosen
        klass = "dp-item selected" if sel else "dp-item"
        st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
        st.write(f"**{s} → {m} → {iq}** — {dp}")
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("✅ Keep", key=f"ai_keep_{idx}", use_container_width=True):
                chosen.add(item)
        with c2:
            if st.button("❌ Remove", key=f"ai_drop_{idx}", use_container_width=True):
                st.markdown('</div>', unsafe_allow_html=True)
                continue
        st.markdown('</div>', unsafe_allow_html=True)
        temp.append(item)

    st.markdown('</div>', unsafe_allow_html=True)  # body

    st.markdown('<div class="scroll-foot">', unsafe_allow_html=True)
    left, mid, right = st.columns([1,1,1])
    with left:
        if st.button("← Back to Choose Subject"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            go("cram_subjects")
    with mid:
        if st.button("Apply selection", type="primary"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            for it in chosen:
                st.session_state["sel_dotpoints"].add(it)
            st.success("Added selected dotpoints.")
    with right:
        if st.button("Done"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            go("home")
    st.markdown('</div>', unsafe_allow_html=True)  # foot
    st.markdown('</div>', unsafe_allow_html=True)  # wrap

# ---------- Router ----------
ROUTES = {
    "home": page_home,

    "srs_menu": page_srs_menu,
    "srs_subjects": page_srs_subjects,
    "srs_modules": page_srs_modules,
    "srs_iqs": page_srs_iqs,
    "srs_dotpoints": page_srs_dotpoints,
    "srs_review": page_srs_review,

    "select_subject_main": page_select_subject_main,
    "cram_subjects": page_cram_subjects,
    "cram_modules": page_cram_modules,
    "cram_iqs": page_cram_iqs,
    "cram_dotpoints": page_cram_dotpoints,
    "cram_review": page_cram_review,
    "cram_how": page_cram_how,

    "ai_select": page_ai_select,
    "ai_review": page_ai_review,
}

ROUTES.get(st.session_state["route"], page_home)()
