import uuid
from typing import List, Set, Tuple
import streamlit as st
from common.ui import topbar, go, safe_rerun

def _stable_key(item: Tuple[str, str, str, str]) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def _class_and_pill(is_removed: bool) -> tuple[str, str]:
    if is_removed:
        return ("dp-card red", '<span class="pill remove">Removed</span>')
    return ("dp-card green", '<span class="pill keep">Kept</span>')

def review_box(
    route_key: str,
    title: str,
    rows: List[Tuple[str, str, str, str]],
    back_to: str,
    after_submit_route: str,
):
    """
    Unified review UI for SR & Cram:
      • Default = Kept (green). Remove toggles red.
      • Status pill + border update instantly.
      • Footer: Back / Apply changes / Submit & Continue.
    """
    topbar(title, back_to=back_to)

    inst = uuid.uuid4().hex[:6]
    KP = f"{route_key}_rb_{inst}"

    removed_key = f"__rb_removed__::{route_key}"
    if removed_key not in st.session_state:
        st.session_state[removed_key] = set()
    removed: Set[str] = st.session_state[removed_key]

    st.caption(f"Total selected dotpoints: **{len(rows)}**")

    for idx, item in enumerate(rows):
        k = _stable_key(item)
        is_removed = (k in removed)
        card_class, pill_html = _class_and_pill(is_removed)

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
                if st.button("Keep", key=f"{KP}_keep_{idx}", use_container_width=True):
                    removed.discard(k)
                    safe_rerun()
            with c2:
                if st.button("Remove", key=f"{KP}_remove_{idx}", use_container_width=True):
                    removed.add(k)
                    safe_rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # end card

    kept_count = len(rows) - len(removed)
    st.info(f"Kept: {kept_count}   |   Removed: {len(removed)}")

    st.markdown('<div class="review-footer">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)

    with f1:
        if st.button("← Back", key=f"{KP}_back"):
            go(back_to)

    def _apply(go_next: bool):
        kept_items = {itm for itm in rows if _stable_key(itm) not in removed}
        st.session_state["sel_dotpoints"] = kept_items
        st.success("Selection updated.")
        if go_next:
            st.session_state.pop(removed_key, None)
            go(after_submit_route)

    with f2:
        if st.button("Apply changes", key=f"{KP}_apply", type="primary"):
            _apply(go_next=False)

    with f3:
        if st.button("Submit & Continue", key=f"{KP}_submit", type="primary"):
            _apply(go_next=True)

    st.markdown("</div>", unsafe_allow_html=True)  # end footer

def page_cram_review():
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box(
        route_key="cram",
        title="Review Selection (Cram)",
        rows=rows,
        back_to="cram_subjects",
        after_submit_route="cram_how",
    )

def page_srs_review():
    rows = sorted(list(st.session_state["sel_dotpoints"]))
    review_box(
        route_key="srs",
        title="Review Selection (SR)",
        rows=rows,
        back_to="srs_subjects",
        after_submit_route="srs_menu",
    )
