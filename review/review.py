import uuid
import streamlit as st
from typing import List, Set
from common.ui import topbar, go, safe_rerun

def review_box(route_key: str, title: str, rows: List[tuple],
               back_to: str, after_submit_route: str):
    """
    Minimal + robust Review UI (unique keys per render):
      - Kept by default (green). Remove -> red.
      - Apply writes kept items; Submit writes + navigates.
      - Keys include a per-call UUID to avoid duplicates even if rendered twice.
    """
    topbar(title, back_to=back_to)

    # Per-call unique prefix so keys never collide
    instance = uuid.uuid4().hex[:8]
    KP = f"{route_key}_rb_{instance}"

    # State bucket for "removed items" for this route
    removed_key = f"__rb_removed__::{route_key}"
    if removed_key not in st.session_state:
        st.session_state[removed_key] = set()
    removed: Set[str] = st.session_state[removed_key]

    def item_key(item: tuple) -> str:
        s, m, iq, dp = item
        return f"{s}||{m}||{iq}||{dp}"

    st.write(f"**Total items:** {len(rows)}")

    for idx, item in enumerate(rows):
        s, m, iq, dp = item
        k = item_key(item)
        is_removed = (k in removed)
        border = "#b91c1c" if is_removed else "#16a34a"
        label = "Removed" if is_removed else "Kept"

        st.markdown(
            f"""
            <div style="border:2px solid {border};
                        border-radius:10px;
                        padding:8px 12px;
                        margin-bottom:10px;">
              <b>{s} → {m} → {iq}</b> — {dp}<br>
              <span style="color:{border}; font-weight:700;">{label}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        left, right = st.columns(2)
        with left:
            if st.button("Keep", key=f"{KP}_keep_{idx}"):
                removed.discard(k)
                safe_rerun()
        with right:
            if st.button("Remove", key=f"{KP}_remove_{idx}"):
                removed.add(k)
                safe_rerun()

    kept_count = len(rows) - len(removed)
    st.info(f"Kept: {kept_count}   |   Removed: {len(removed)}")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("← Back", key=f"{KP}_back"):
            go(back_to)

    def write_selection_and_maybe_go(go_next: bool):
        kept_items = {item for item in rows if item_key(item) not in removed}
        st.session_state["sel_dotpoints"] = kept_items
        st.success("Selection updated.")
        if go_next:
            st.session_state.pop(removed_key, None)
            go(after_submit_route)

    with c2:
        if st.button("Apply changes", key=f"{KP}_apply", type="primary"):
            write_selection_and_maybe_go(go_next=False)

    with c3:
        if st.button("Submit & Continue", key=f"{KP}_submit", type="primary"):
            write_selection_and_maybe_go(go_next=True)

def page_cram_review():
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box("cram", "Review Selection (Cram)", rows, back_to="cram_subjects", after_submit_route="cram_how")

def page_srs_review():
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box("srs", "Review Selection (SR)", rows, back_to="srs_subjects", after_submit_route="srs_menu")
