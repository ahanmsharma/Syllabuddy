import uuid
from typing import List, Set, Tuple
import streamlit as st
from common.ui import topbar, go

# ---------- Local CSS just for review pages ----------
REVIEW_CSS = """
<style>
/* Card */
.dp-card {
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: #ffffff;
}
.dp-card.green {
  border-color: #16a34a; /* green-600 */
  box-shadow: inset 0 0 0 2px rgba(22,163,74,.18);
}
.dp-card.red {
  border-color: #b91c1c; /* red-700 */
  box-shadow: inset 0 0 0 2px rgba(185,28,28,.15);
}

/* Top row: subject/module/iq + status pill */
.row-top {
  display:flex; align-items:center; justify-content:space-between;
  gap:10px; margin-bottom:8px;
}
.title {
  font-weight: 800; color: #111827;
}
.dp-text { color:#111827; }

/* Status pill */
.pill {
  display:inline-block; font-weight:700; font-size:.85rem;
  padding:2px 10px; border-radius:9999px; border:1px solid transparent;
}
.pill.keep   { color:#065f46; background:#d1fae5; border-color:#6ee7b7; }   /* green */
.pill.remove { color:#7f1d1d; background:#fee2e2; border-color:#fecaca; }   /* red */

/* Footer */
.review-footer {
  position: relative;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}
</style>
"""

def _stable_key(item: Tuple[str, str, str, str]) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def _class_and_pill(is_removed: bool) -> Tuple[str, str]:
    """Return (card_class, pill_html)."""
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
    Clean, stable review UI shared by SR and Cram:
      • Kept (green) by default; clicking Remove toggles to red.
      • Status pill and card border color update immediately.
      • Single footer: Back / Apply changes / Submit & Continue.
      • Unique keys per render to avoid duplicate-key issues.
      • No custom scroll wrappers.
    """
    topbar(title, back_to=back_to)
    st.markdown(REVIEW_CSS, unsafe_allow_html=True)

    # Per-render instance key to avoid duplicate widget keys even on rapid reruns
    instance = uuid.uuid4().hex[:6]
    KP = f"{route_key}_rb_{instance}"

    # Route-scoped "removed" set
    removed_key = f"__rb_removed__::{route_key}"
    if removed_key not in st.session_state:
        st.session_state[removed_key] = set()
    removed: Set[str] = st.session_state[removed_key]

    st.caption(f"Total selected dotpoints: **{len(rows)}**")

    # Render each row as a consistent card
    for idx, item in enumerate(rows):
        s, m, iq, dp = item
        k = _stable_key(item)
        is_removed = (k in removed)

        card_class, pill_html = _class_and_pill(is_removed)

        with st.container(border=False):
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

            # Title + pill on top
            st.markdown('<div class="row-top">', unsafe_allow_html=True)
            st.markdown(f'<div class="title">{s} → {m} → {iq}</div>', unsafe_allow_html=True)
            st.markdown(pill_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Dotpoint text
            st.markdown(f'<div class="dp-text">{dp}</div>', unsafe_allow_html=True)

            # Actions
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Keep", key=f"{KP}_keep_{idx}", use_container_width=True):
                    # kept by default; ensure it's not in removed
                    if k in removed:
                        removed.remove(k)
                    # no explicit rerun needed; button click already reruns the script
            with c2:
                if st.button("Remove", key=f"{KP}_remove_{idx}", use_container_width=True):
                    removed.add(k)

            st.markdown("</div>", unsafe_allow_html=True)  # end card

    kept_count = len(rows) - len(removed)
    st.info(f"Kept: {kept_count}   |   Removed: {len(removed)}")

    # Footer (single set of buttons)
    st.markdown('<div class="review-footer">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)

    with f1:
        if st.button("← Back", key=f"{KP}_back"):
            go(back_to)

    def _apply(go_next: bool):
        # Compute final kept items
        kept_items = {itm for itm in rows if _stable_key(itm) not in removed}
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
