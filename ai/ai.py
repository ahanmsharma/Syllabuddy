import uuid
import streamlit as st
from common.ui import topbar, go, safe_rerun

def _key_for(item) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def page_ai_select():
    SUBJECTS = st.session_state["_SUBJECTS"]
    MODS     = st.session_state["_MODS"]
    IQS      = st.session_state["_IQS"]
    DPS      = st.session_state["_DPS"]

    topbar("AI selection — enter weaknesses", back_to="select_subject_main")
    st.write("Type what you struggle with; we’ll propose dotpoints that match (placeholder suggestions for now).")
    st.session_state["ai_weakness_text"] = st.text_area(
        "Weaknesses", key="ai_wk2", height=150,
        placeholder="e.g., equilibrium constants; vectors; cell transport"
    )
    if st.button("Get suggestions", type="primary"):
        suggestions = []
        for s in SUBJECTS:
            for m in MODS.get(s, []):
                for iq in IQS.get((s, m), []):
                    for dp in DPS.get((s, m, iq), []):
                        suggestions.append((s, m, iq, dp))
        st.session_state["ai_suggested"] = suggestions[:40]

        # Per-item status: None | "keep" | "remove"
        st.session_state["ai_status"] = {}  # key -> "keep"/"remove"
        go("ai_review")

def page_ai_review():
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.write("Click ✅ Keep (green) or ❌ Remove (red). Tally updates live. Use 'Apply selection' to add kept items.")

    suggested = st.session_state.get("ai_suggested", [])
    status: dict = st.session_state.get("ai_status", {}) or {}
    st.session_state["ai_status"] = status

    inst = uuid.uuid4().hex[:6]
    KP = f"ai_rev_{inst}"

    kept_count = 0
    removed_count = 0

    for idx, item in enumerate(suggested):
        k = _key_for(item)
        tag = status.get(k)  # None | "keep" | "remove"
        is_removed = (tag == "remove")
        is_kept    = (tag == "keep")

        card_class = "dp-card green" if is_kept else ("dp-card red" if is_removed else "dp-card")
        pill_html  = (
            '<span class="pill keep">Kept</span>' if is_kept
            else ('<span class="pill remove">Removed</span>' if is_removed
                  else '<span class="pill">Unreviewed</span>')
        )

        if is_kept: kept_count += 1
        if is_removed: removed_count += 1

        s, m, iq, dp = item
        with st.container(border=False):
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            st.markdown('<div class="row-top">', unsafe_allow_html=True)
            st.markdown(f'<div class="title">{s} → {m} → {iq}</div>', unsafe_allow_html=True)
            st.markdown(pill_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="dp-text">{dp}</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Keep", key=f"{KP}_keep_{idx}", use_container_width=True):
                    status[k] = "keep"
                    safe_rerun()
            with c2:
                if st.button("❌ Remove", key=f"{KP}_remove_{idx}", use_container_width=True):
                    status[k] = "remove"
                    safe_rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # end card

    st.info(f"Kept: {kept_count}   |   Removed: {removed_count}   |   Unreviewed: {len(suggested) - kept_count - removed_count}")

    # Footer
    st.markdown('<div class="review-footer">', unsafe_allow_html=True)
    left, mid, right = st.columns(3)
    with left:
        if st.button("← Back to Choose Subject", key=f"{KP}_back"):
            go("cram_subjects")

    def _apply_selection(go_home: bool):
        sel = st.session_state.get("sel_dotpoints", set())
        for item in suggested:
            if st.session_state["ai_status"].get(_key_for(item)) == "keep":
                sel.add(item)
        st.session_state["sel_dotpoints"] = sel
        st.success("Added kept dotpoints to your selection.")
        if go_home:
            go("home")

    with mid:
        if st.button("Apply selection", key=f"{KP}_apply", type="primary"):
            _apply_selection(go_home=False)

    with right:
        if st.button("Done", key=f"{KP}_done", type="primary"):
            _apply_selection(go_home=True)

    st.markdown("</div>", unsafe_allow_html=True)  # end footer
