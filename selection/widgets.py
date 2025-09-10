import streamlit as st
from common.ui import (
    topbar, go,
    k_subject_open, k_subject_toggle,
    k_module_open,  k_module_toggle,
    k_iq_open,      k_iq_toggle,
    k_dp_toggle,
)

# =============================
# Helpers to add/remove in bulk
# =============================

def add_all_modules(subject: str, on: bool):
    MODS = st.session_state["_MODS"]
    IQS  = st.session_state["_IQS"]
    DPS  = st.session_state["_DPS"]
    sel  = st.session_state["sel_dotpoints"]
    for m in MODS.get(subject, []):
        for iq in IQS.get((subject, m), []):
            for dp in DPS.get((subject, m, iq), []):
                item = (subject, m, iq, dp)
                if on: sel.add(item)
                else:  sel.discard(item)

def add_all_iqs(subject: str, module: str, on: bool):
    IQS  = st.session_state["_IQS"]
    DPS  = st.session_state["_DPS"]
    sel  = st.session_state["sel_dotpoints"]
    for iq in IQS.get((subject, module), []):
        for dp in DPS.get((subject, module, iq), []):
            item = (subject, module, iq, dp)
            if on: sel.add(item)
            else:  sel.discard(item)

def add_all_dps(subject: str, module: str, iq: str, on: bool):
    DPS = st.session_state["_DPS"]
    sel = st.session_state["sel_dotpoints"]
    for dp in DPS.get((subject, module, iq), []):
        item = (subject, module, iq, dp)
        if on: sel.add(item)
        else:  sel.discard(item)

def is_subject_selected(subject: str) -> bool:
    return any(s==subject for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_module_selected(subject: str, module: str) -> bool:
    return any((s==subject and m==module) for (s, m, iq, dp) in st.session_state["sel_dotpoints"])

def is_iq_selected(subject: str, module: str, iq: str) -> bool:
    return any((s==subject and m==module and i==iq) for (s, m, i, dp) in st.session_state["sel_dotpoints"])

# =============================
# CRAM pages
# =============================

def page_cram_subjects():
    SUBJECTS = st.session_state["_SUBJECTS"]
    topbar("Choose Subject", back_to="srs_menu")
    st.caption("Open drills down. “Select” toggles all children (modules → IQs → dotpoints).")

    cols = st.columns(2)
    for i, s in enumerate(SUBJECTS):
        with cols[i % 2]:
            selected = is_subject_selected(s)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.subheader(s)
                c1, c2 = st.columns([2,1])

                # Open
                with c1:
                    st.button(
                        "Open",
                        key=k_subject_open(s, "cram"),
                        on_click=lambda subj=s: st.session_state.update({"focus_subject": subj}) or go("cram_modules"),
                        use_container_width=True
                    )

                # Select/Unselect whole subject
                with c2:
                    label = "Unselect" if selected else "Select"
                    st.button(
                        label,
                        key=k_subject_toggle(s, "cram"),
                        on_click=lambda subj=s, sel=selected: (add_all_modules(subj, not sel),),
                        use_container_width=True
                    )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("cram_review",))

def page_cram_modules():
    MODS = st.session_state["_MODS"]
    s = st.session_state.get("focus_subject")
    if not s:
        return go("cram_subjects")

    topbar(f"{s} — Modules", back_to="cram_subjects")
    modules = MODS.get(s, [])
    cols = st.columns(2)

    for i, m in enumerate(modules):
        with cols[i % 2]:
            selected = is_module_selected(s, m)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.subheader(m)
                c1, c2 = st.columns([2,1])

                with c1:
                    st.button(
                        "Open",
                        key=k_module_open(s, m, "cram"),
                        on_click=lambda subj=s, mod=m: st.session_state.update({"focus_module": (subj, mod)}) or go("cram_iqs"),
                        use_container_width=True
                    )
                with c2:
                    label = "Unselect" if selected else "Select"
                    st.button(
                        label,
                        key=k_module_toggle(s, m, "cram"),
                        on_click=lambda subj=s, mod=m, sel=selected: (add_all_iqs(subj, mod, not sel),),
                        use_container_width=True
                    )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("cram_review",))

def page_cram_iqs():
    IQS = st.session_state["_IQS"]
    sm = st.session_state.get("focus_module")
    if not sm:
        return go("cram_modules")
    s, m = sm

    topbar(f"{s} → {m} — IQs", back_to="cram_modules")
    iqs = IQS.get((s, m), [])
    cols = st.columns(2)

    for i, iq in enumerate(iqs):
        with cols[i % 2]:
            selected = is_iq_selected(s, m, iq)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.subheader(iq)
                c1, c2 = st.columns([2,1])

                with c1:
                    st.button(
                        "Open",
                        key=k_iq_open(s, m, iq, "cram"),
                        on_click=lambda subj=s, mod=m, q=iq: st.session_state.update({"focus_iq": (subj, mod, q)}) or go("cram_dotpoints"),
                        use_container_width=True
                    )
                with c2:
                    label = "Unselect" if selected else "Select"
                    st.button(
                        label,
                        key=k_iq_toggle(s, m, iq, "cram"),
                        on_click=lambda subj=s, mod=m, q=iq, sel=selected: (add_all_dps(subj, mod, q, not sel),),
                        use_container_width=True
                    )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("cram_review",))

