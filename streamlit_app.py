# ===============================
# S Y L L A B U D D Y   (sections)
# - Section 0: Imports, Config, Styles
# - Section 1: Data Loaders
# - Section 2: Global State / Helpers
# - Section 3: Reusable UI (Topbar, Cards, Grids)
# - Section 4: Selection Engine (Subjects → Modules → IQs → Dotpoints)
# - Section 5: Home & Menus (Home, SRS menu, Select Subject)
# - Section 6: Cram Mode + Prioritization Review
# - Section 7: AI Suggestions (weakness-based) + Review
# - Section 8: Router
# - Section 9: (PLACEHOLDERS) SRS Engine, Exam Mode, Tutor Flow
# ===============================

# ---------- Section 0: Imports, Config, Styles ----------
import json
from typing import Dict, List, Tuple, Set
import streamlit as st

st.set_page_config(page_title="Syllabuddy", layout="wide")

# Make the page title sit high (less padding), keep everything crisp
st.markdown("""
<style>
  .block-container { max-width: 1280px; padding-top: 8px; margin: auto; } /* tighter top */
  header {visibility: hidden;}
  #MainMenu {visibility: hidden;} footer {visibility: hidden;}

  /* Top bar (back arrow + back button inline) */
  .topbar { display:flex; align-items:center; justify-content:space-between; margin: 2px 0 8px 0; }
  .topbar-left { display:flex; align-items:center; gap:8px; }

  /* Buttons */
  .btn { padding:8px 12px; border-radius:10px; border:1px solid #d1d5db; background:#fff; font-weight:600; }
  .btn.primary { background:#3b82f6; color:#fff; border-color:#2563eb; }
  .btn.ghost { background:#f8fafc; }
  .btn.warn { background:#fee2e2; color:#991b1b; border-color:#fecaca; }

  /* Big action buttons on Home */
  .big-btn {
    display:inline-block; padding:18px 24px; border-radius:14px; border:1px solid #d1d5db;
    background:#f8fafc; text-decoration:none; color:#111; font-weight:700; width:100%; text-align:center;
  }
  .big-btn:hover { background:#eef2ff; border-color:#93c5fd; }

  /* Cards + grid */
  .grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); gap:16px; }
  .card {
    border:2px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; position:relative;
  }
  .card.selected { border-color:#3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset; }
  .card-title { font-weight:800; margin-bottom:.35rem; }
  .card-sub { color:#4b5563; font-size:.95rem; margin-bottom:.35rem; }
  .card-actions { display:flex; gap:8px; flex-wrap:wrap; }

  /* Sticky scroll container (Review screens) */
  .scroll-wrap { display:flex; flex-direction:column; height:70vh; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden; }
  .scroll-head { padding:12px 14px; font-weight:900; background:#f8fafc; border-bottom:1px solid #e5e7eb; }
  .scroll-body { flex:1; overflow:auto; padding:12px 14px; }
  .scroll-foot { padding:12px 14px; background:#f8fafc; border-top:1px solid #e5e7eb; }

  /* Review dotpoint item */
  .dp-item { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; margin-bottom:10px; }
  .dp-item.selected { border-color:#16a34a; box-shadow: inset 0 0 0 2px rgba(22,163,74,.2); }

  /* Tiny badges */
  .badge { display:inline-block; font-size:.9rem; padding:4px 8px; background:#eef2ff; border:1px solid #c7d2fe; border-radius:999px; }
</style>
""", unsafe_allow_html=True)

# ---------- Section 1: Data Loaders ----------
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    # Structure: { Subject: { Module: { IQ: [dotpoints...] } } }
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

    # selections (persist across the app)
    st.session_state.setdefault("sel_dotpoints", set())   # set of (s,m,iq,dp)

    # selection browsing focus (one subject at a time)
    st.session_state.setdefault("focus_subject", None)
    st.session_state.setdefault("focus_module", None)     # (s, m)
    st.session_state.setdefault("focus_iq", None)         # (s, m, iq)

    # for cram/prioritization paths
    st.session_state.setdefault("cram_mode", False)
    st.session_state.setdefault("prioritization_mode", False)

    # AI suggestion buffers
    st.session_state.setdefault("ai_weakness_text", "")
    st.session_state.setdefault("ai_strength_text", "")
    st.session_state.setdefault("ai_suggested", [])       # list of (s,m,iq,dp)
    st.session_state.setdefault("ai_chosen", set())       # set of (s,m,iq,dp)

