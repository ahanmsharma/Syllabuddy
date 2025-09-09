import json
import pathlib
from typing import Dict, List, Tuple

import streamlit as st

# ================== PAGE SETUP ==================
st.set_page_config(page_title="Syllabuddy", layout="wide")

# ================== LOAD SYLLABUS ==================
@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    with open("syllabus.json", "r") as f:
        return json.load(f)

def syllabus_levels(data: Dict) -> Tuple[List[str], Dict[str, List[str]], Dict[Tuple[str, str], List[str]], Dict[Tuple[str, str, str], List[str]]]:
    """Return convenience structures:
       subjects, modules_by_subject, iqs_by_subject_module, dotpoints_by_subject_module_iq
    """
    subjects = list(data.keys())
    modules_by_subject = {s: list(data[s].keys()) for s in subjects}
    iqs_by_subject_module = {}
    dotpoints_by_smi = {}
    for s in subjects:
        for m in data[s]:
            iqs_by_subject_module[(s, m)] = list(data[s][m].keys())
            for iq in data[s][m]:
                dotpoints_by_smi[(s, m, iq)] = list(data[s][m][iq])
    return subjects, modules_by_subject, iqs_by_subject_module, dotpoints_by_smi

syllabus = load_syllabus()
SUBJECTS, MODS, IQS, DPS = syllabus_levels(syllabus)

# ================== STATE ==================
def ensure_state():
    st.session_state.setdefault("route", "home")  # home, srs_menu, srs_choose, cram_select, cram_review_mode, select_subject_main, ai_select, ai_review
    st.session_state.setdefault("sel_subjects", set())
    st.session_state.setdefault("sel_modules", set())    # (subj, module)
    st.session_state.setdefault("sel_iqs", set())        # (subj, module, iq)
    st.session_state.setdefault("sel_dotpoints", set())  # tuples (subj, module, iq, dotpoint)
    st.session_state.setdefault("nav_stack", [])         # for back button (route history)
    st.session_state.setdefault("ai_weakness_text", "")
    st.session_state.setdefault("ai_strength_text", "")
    st.session_state.setdefault("ai_suggested", [])      # list of tuples (s,m,iq,dp)

ensure_state()

def go(route: str):
    # push current route for back behavior
    st.session_state["nav_stack"].append(st.session_state["route"])
    st.session_state["route"] = route

def back():
    if st.session_state["nav_stack"]:
        st.session_state["route"] = st.session_state["nav_stack"].pop()
    else:
        st.session_state["route"] = "home"

# ================== STYLES ==================
st.markdown("""
<style>
/* General */
.block-container { max-width: 1280px; margin: auto; }

/* Big buttons */
.big-btn {
  display:inline-block;padding:18px 24px;border-radius:14px;border:1px solid #d1d5db;
  background:#f8fafc;text-decoration:none;color:#111;font-weight:600;
}
.big-btn:hover { background:#eef2ff; border-color:#93c5fd; }

/* Card grid */
.grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(260px,1fr)); gap:16px; }
.card {
  border:2px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; position:relative;
}
.card.selected { border-color:#3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset; }
.card-title { font-weight:700; margin-bottom:.5rem; }
.card-actions { display:flex; gap:8px; flex-wrap:wrap; }

/* Blue progress border (simulated) */
.progress-border { position:absolute; inset:0; border-radius:14px; border:3px solid #93c5fd; pointer-events:none; }

/* Sticky header/footer for scroll section */
.scroll-wrap { display:flex; flex-direction:column; height:70vh; border:1px solid #e5e7eb; border-radius:12px; overflow:hidden; }
.scroll-head { padding:12px 14px; font-weight:700; background:#f8fafc; border-bottom:1px solid #e5e7eb; }
.scroll-body { flex:1; overflow:auto; padding:12px 14px; }
.scroll-foot { padding:12px 14px; background:#f8fafc; border-top:1px solid #e5e7eb; }

/* Tick / Cross item */
.dp-item { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; margin-bottom:10px; }
.dp-item.selected { border-color:#16a34a; box-shadow: inset 0 0 0 2px rgba(22,163,74,.2); }
.btn { padding:8px 12px; border-radius:10px; border:1px solid #d1d5db; background:#fff; font-weight:600; }
.btn.primary { background:#3b82f6; color:#fff; border-color:#2563eb; }
.btn.destructive { background:#fee2e2; color:#991b1b; border-color:#fecaca; }
.btn.ghost { background:#f8fafc;}

/* Top bar with back arrow */
.topbar { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
.back { cursor:pointer; font-size:20px; }
.badge { display:inline-block; font-size:.9rem; padding:4px 8px; background:#eef2ff; border:1px solid #c7d2fe; border-radius:999px; }
</style>
""", unsafe_allow_html=True)

