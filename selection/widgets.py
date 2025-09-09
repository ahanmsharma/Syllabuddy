import streamlit as st
from typing import List

def _data():
    return (
        st.session_state["_SUBJECTS"],
        st.session_state["_MODS"],
        st.session_state["_IQS"],
        st.session_state["_DPS"],
        st.session_state["_go"],
    )

# ---- selection helpers ----
def is_subject_selected(subject: str) -> bool:
    return any(s == subject for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_module_selected(subject: str, module: str) -> bool:
    return any((s == subject and m == module) for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_iq_selected(subject: str, module: str, iq: str) -> bool:
    return any((s == subject and m == module and i == iq) for (s, m, i, dp) in st.session_state["sel_dotpoints"])

def add_all_modules(subject: str, on: bool, MODS, IQS, DPS):
    for m in MODS.get(subject, []):
        add_all_iqs(subject, m, on, IQS, DPS)

def add_all_iqs(subject: str, module: str, on: bool, IQS, DPS):
    for iq in IQS.get((subject, module), []):
        add_all_dps(subject, module, iq, on, DPS)

def add_all_dps(subject: str, module: str, iq: str, on: bool, DPS):
    for dp in DPS.get((subject, module, iq), []):
        item = (subject, module, iq, dp)
        if on:  st.session_state["sel_dotpoints"].add(item)
        else:   st.session_state["sel_dotpoints"].discard(item)

# ---- cards ----
def subject_cards(key_prefix: str, back_to: str | None):
    SUBJECTS, MODS, IQS, DPS, go = _data()
    if back_to: from common.ui import topbar; topbar("Choose Subject", back_to=back_to)
    else: st.title("Choose Subject")
    st.caption("Open drills down. Use Select/Unselect to include/exclude.")

    cols = st.columns(2)
    for i, s in enumerate(SUBJECTS):
        with cols[i % 2]:
            selected = is_subject_selected(s)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.markdown(f"### {s}")
                st.caption(f"{len(MODS.get(s, []))} modules")
                a, b = st.columns([3,2])
                with a:
                    if st.button("Open", key=f"{key_prefix}_open_{i}", use_container_width=True):
                        st.session_state["focus_subject"] = s
                        go(f"{key_prefix}_modules")
                with b:
                    if st.button(("Unselect" if selected else "Select"),
                                 key=f"{key_prefix}_sel_{i}", use_container_width=True):
                        add_all_modules(s, on=not selected, MODS=MODS, IQS=IQS, DPS=DPS)
                        st.rerun()

def module_cards(subject: str, key_prefix: str, back_to: str):
    from common.ui import topbar
    SUBJECTS, MODS, IQS, DPS, go = _data()
    topbar(f"{subject} — Modules", back_to=back_to)
    st.caption("Open drills down. Use Select/Unselect to include/exclude.")
    modules = MODS.get(subject, [])
    cols = st.columns(2)
    for i, m in enumerate(modules):
        with cols[i % 2]:
            selected = is_module_selected(subject, m)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.markdown(f"### {m}")
                st.caption(f"{len(IQS.get((subject, m), []))} inquiry questions")
                a, b = st.columns([3,2])
                with a:
                    if st.button("Open", key=f"{key_prefix}_mod_open_{i}", use_container_width=True):
                        st.session_state["focus_module"] = (subject, m)
                        go(f"{key_prefix}_iqs")
                with b:
                    if st.button(("Unselect" if selected else "Select"),
                                 key=f"{key_prefix}_mod_sel_{i}", use_container_width=True):
                        add_all_iqs(subject, m, on=not selected, IQS=IQS, DPS=DPS)
                        st.rerun()

def iq_cards(subject: str, module: str, key_prefix: str, back_to: str):
    from common.ui import topbar
    SUBJECTS, MODS, IQS, DPS, go = _data()
    topbar(f"{subject} → {module} — IQs", back_to=back_to)
    st.caption("Open drills down. Use Select/Unselect to include/exclude.")
    iqs = IQS.get((subject, module), [])
    cols = st.columns(2)
    for i, iq in enumerate(iqs):
        with cols[i % 2]:
            selected = is_iq_selected(subject, module, iq)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.markdown(f"### {iq}")
                st.caption(f"{len(DPS.get((subject, module, iq), []))} dotpoints")
                a, b = st.columns([3,2])
                with a:
                    if st.button("Open", key=f"{key_prefix}_iq_open_{i}", use_container_width=True):
                        st.session_state["focus_iq"] = (subject, module, iq)
                        go(f"{key_prefix}_dotpoints")
                with b:
                    if st.button(("Unselect" if selected else "Select"),
                                 key=f"{key_prefix}_iq_sel_{i}", use_container_width=True):
                        add_all_dps(subject, module, iq, on=not selected, DPS=DPS)
                        st.rerun()

def dotpoint_cards(subject: str, module: str, iq: str, key_prefix: str, back_to: str):
    from common.ui import topbar
    SUBJECTS, MODS, IQS, DPS, go = _data()
    topbar(f"{subject} → {module} → {iq} — Dotpoints", back_to=back_to)
    st.caption("Click Toggle to include/exclude dotpoints.")
    dps = DPS.get((subject, module, iq), [])
    colA, colB = st.columns(2)
    for i, dp in enumerate(dps):
        item = (subject, module, iq, dp)
        selected = item in st.session_state["sel_dotpoints"]
        with (colA if i % 2 == 0 else colB):
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#16a34a;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.markdown(f"**{dp}**")
                if st.button(("Unselect" if selected else "Select / Toggle"),
                             key=f"{key_prefix}_dp_toggle_{i}", use_container_width=True):
                    if selected: st.session_state["sel_dotpoints"].discard(item)
                    else:        st.session_state["sel_dotpoints"].add(item)
                    st.rerun()
