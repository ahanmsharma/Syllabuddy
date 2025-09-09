import uuid
from typing import List, Set, Tuple
import streamlit as st
from common.ui import topbar, go, safe_rerun

# ---------- Local CSS just for review pages ----------
REVIEW_CSS = """
<style>
.review-card {
  border: 2px solid #e5e7eb;
  border-left-width: 6px;            /* fat left color bar */
  border-radius: 12px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: #ffffff;
}
.review-card.border-green { border-left-color: #16a34a; } /* green-600 */
.review-card.border-red   { border-left-color: #b91c1c; } /* red-700  */

.review-card .row-top {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; margin-bottom: 6px;
}

.review-title {
  font-weight: 800; color: #111827; /* slate-900 */
}

.review-dp {
  color: #111827; margin-bottom: 6px;
}

.status-pill {
  display: inline-block;
  font-weight: 700;
  font-size: 0.85rem;
  padding: 2px 10px;
  border-radius: 9999px;
  border: 1px solid transparent;
}
.status-kept   { color: #065f46; background: #d1fae5; border-color: #6ee7b7; }
.status-removed{ color: #7f1d1d; background: #fee2e2; border-color: #fecaca; }

.review-footer {
  position: relative;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
  background: transparent;
}
</style>
"""

def _stable_key(item: Tuple[str, str, str, str]) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def _card_class(is_removed: bool) -> str:
    return "review-card border-red" if is_removed else "review-card border-green"

def _pill(is_removed: bool) -> str:
    if is_removed:
        return '<span class="status-pill status-removed">Removed</span>'
    return '<span class="status-pill status-kept">Kept</span>'

def review_box(
    route_key: str,
    title: str,
    rows: List[Tuple[str, str, str, str]],
    back_to: str,
    after_submit_route: str,
):
    """
    Clean, stable review UI shared by SR and Cram:
      • Kept (green) by default; clicking Remove flips to red.
      • Status pill (Kept/Removed) and card border color update instantly.
      • Single footer: Back / Apply changes / Submit & Continue.
      • Unique keys per render to avoid duplicate-key issues.
      • No custom scroll wrappers (prevents the 'big white box').
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

    # Render each row as a card
    for idx, item in enumerate(rows):
        s, m, iq, dp = item
        k = _stable_key(item)
        is_removed = (k in removed)

        with st.container(border=False):
            st.markdown(
                f'<div class="{_card_class(is_removed)}">', unsafe_allow_html=True
            )

            # Top row: title + status pill
            st.markdown('<div class="row-top">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="review-title">{s} → {m} → {iq}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_pill(is_removed), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)  # end row-top

            # Dotpoint text
            st.markdown(f'<div class="review-dp">{dp}</div>', unsafe_allow_html=True)

            # Actions
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

    # Footer (single set of buttons; unique keys; no extra containers)
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