# ================== HELPERS (SELECTION) ==================
def select_level_card(title: str, subtitle: str, selected: bool, open_key: str, select_key: str):
    cls = "card selected" if selected else "card"
    st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
    st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
    st.caption(subtitle)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open", key=open_key, use_container_width=True):
            return "open"
    with col2:
        if st.button("Select this level", key=select_key, use_container_width=True):
            return "select"
    st.markdown("</div>", unsafe_allow_html=True)
    return None

def toggle_tuple(store: set, value: tuple):
    if value in store:
        store.remove(value)
    else:
        store.add(value)

def mark_all_modules_of_subject(subj: str, on: bool):
    for m in MODS[subj]:
        if on:
            st.session_state["sel_modules"].add((subj, m))
        else:
            st.session_state["sel_modules"].discard((subj, m))
        # and their IQs & DPs
        for iq in IQS[(subj, m)]:
            if on:
                st.session_state["sel_iqs"].add((subj, m, iq))
            else:
                st.session_state["sel_iqs"].discard((subj, m, iq))
            for dp in DPS[(subj, m, iq)]:
                if on:
                    st.session_state["sel_dotpoints"].add((subj, m, iq, dp))
                else:
                    st.session_state["sel_dotpoints"].discard((subj, m, iq, dp))

def mark_all_iqs_of_module(subj: str, mod: str, on: bool):
    for iq in IQS[(subj, mod)]:
        if on:
            st.session_state["sel_iqs"].add((subj, mod, iq))
        else:
            st.session_state["sel_iqs"].discard((subj, mod, iq))
        for dp in DPS[(subj, mod, iq)]:
            if on:
                st.session_state["sel_dotpoints"].add((subj, mod, iq, dp))
            else:
                st.session_state["sel_dotpoints"].discard((subj, mod, iq, dp))

def mark_all_dps_of_iq(subj: str, mod: str, iq: str, on: bool):
    for dp in DPS[(subj, mod, iq)]:
        if on:
            st.session_state["sel_dotpoints"].add((subj, mod, iq, dp))
        else:
            st.session_state["sel_dotpoints"].discard((subj, mod, iq, dp))

# ================== ROUTES ==================

def route_home():
    st.title("Syllabuddy")
    st.write("Stay on track with spaced repetition, targeted practice, and quick selection.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Spaced Repetition", use_container_width=True, type="primary"):
            go("srs_menu")
    with c2:
        if st.button("Select Subject", use_container_width=True):
            go("select_subject_main")

def route_srs_menu():
    st.markdown('<div class="topbar"><div class="back">⬅</div><div></div></div>', unsafe_allow_html=True)
    if st.button("Back", key="back_srs_menu_small"):
        back()
        st.stop()

    st.title("Spaced Repetition")
    # Show "All" with a count (placeholder count)
    today_count = max(1, len(st.session_state["sel_dotpoints"]))  # placeholder; wire to SRS later
    st.write(f"**All (Today):** {today_count} dotpoints due")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Start: All (SR priority)", use_container_width=True, type="primary"):
            st.success("SR engine not wired yet — will run due items in priority order.")
    with c2:
        if st.button("Choose Subject (SR order)", use_container_width=True):
            go("srs_choose")
    with c3:
        if st.button("Cram Mode (mass select)", use_container_width=True):
            go("cram_select")

def route_srs_choose():
    # identical hierarchy selection but the intent is SR ordering
    topbar("Choose Subject (SR)")
    hierarchical_selector(intent="srs")
    bottom_submit(next_route="srs_menu", submit_label="Done (return to SR menu)")