ensure_state()

def go(route: str):
    st.session_state["route"] = route

# ---------- Section 3: Reusable UI (Topbar, Cards, Grids) ----------
def topbar(title: str, back_to: str | None = None):
    c1, c2 = st.columns([1,6], vertical_alignment="center")
    with c1:
        if back_to:
            # Arrow and back are inline on the left
            colL, colR = st.columns([1,3])
            with colL:
                if st.button("⬅", key=f"arrow_{title}"):
                    go(back_to)
                    st.stop()
            with colR:
                if st.button("Back", key=f"back_{title}", use_container_width=True):
                    go(back_to)
                    st.stop()
    with c2:
        st.title(title)

def card(title: str, sub: str, selected: bool, open_key: str, select_key: str) -> str | None:
    klass = "card selected" if selected else "card"
    st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card-sub">{sub}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Open", key=open_key, use_container_width=True):
            st.markdown("</div>", unsafe_allow_html=True)
            return "open"
    with c2:
        if st.button("Select / Unselect", key=select_key, use_container_width=True):
            st.markdown("</div>", unsafe_allow_html=True)
            return "toggle"
    st.markdown("</div>", unsafe_allow_html=True)
    return None

# helpers to add/remove full levels
def add_all_modules(subject: str, on: bool):
    for m in MODS[subject]:
        add_all_iqs(subject, m, on)

def add_all_iqs(subject: str, module: str, on: bool):
    for iq in IQS[(subject, module)]:
        add_all_dps(subject, module, iq, on)

def add_all_dps(subject: str, module: str, iq: str, on: bool):
    for dp in DPS[(subject, module, iq)]:
        item = (subject, module, iq, dp)
        if on:
            st.session_state["sel_dotpoints"].add(item)
        else:
            st.session_state["sel_dotpoints"].discard(item)

