# ===============================
# S Y L L A B U D D Y   (clean routes + fixed scroll + robust gestures)
# ===============================

# ---------- Section 0: Imports, Config, Styles ----------
import json
import pathlib
from typing import Dict, List, Set, Tuple, Optional

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Syllabuddy", layout="wide")

# Global CSS (title high, sticky review box, crisp cards)
st.markdown("""
<style>
  .block-container { max-width: 1280px; padding-top: 6px; margin: auto; }
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

  /* Fallback grid (if gestures unavailable) */
  .grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap:16px; }
  .card { border:2px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; position:relative; }
  .card.selected { border-color:#3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset; }
  .card-title { font-weight:800; margin-bottom:.35rem; color:#111; }
  .card-sub { color:#4b5563; font-size:.95rem; margin-bottom:.35rem; }

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

# ---------- gestures component (zero-build; require index.html) ----------
GESTURE_DIR = pathlib.Path(__file__).parent / "frontend_gestures" / "build"
GESTURES_OK = GESTURE_DIR.exists() and (GESTURE_DIR / "index.html").exists()

if GESTURES_OK:
    gesture_grid = components.declare_component("gesture_grid", path=str(GESTURE_DIR))

def render_gesture_grid(items: List[dict], key: str = "grid"):
    """
    Simple fallback: 
    - Single click = open 
    - Checkbox = select/unselect
    """
    event = None
    cols = st.columns(2)
    for i, it in enumerate(items):
        col = cols[i % 2]
        with col:
            sel = st.checkbox(
                it["title"], 
                value=it.get("selected", False), 
                key=f"{key}_chk_{i}"
            )
            if sel != it.get("selected", False):
                event = {"type": "select", "id": it["id"]}
            if st.button("Open", key=f"{key}_open_{i}", use_container_width=True):
                event = {"type": "open", "id": it["id"]}
    return event

# ---------- Section 1: Data Loaders ----------
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    # { Subject: { Module: { IQ: [dotpoints...] } } }
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

# ---------- Section 2: Global State / Helpers ----------
def ensure_state():
    st.session_state.setdefault("route", "home")
    st.session_state.setdefault("sel_dotpoints", set())  # {(s,m,iq,dp)}
    st.session_state.setdefault("focus_subject", None)
    st.session_state.setdefault("focus_module", None)    # (s,m)
    st.session_state.setdefault("focus_iq", None)        # (s,m,iq)
    st.session_state.setdefault("cram_mode", False)
    st.session_state.setdefault("prioritization_mode", False)
    st.session_state.setdefault("ai_weakness_text", "")
    st.session_state.setdefault("ai_strength_text", "")
    st.session_state.setdefault("ai_suggested", [])
    st.session_state.setdefault("ai_chosen", set())

ensure_state()
def go(route: str): st.session_state["route"] = route

# selection helpers
def add_all_modules(subject: str, on: bool):
    for m in MODS.get(subject, []): add_all_iqs(subject, m, on)
def add_all_iqs(subject: str, module: str, on: bool):
    for iq in IQS.get((subject, module), []): add_all_dps(subject, module, iq, on)
def add_all_dps(subject: str, module: str, iq: str, on: bool):
    for dp in DPS.get((subject, module, iq), []):
        item = (subject, module, iq, dp)
        (st.session_state["sel_dotpoints"].add(item) if on
         else st.session_state["sel_dotpoints"].discard(item))
def is_subject_selected(subject: str) -> bool:
    return any(s == subject for (s, m, iq, dp) in st.session_state["sel_dotpoints"])
def is_module_selected(subject: str, module: str) -> bool:
    return any((s == subject and m == module) for (s, m, iq, dp) in st.session_state["sel_dotpoints"])
def is_iq_selected(subject: str, module: str, iq: str) -> bool:
    return any((s == subject and m == module and i == iq) for (s, m, i, dp) in st.session_state["sel_dotpoints"])

# ---------- Section 3: Reusable UI ----------
def topbar(title: str, back_to: Optional[str] = None):
    c1, c2 = st.columns([1,6], vertical_alignment="center")
    with c1:
        if back_to:
            b1, b2 = st.columns([1,3])
            with b1:
                if st.button("⬅", key=f"arrow_{title}"):
                    go(back_to); st.stop()
            with b2:
                if st.button("Back", key=f"back_{title}", use_container_width=True):
                    go(back_to); st.stop()
    with c2:
        st.title(title)

def review_box(title: str, rows: List[tuple], apply_label: str,
               submit_label: str, back_to: str, after_submit_route: str):
    # Important: No extra Streamlit containers around this block → only inner list scrolls
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
            go(back_to); st.stop()
    with mid:
        if st.button(apply_label, type="primary"):
            st.session_state["sel_dotpoints"] = set(temp)
            st.success("Selection updated.")
    with right:
        if st.button(submit_label, type="primary"):
            st.session_state["sel_dotpoints"] = set(temp)
            go(after_submit_route); st.stop()
    st.markdown('</div>', unsafe_allow_html=True)  # foot
    st.markdown('</div>', unsafe_allow_html=True)  # wrap

# ---------- Section 4: Selection Engine ----------
def page_subjects(subject_next_route: str, review_route: str, back_to: Optional[str]):
    topbar("Choose Subject", back_to=back_to)
    st.caption("Click = **Open** · Long-press = **Select/Unselect** (blue border).")

    # Reset focus on entering subjects
    st.session_state["focus_subject"] = None
    st.session_state["focus_module"] = None
    st.session_state["focus_iq"] = None

    if not SUBJECTS:
        st.warning("No subjects found in syllabus.json.")
        return

    items = [{
        "id": f"subj::{s}",
        "title": s,
        "subtitle": f"{len(MODS.get(s, []))} modules",
        "selected": is_subject_selected(s),
    } for s in SUBJECTS]

    evt = render_gesture_grid(items, key="grid_subjects")
    if evt:
        et, eid = evt.get("type"), evt.get("id")
        _, subj = eid.split("::", 1)
        if et == "select":
            add_all_modules(subj, on=not is_subject_selected(subj))
            st.rerun()
        elif et == "open":
            st.session_state["focus_subject"] = subj
            go(subject_next_route); st.stop()

    st.write("")
    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go(review_route); st.stop()

def page_subject_drill(subject: str, next_route: str, back_to: str):
    topbar(f"{subject} — Modules", back_to=back_to)
    st.caption("Click = **Open** · Long-press = **Select/Unselect**. Dotpoints toggle on click.")

    # Modules grid
    items = [{
        "id": f"mod::{subject}::{m}",
        "title": m,
        "subtitle": f"{len(IQS.get((subject, m), []))} inquiry questions",
        "selected": is_module_selected(subject, m),
    } for m in MODS.get(subject, [])]

    evt = render_gesture_grid(items, key=f"grid_modules_{subject}")
    if evt:
        et, eid = evt.get("type"), evt.get("id")
        _, s, m = eid.split("::", 2)
        if et == "select":
            add_all_iqs(s, m, on=not is_module_selected(s, m)); st.rerun()
        elif et == "open":
            st.session_state["focus_module"] = (s, m); st.rerun()

    # IQs grid
    sm = st.session_state.get("focus_module")
    if sm and sm[0] == subject:
        s, m = sm
        st.subheader(f"IQs in {m}")
        items2 = [{
            "id": f"iq::{s}::{m}::{iq}",
            "title": iq,
            "subtitle": f"{len(DPS.get((s, m, iq), []))} dotpoints",
            "selected": is_iq_selected(s, m, iq),
        } for iq in IQS.get((s, m), [])]

        evt2 = render_gesture_grid(items2, key=f"grid_iqs_{s}_{m}")
        if evt2:
            et, eid = evt2.get("type"), evt2.get("id")
            _, ss, mm, ii = eid.split("::", 3)
            if et == "select":
                add_all_dps(ss, mm, ii, on=not is_iq_selected(ss, mm, ii)); st.rerun()
            elif et == "open":
                st.session_state["focus_iq"] = (ss, mm, ii); st.rerun()

    # Dotpoints — single-click toggle
    smi = st.session_state.get("focus_iq")
    if smi and smi[0] == subject:
        s, m, iq = smi
        st.subheader(f"Dotpoints in {iq}")
        colA, colB = st.columns(2)
        for i, dp in enumerate(DPS.get((s, m, iq), [])):
            selected = (s, m, iq, dp) in st.session_state["sel_dotpoints"]
            with (colA if i % 2 == 0 else colB):
                klass = "card selected" if selected else "card"
                st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
                st.markdown(f'<div class="card-title">{dp}</div>', unsafe_allow_html=True)
                if st.button("Toggle", key=f"toggle_dp_{s}_{m}_{iq}_{i}", use_container_width=True):
                    if selected:
                        st.session_state["sel_dotpoints"].discard((s, m, iq, dp))
                    else:
                        st.session_state["sel_dotpoints"].add((s, m, iq, dp))
                st.markdown('</div>', unsafe_allow_html=True)

    mid = st.columns([1,1,1])[1]
    with mid:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go(next_route); st.stop()

def page_review_selected(title: str, after_submit_route: str, back_to: str):
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box(
        title=title,
        rows=rows,
        apply_label="Apply changes",
        submit_label="Submit & Continue",
        back_to=back_to,
        after_submit_route=after_submit_route
    )

# ---------- Section 5: Home & Menus ----------
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

# ---------- Section 6: Cram Mode + Prioritization Review ----------
def page_cram_subjects():
    page_subjects("cram_subject_drill", "cram_review",
                  back_to=("srs_menu" if st.session_state["cram_mode"] else "select_subject_main"))

def page_cram_subject_drill():
    s = st.session_state.get("focus_subject")
    if not s:
        go("cram_subjects"); st.stop()
    page_subject_drill(s, "cram_review", "cram_subjects")

def page_cram_review():
    page_review_selected("Review Selection (Cram)", "cram_how", "cram_subjects")

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
            go("home"); st.stop()

# ---------- Section 7: AI Suggestions + Review ----------
def page_ai_select():
    topbar("AI selection — enter weaknesses", back_to="select_subject_main")
    st.write("Type what you struggle with; we’ll propose dotpoints that match (placeholder suggestions for now).")
    wk = st.text_area("Weaknesses", key="ai_wk2", height=150,
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
        go("ai_review"); st.stop()

def page_ai_review():
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.write("Click ✅ to keep or ❌ to remove. Green border = kept. The middle scrolls; header & footer stick.")

    chosen: Set[tuple] = set(st.session_state.get("ai_chosen", set()))
    suggestions = st.session_state.get("ai_suggested", [])

    # Boxed, inner-scrolling list
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
                # not appending -> removed next render
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
            go("cram_subjects"); st.stop()
    with mid:
        if st.button("Apply selection", type="primary"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            for it in chosen: st.session_state["sel_dotpoints"].add(it)
            st.success("Added to your selection.")
    with right:
        if st.button("Done"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            go("home"); st.stop()
    st.markdown('</div>', unsafe_allow_html=True)  # foot
    st.markdown('</div>', unsafe_allow_html=True)  # wrap

# ---------- Section 8: Router (no lambdas that call go() mid-render) ----------
def route_home(): page_home()
def route_srs_menu(): page_srs_menu()

def route_select_subject_main(): page_select_subject_main()

def route_cram_subjects(): page_cram_subjects()
def route_cram_subject_drill(): page_cram_subject_drill()
def route_cram_review(): page_cram_review()
def route_cram_how(): page_cram_how()

def route_srs_subjects():
    page_subjects("srs_subject_drill", "srs_review", back_to="srs_menu")

def route_srs_subject_drill():
    s = st.session_state.get("focus_subject")
    if not s:
        go("srs_subjects"); st.stop()
    page_subject_drill(s, "srs_review", "srs_subjects")

def route_srs_review():
    page_review_selected("Review Selection (SR)", "srs_menu", "srs_subjects")

def route_ai_select(): page_ai_select()
def route_ai_review(): page_ai_review()

ROUTES = {
    "home": route_home,
    "srs_menu": route_srs_menu,

    "select_subject_main": route_select_subject_main,

    "cram_subjects": route_cram_subjects,
    "cram_subject_drill": route_cram_subject_drill,
    "cram_review": route_cram_review,
    "cram_how": route_cram_how,

    "srs_subjects": route_srs_subjects,
    "srs_subject_drill": route_srs_subject_drill,
    "srs_review": route_srs_review,

    "ai_select": route_ai_select,
    "ai_review": route_ai_review,
}

ROUTES.get(st.session_state["route"], route_home)()
# ---------- Section 9: (engines to be added later) ----------