def route_select_subject_main():
    topbar("Select Subject")
    st.write("Choose subjects/modules/IQs/dotpoints for study or try AI selection from your weaknesses.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("Manual selection", use_container_width=True, type="primary"):
            go("cram_select")
    with c2:
        if st.button("AI selection (enter weaknesses)", use_container_width=True):
            go("ai_select")

def route_cram_select():
    topbar("Cram Mode — Select what to review")
    hierarchical_selector(intent="cram")
    bottom_submit(next_route="cram_review_mode", submit_label="Next: How to review")

def route_cram_review_mode():
    topbar("How to review")
    st.write("Choose the order of review:")
    c1, c2 = st.columns(2, gap="large")
    review_choice = st.radio("Mode", ["SR (spaced repetition order)", "Prioritization (based on strengths/weaknesses)"], label_visibility="collapsed")
    if review_choice == "Prioritization (based on strengths/weaknesses)":
        st.subheader("Tell the AI:")
        st.session_state["ai_weakness_text"] = st.text_area("What topics are you struggling with most?", key="ai_wk", height=120, placeholder="e.g., diffusion vs osmosis; rates; energy changes")
        st.session_state["ai_strength_text"] = st.text_area("Where are your strengths?", key="ai_st", height=100, placeholder="e.g., definitions; diagrams")
        st.caption("These will be used to prioritize the order and can carry into your FP flow later.")

    if st.button("Proceed", type="primary"):
        st.success(f"Review mode: {review_choice}")
        # Wire to your session start later. For now, go back to home or SR menu.
        go("home")

def route_ai_select():
    topbar("AI selection — enter weaknesses")
    st.write("Type what you struggle with; we'll propose dotpoints that match (placeholder suggestions for now).")
    wk = st.text_area("Weaknesses", key="ai_wk2", height=150, placeholder="e.g., equilibrium constants; vectors; cell transport")
    if st.button("Get suggestions", type="primary"):
        # Placeholder suggestion: pick first 10 dotpoints across the syllabus
        suggestions = []
        for s in SUBJECTS:
            for m in MODS[s]:
                for iq in IQS[(s,m)]:
                    for dp in DPS[(s,m,iq)]:
                        suggestions.append((s,m,iq,dp))
        st.session_state["ai_suggested"] = suggestions[:20]
        go("ai_review")

def route_ai_review():
    topbar("Review suggested dotpoints")
    st.write("Click ✅ to keep or ❌ to remove. The green border indicates selected. This list can be long — the middle scrolls.")

    # Track chosen set locally
    chosen = set(st.session_state.get("ai_chosen", set()))
    # Build a scrollable section with sticky header/footer
    st.markdown('<div class="scroll-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="scroll-head">AI suggested dotpoints</div>', unsafe_allow_html=True)
    st.markdown('<div class="scroll-body">', unsafe_allow_html=True)

    new_list = []
    for idx, item in enumerate(st.session_state["ai_suggested"]):
        s, m, iq, dp = item
        is_selected = item in chosen
        cls = "dp-item selected" if is_selected else "dp-item"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        st.write(f"**{s} → {m} → {iq}** — {dp}")
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("✅ Keep", key=f"keep_{idx}", use_container_width=True):
                chosen.add(item)
        with c2:
            if st.button("❌ Remove", key=f"drop_{idx}", use_container_width=True):
                # removing: do nothing (we just won't copy it into new list)
                pass
                # If you want it to 'disappear', we just don't append to new_list.
        st.markdown('</div>', unsafe_allow_html=True)

        # Only keep if not dropped this time
        # Since we can't detect a single click in the same rerun, we rebuild below
        # Collect all not removed by checking if drop button wasn't clicked:
        # (Streamlit doesn't tell us; simplest is to keep all, then after user presses "Apply selection",
        # we use the 'chosen' set to decide)
        new_list.append(item)

    st.markdown('</div>', unsafe_allow_html=True)  # end body

    st.markdown('<div class="scroll-foot">', unsafe_allow_html=True)
    left, mid, right = st.columns([1,1,1])
    with left:
        if st.button("← Back to Choose Subject"):
            go("cram_select")
            st.stop()
    with mid:
        if st.button("Apply selection", type="primary"):
            st.session_state["ai_chosen"] = chosen
            # Copy chosen into sel_dotpoints (additive)
            for item in chosen:
                st.session_state["sel_dotpoints"].add(item)
            st.success("Added selected dotpoints to your selection list.")
    with right:
        if st.button("Done"):
            go("home")
    st.markdown('</div>', unsafe_allow_html=True)  # end foot
    st.markdown('</div>', unsafe_allow_html=True)  # end wrap

# ================== REUSABLE UI ==================
def topbar(title: str):
    c1, c2 = st.columns([1,6], vertical_alignment="center")
    with c1:
        if st.button("⬅ Back", use_container_width=True):
            back()
            st.stop()
    with c2:
        st.title(title)

def bottom_submit(next_route: str, submit_label: str = "Next"):
    st.write("")
    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        if st.button(submit_label, type="primary", use_container_width=True):
            go(next_route)

def hierarchical_selector(intent: str):
    """Full-page hierarchical selection UI.
       intent: 'srs' or 'cram' (labeling only)
    """
    # Level 1: Subjects
    st.subheader("1) Subjects")
    with st.container():
        cols = st.columns(2)
        for i, subj in enumerate(SUBJECTS):
            selected = any(s == subj for (s,_,_,_) in st.session_state["sel_dotpoints"])
            with cols[i % 2]:
                action = select_level_card(
                    title=subj,
                    subtitle=f"{len(MODS[subj])} modules",
                    selected=selected,
                    open_key=f"open_subj_{subj}_{intent}",
                    select_key=f"sel_subj_{subj}_{intent}",
                )
                if action == "open":
                    st.session_state["focus_subject"] = subj
                elif action == "select":
                    mark_all_modules_of_subject(subj, on=True)

    # Drilldown to Modules
    subj = st.session_state.get("focus_subject")
    if subj:
        st.subheader(f"2) Modules in {subj}")
        with st.container():
            cols = st.columns(2)
            for i, mod in enumerate(MODS[subj]):
                selected = any((s == subj and m == mod) for (s,m,_,_) in st.session_state["sel_dotpoints"])
                with cols[i % 2]:
                    action = select_level_card(
                        title=mod,
                        subtitle=f"{len(IQS[(subj, mod)])} inquiry questions",
                        selected=selected,
                        open_key=f"open_mod_{subj}_{mod}_{intent}",
                        select_key=f"sel_mod_{subj}_{mod}_{intent}",
                    )
                    if action == "open":
                        st.session_state["focus_module"] = (subj, mod)
                    elif action == "select":
                        mark_all_iqs_of_module(subj, mod, on=True)

    # Drilldown to IQs
    sm = st.session_state.get("focus_module")
    if sm:
        s, m = sm
        st.subheader(f"3) Inquiry Questions in {s} → {m}")
        with st.container():
            cols = st.columns(2)
            for i, iq in enumerate(IQS[(s,m)]):
                selected = any((ss == s and mm == m and ii == iq) for (ss,mm,ii,_) in st.session_state["sel_dotpoints"])
                with cols[i % 2]:
                    action = select_level_card(
                        title=iq,
                        subtitle=f"{len(DPS[(s,m,iq)])} dotpoints",
                        selected=selected,
                        open_key=f"open_iq_{s}_{m}_{iq}_{intent}",
                        select_key=f"sel_iq_{s}_{m}_{iq}_{intent}",
                    )
                    if action == "open":
                        st.session_state["focus_iq"] = (s, m, iq)
                    elif action == "select":
                        mark_all_dps_of_iq(s, m, iq, on=True)

    # Drilldown to Dotpoints
    smi = st.session_state.get("focus_iq")
    if smi:
        s, m, iq = smi
        st.subheader(f"4) Dotpoints in {s} → {m} → {iq}")
        grid = st.container()
        with grid:
            cols = st.columns(2)
            for i, dp in enumerate(DPS[(s,m,iq)]):
                selected = (s,m,iq,dp) in st.session_state["sel_dotpoints"]
                with cols[i % 2]:
                    cls = "card selected" if selected else "card"
                    st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
                    st.markdown(f'<div class="card-title">{dp}</div>', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Select / Unselect", key=f"toggle_dp_{s}_{m}_{iq}_{i}_{intent}", use_container_width=True):
                            if selected:
                                st.session_state["sel_dotpoints"].discard((s,m,iq,dp))
                            else:
                                st.session_state["sel_dotpoints"].add((s,m,iq,dp))
                    with c2:
                        st.caption("Click to toggle")
                    st.markdown('</div>', unsafe_allow_html=True)

# ================== ROUTER ==================
ROUTES = {
    "home": route_home,
    "srs_menu": route_srs_menu,
    "srs_choose": route_srs_choose,
    "cram_select": route_cram_select,
    "cram_review_mode": route_cram_review_mode,
    "select_subject_main": route_select_subject_main,
    "ai_select": route_ai_select,
    "ai_review": route_ai_review,
}

ROUTES[st.session_state["route"]]()
