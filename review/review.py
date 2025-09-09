import uuid
from typing import List, Set, Tuple
import streamlit as st
from common.ui import topbar, go, safe_rerun

def _stable_key(item: Tuple[str, str, str, str]) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def _inject_local_css():
    st.markdown(
        """
<style>
/* Local, review-only styles: safe and minimal */
.review-card {
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #ffffff;
}
.review-card .strip {
  height: 6px;
  border-radius: 6px;
  margin: -10px -12px 10px -12px;
}
.review-card .title {
  font-weight: 700;
  margin-bottom: 4px;
  color: #111827;
}
.review-card .dp {
  color: #111827;
}
.review-footer {
  position: relative;
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
  background: transparent;
}
.status-pill {
  display: inline-block;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
}
.status-kept {
  color: #065f46; background: #d1fae5; border: 1px solid #6ee7b7;
}
.status-removed {
  color: #7f1d1d; background: #fee2e2; border: 1px solid #fecaca;
}
</style>
        """,
        unsafe_allow_html=True,
    )

def review_box(
    route_key: str,
    title: str,
    rows: List[Tuple[str, str, str, str]],
    back_to: str,
    after_submit_route: str,
):
    """
    Clean, stable review UI:
      - Kept by default (green). Press Remove to mark red.
      - Keep/Remove updates immediately (using a small per-route state set).
      - Single footer: Back / Apply changes / Submit & Continue.
      - Unique keys per render to avoid duplicate-key issues.
      - No custom scroll containers that cause the “big white box”.
    """
    topbar(title, back_to=back_to)
    _inject_local_css()

    # Per-render instance key to avoid duplicate widget keys even on rapid reruns
    instance = uuid.uuid4().hex[:6]
    KP = f"{route_key}_rb_{instance}"

    # Route-scoped "removed" set
    removed_key = f"__rb_removed__::{route_key}"
    if removed_key not in st.session_state:
        st.session_state[removed_key] = set()
    removed: Set[str] = st.session_state[removed_key]

    st.caption(f"Total selected dotpoints: **{len(rows)}**")

    # Render each row
    for idx, item in enumerate(rows):
        k = _stable_key(item)
        is_removed = (k in removed)

        strip_color = "#b91c1c" if is_removed else "#16a34a"
        status_label = "Removed" if is_removed else "Kept"
        status_class = "status-removed" if is_removed else "status-kept"

        s, m, iq, dp = item
        with st.container(border=False):
            # Card
            st.markdown('<div class="review-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="strip" style="background:{strip_color};"></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="title">{s} → {m} → {iq}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dp">{dp}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="status-pill {status_class}">{status_label}</span>',
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Keep", key=f"{KP}_keep_{idx}", use_container_width=True):
                    if k in removed:
                        removed.remove(k)
                    safe_rerun()
            with c2:
                if st.button("Remove", key=f"{KP}_remove_{idx}", use_container_width=True):
                    removed.add(k)
                    safe_rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # end .review-card

    kept_count = len(rows) - len(removed)
    st.info(f"Kept: {kept_count}   |   Removed: {len(removed)}")

    # Footer (single set of buttons; no duplicate keys; no extra white boxes)
    st.markdown('<div class="review-footer">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        if st.button("← Back", key=f"{KP}_back"):
            go(back_to)

    def _apply(go_next: bool):
        # Compute final kept items
        def kept(itm: Tuple[str, str, str, str]) -> bool:
            return _stable_key(itm) not in removed
        kept_items = {itm for itm in rows if kept(itm)}
        st.session_state["sel_dotpoints"] = kept_items
        st.success("Selection updated.")
        if go_next:
            # clear the removed cache so a fresh visit starts clean
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