def page_cram_dotpoints():
    DPS = st.session_state["_DPS"]
    smi = st.session_state.get("focus_iq")
    if not smi:
        return go("cram_iqs")
    s, m, iq = smi

    topbar(f"{s} → {m} → {iq} — Dotpoints", back_to="cram_iqs")
    dps = DPS.get((s, m, iq), [])
    c1, c2 = st.columns(2)

    for i, dp in enumerate(dps):
        with (c1 if i % 2 == 0 else c2):
            item = (s, m, iq, dp)
            selected = item in st.session_state["sel_dotpoints"]

            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#16a34a;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.write(f"**{dp}**")
                label = "Unselect" if selected else "Select / Toggle"
                st.button(
                    label,
                    key=k_dp_toggle(s, m, iq, dp, "cram"),
                    on_click=lambda it=item, sel=selected: (
                        st.session_state["sel_dotpoints"].discard(it) if sel
                        else st.session_state["sel_dotpoints"].add(it)
                    ),
                    use_container_width=True
                )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("cram_review",))

# =============================
# SRS pages (same UI, different backs)
# =============================

def page_srs_subjects():
    SUBJECTS = st.session_state["_SUBJECTS"]
    topbar("Choose Subject", back_to="srs_menu")
    st.caption("Open drills down. “Select” toggles all children (modules → IQs → dotpoints).")

    cols = st.columns(2)
    for i, s in enumerate(SUBJECTS):
        with cols[i % 2]:
            selected = is_subject_selected(s)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.subheader(s)
                c1, c2 = st.columns([2,1])

                with c1:
                    st.button(
                        "Open",
                        key=k_subject_open(s, "srs"),
                        on_click=lambda subj=s: st.session_state.update({"focus_subject": subj}) or go("srs_modules"),
                        use_container_width=True
                    )
                with c2:
                    label = "Unselect" if selected else "Select"
                    st.button(
                        label,
                        key=k_subject_toggle(s, "srs"),
                        on_click=lambda subj=s, sel=selected: (add_all_modules(subj, not sel),),
                        use_container_width=True
                    )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("srs_review",))

def page_srs_modules():
    MODS = st.session_state["_MODS"]
    s = st.session_state.get("focus_subject")
    if not s:
        return go("srs_subjects")

    topbar(f"{s} — Modules", back_to="srs_subjects")
    modules = MODS.get(s, [])
    cols = st.columns(2)

    for i, m in enumerate(modules):
        with cols[i % 2]:
            selected = is_module_selected(s, m)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.subheader(m)
                c1, c2 = st.columns([2,1])

                with c1:
                    st.button(
                        "Open",
                        key=k_module_open(s, m, "srs"),
                        on_click=lambda subj=s, mod=m: st.session_state.update({"focus_module": (subj, mod)}) or go("srs_iqs"),
                        use_container_width=True
                    )
                with c2:
                    label = "Unselect" if selected else "Select"
                    st.button(
                        label,
                        key=k_module_toggle(s, m, "srs"),
                        on_click=lambda subj=s, mod=m, sel=selected: (add_all_iqs(subj, mod, not sel),),
                        use_container_width=True
                    )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("srs_review",))

def page_srs_iqs():
    IQS = st.session_state["_IQS"]
    sm = st.session_state.get("focus_module")
    if not sm:
        return go("srs_modules")
    s, m = sm

    topbar(f"{s} → {m} — IQs", back_to="srs_modules")
    iqs = IQS.get((s, m), [])
    cols = st.columns(2)

    for i, iq in enumerate(iqs):
        with cols[i % 2]:
            selected = is_iq_selected(s, m, iq)
            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#3b82f6;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.subheader(iq)
                c1, c2 = st.columns([2,1])

                with c1:
                    st.button(
                        "Open",
                        key=k_iq_open(s, m, iq, "srs"),
                        on_click=lambda subj=s, mod=m, q=iq: st.session_state.update({"focus_iq": (subj, mod, q)}) or go("srs_dotpoints"),
                        use_container_width=True
                    )
                with c2:
                    label = "Unselect" if selected else "Select"
                    st.button(
                        label,
                        key=k_iq_toggle(s, m, iq, "srs"),
                        on_click=lambda subj=s, mod=m, q=iq, sel=selected: (add_all_dps(subj, mod, q, not sel),),
                        use_container_width=True
                    )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("srs_review",))

def page_srs_dotpoints():
    DPS = st.session_state["_DPS"]
    smi = st.session_state.get("focus_iq")
    if not smi:
        return go("srs_iqs")
    s, m, iq = smi

    topbar(f"{s} → {m} → {iq} — Dotpoints", back_to="srs_iqs")
    dps = DPS.get((s, m, iq), [])
    c1, c2 = st.columns(2)

    for i, dp in enumerate(dps):
        with (c1 if i % 2 == 0 else c2):
            item = (s, m, iq, dp)
            selected = item in st.session_state["sel_dotpoints"]

            box = st.container(border=True)
            with box:
                if selected:
                    st.markdown("<div style='height:6px;background:#16a34a;border-radius:6px;margin:-8px -8px 8px -8px;'></div>", unsafe_allow_html=True)
                st.write(f"**{dp}**")
                label = "Unselect" if selected else "Select / Toggle"
                st.button(
                    label,
                    key=k_dp_toggle(s, m, iq, dp, "srs"),
                    on_click=lambda it=item, sel=selected: (
                        st.session_state["sel_dotpoints"].discard(it) if sel
                        else st.session_state["sel_dotpoints"].add(it)
                    ),
                    use_container_width=True
                )

    mid = st.columns([1,1,1])[1]
    with mid:
        st.button("Review selected dotpoints", type="primary", use_container_width=True, on_click=go, args=("srs_review",))