def is_subject_selected(subject: str) -> bool:
    return any(s == subject for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_module_selected(subject: str, module: str) -> bool:
    return any((s == subject and m == module) for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_iq_selected(subject: str, module: str, iq: str) -> bool:
    return any((s == subject and m == module and i == iq) for (s, m, i, dp) in st.session_state["sel_dotpoints"])

# ---------- Section 4: Selection Engine ----------
def page_subjects(subject_next_route: str, review_route: str, back_to: str | None):
    """Subjects-only page. Drill into ONE subject at a time.
       Selections persist across subjects; review page aggregates all.
    """
    topbar("Choose Subject", back_to=back_to)
    st.write("Open a subject to pick modules/IQs/dotpoints, or toggle entire subject selection.")

    # ensure focus cleared when entering subjects page
    st.session_state["focus_subject"] = None
    st.session_state["focus_module"] = None
    st.session_state["focus_iq"] = None

    st.markdown('<div class="grid">', unsafe_allow_html=True)
    for s in SUBJECTS:
        selected = is_subject_selected(s)
        action = card(
            title=s,
            sub=f"{len(MODS[s])} modules",
            selected=selected,
            open_key=f"open_subj_{s}",
            select_key=f"toggle_subj_{s}",
        )
        if action == "open":
            st.session_state["focus_subject"] = s
            go(subject_next_route)
            st.stop()
        elif action == "toggle":
            # if already selected, unselect entire tree; else select all
            add_all_modules(s, on=not selected)
    st.markdown('</div>', unsafe_allow_html=True)

    # review (aggregated across subjects)
    st.write("")
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go(review_route)
            st.stop()

def page_subject_drill(subject: str, next_route: str, back_to: str):
    """Inside one subject: show modules → open IQs → open dotpoints"""
    topbar(f"{subject} — Modules", back_to=back_to)

    # MODULES
    st.subheader("Modules")
    st.markdown('<div class="grid">', unsafe_allow_html=True)
    for m in MODS[subject]:
        selected = is_module_selected(subject, m)
        action = card(
            title=m,
            sub=f"{len(IQS[(subject, m)])} inquiry questions",
            selected=selected,
            open_key=f"open_mod_{subject}_{m}",
            select_key=f"toggle_mod_{subject}_{m}",
        )
        if action == "open":
            st.session_state["focus_module"] = (subject, m)
        elif action == "toggle":
            add_all_iqs(subject, m, on=not selected)
    st.markdown('</div>', unsafe_allow_html=True)

    # IQs for focused module
    sm = st.session_state.get("focus_module")
    if sm and sm[0] == subject:
        s, m = sm
        st.subheader(f"IQs in {m}")
        st.markdown('<div class="grid">', unsafe_allow_html=True)
        for iq in IQS[(s, m)]:
            selected = is_iq_selected(s, m, iq)
            action = card(
                title=iq,
                sub=f"{len(DPS[(s, m, iq)])} dotpoints",
                selected=selected,
                open_key=f"open_iq_{s}_{m}_{iq}",
                select_key=f"toggle_iq_{s}_{m}_{iq}",
            )
            if action == "open":
                st.session_state["focus_iq"] = (s, m, iq)
            elif action == "toggle":
                add_all_dps(s, m, iq, on=not selected)
        st.markdown('</div>', unsafe_allow_html=True)

    # Dotpoints for focused IQ
    smi = st.session_state.get("focus_iq")
    if smi and smi[0] == subject:
        s, m, iq = smi
        st.subheader(f"Dotpoints in {iq}")
        colA, colB = st.columns(2)
        all_dps = DPS[(s, m, iq)]
        for i, dp in enumerate(all_dps):
            selected = (s, m, iq, dp) in st.session_state["sel_dotpoints"]
            with (colA if i % 2 == 0 else colB):
                klass = "card selected" if selected else "card"
                st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
                st.markdown(f'<div class="card-title">{dp}</div>', unsafe_allow_html=True)
                if st.button("Select / Unselect", key=f"toggle_dp_{s}_{m}_{iq}_{i}", use_container_width=True):
                    if selected:
                        st.session_state["sel_dotpoints"].discard((s, m, iq, dp))
                    else:
                        st.session_state["sel_dotpoints"].add((s, m, iq, dp))
                st.markdown('</div>', unsafe_allow_html=True)

    # sticky submit
    st.write("")
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("Review selected dotpoints", type="primary", use_container_width=True):
            go(next_route)
            st.stop()

def page_review_selected(title: str, after_submit_route: str, back_to: str):
    """Sticky header, scrollable dotpoint list, sticky submit bar; selections persist across app."""
    topbar(title, back_to=back_to)

    # Snapshot current selection list
    dplist = sorted(list(st.session_state["sel_dotpoints"]))

    st.markdown('<div class="scroll-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="scroll-head">Selected dotpoints</div>', unsafe_allow_html=True)
    st.markdown('<div class="scroll-body">', unsafe_allow_html=True)

    # Make a temp set to allow removing items in this view
    temp = set(dplist)
    for idx, (s, m, iq, dp) in enumerate(dplist):
        sel = (s, m, iq, dp) in temp
        klass = "dp-item selected" if sel else "dp-item"
        st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
        st.write(f"**{s} → {m} → {iq}** — {dp}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Keep", key=f"keep_{idx}", use_container_width=True):
                temp.add((s, m, iq, dp))
        with c2:
            if st.button("❌ Remove", key=f"drop_{idx}", use_container_width=True):
                temp.discard((s, m, iq, dp))
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # end body

    st.markdown('<div class="scroll-foot">', unsafe_allow_html=True)
    left, mid, right = st.columns([1,1,1])
    with left:
        if st.button("← Back (keep selection)"):
            # keep current selection set (no change), go back
            go(back_to)
            st.stop()
    with mid:
        if st.button("Apply changes", type="primary"):
            # write temp back to global selection
            st.session_state["sel_dotpoints"] = set(temp)
            st.success("Selection updated.")
    with right:
        if st.button("Submit & Continue", type="primary"):
            st.session_state["sel_dotpoints"] = set(temp)
            go(after_submit_route)
            st.stop()
    st.markdown('</div>', unsafe_allow_html=True)  # end foot
    st.markdown('</div>', unsafe_allow_html=True)  # end wrap

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
    # Placeholder due count — later wire to SRS engine
    due_count = max(1, len(st.session_state["sel_dotpoints"]))
    st.write(f"**All (Today):** {due_count} dotpoints due")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Start: All (SR order)", use_container_width=True, type="primary"):
            # TODO: route to SRS Engine with 'all'
            st.info("SRS Engine (All) is a placeholder.")
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
    # Subjects page for cram selection
    page_subjects(
        subject_next_route="cram_subject_drill",
        review_route="cram_review",
        back_to="srs_menu" if st.session_state["cram_mode"] else "select_subject_main",
    )

def page_cram_subject_drill():
    s = st.session_state.get("focus_subject")
    if not s:
        go("cram_subjects"); return
    page_subject_drill(
        subject=s,
        next_route="cram_review",
        back_to="cram_subjects",
    )

def page_cram_review():
    # After selecting dotpoints across any subjects, confirm list then choose "how to review"
    page_review_selected(
        title="Review Selection (Cram)",
        after_submit_route="cram_how",
        back_to="cram_subjects",
    )

def page_cram_how():
    topbar("How to review", back_to="cram_review")
    mode = st.radio("Choose order:", ["SR order (spaced repetition)", "Prioritization (based on strengths/weaknesses)"])
    if mode.startswith("Prioritization"):
        st.subheader("Tell the AI")
        st.session_state["ai_weakness_text"] = st.text_area("What topics are you struggling with most?", height=120, placeholder="e.g., diffusion vs osmosis; rates; energy changes")
        st.session_state["ai_strength_text"] = st.text_area("Where are your strengths?", height=100, placeholder="e.g., definitions; diagrams")
        st.caption("These can flow into your tutor screens as initial weaknesses/strengths.")

    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button("Proceed", type="primary", use_container_width=True):
            st.session_state["prioritization_mode"] = mode.startswith("Prioritization")
            # TODO: Route to Tutor/SRS based on mode. For now, return home.
            st.success(f"Mode: {mode}")
            go("home")

# ---------- Section 7: AI Suggestions + Review ----------
def page_ai_select():
    topbar("AI selection — enter weaknesses", back_to="select_subject_main")
    st.write("Type what you struggle with; we’ll propose dotpoints that match (placeholder suggestions for now).")
    wk = st.text_area("Weaknesses", key="ai_wk2", height=150, placeholder="e.g., equilibrium constants; vectors; cell transport")
    if st.button("Get suggestions", type="primary"):
        # Placeholder suggestions: first 30 dotpoints across syllabus
        suggestions = []
        for s in SUBJECTS:
            for m in MODS[s]:
                for iq in IQS[(s, m)]:
                    for dp in DPS[(s, m, iq)]:
                        suggestions.append((s, m, iq, dp))
        st.session_state["ai_suggested"] = suggestions[:30]
        st.session_state["ai_chosen"] = set()
        go("ai_review")

def page_ai_review():
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.write("Click ✅ to keep or ❌ to remove. Green border = kept. The middle scrolls; header & footer stick.")

    # We keep a chosen set across runs
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
                # Do not append to temp => disappears on next render
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
            st.stop()
    with mid:
        if st.button("Apply selection", type="primary"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            # Copy chosen into the global selection set
            for it in chosen:
                st.session_state["sel_dotpoints"].add(it)
            st.success("Added selected dotpoints to your selection.")
    with right:
        if st.button("Done"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            go("home")
            st.stop()
    st.markdown('</div>', unsafe_allow_html=True)  # foot
    st.markdown('</div>', unsafe_allow_html=True)  # wrap

# ---------- Section 8: Router ----------
ROUTES = {
    "home": page_home,
    "srs_menu": page_srs_menu,

    # Manual selection flows
    "select_subject_main": page_select_subject_main,   # Home → Select Subject
    "cram_subjects": page_cram_subjects,               # subjects-only page
    "cram_subject_drill": page_cram_subject_drill,     # single subject’s modules/IQs/DPs
    "cram_review": page_cram_review,                   # sticky review
    "cram_how": page_cram_how,                         # SR order vs Prioritization

    # SRS choose subject (same UI, different back)
    "srs_subjects": lambda: page_subjects("srs_subject_drill", "srs_review", back_to="srs_menu"),
    "srs_subject_drill": lambda: page_subject_drill(
        st.session_state.get("focus_subject"), "srs_review", "srs_subjects"
    ) if st.session_state.get("focus_subject") else go("srs_subjects"),
    "srs_review": lambda: page_review_selected("Review Selection (SR)", "srs_menu", "srs_subjects"),

    # AI selection
    "ai_select": page_ai_select,
    "ai_review": page_ai_review,
}

ROUTES[st.session_state["route"]]()

# ---------- Section 9: PLACEHOLDERS (paste your engines here later) ----------
# def page_srs_engine(): ...
# def page_exam_mode(): ...
# def page_tutor_flow(): ...
