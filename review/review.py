import uuid
from typing import List, Tuple, Set
import streamlit as st
from common.ui import topbar, go

# --------- helpers ---------
def _stable_key(item: Tuple[str, str, str, str]) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def _get_removed(route_key: str) -> Set[str]:
    """Store as list in session state for safety; expose as a set in code."""
    k = f"__rb_removed__::{route_key}"
    if k not in st.session_state:
        st.session_state[k] = []  # list of stable keys
    return set(st.session_state[k])

def _set_removed(route_key: str, removed_set: Set[str]) -> None:
    k = f"__rb_removed__::{route_key}"
    st.session_state[k] = list(removed_set)

def _rerun():
    # Avoid experimental_*; use st.rerun if present, else no-op
    r = getattr(st, "rerun", None)
    if callable(r):
        r()

# --------- theme-aware CSS (dark/light) ---------
REVIEW_CSS = """
<style>
:root{
  --border: #e5e7eb;       /* slate-200 */
  --text:   #111827;       /* slate-900 */
  --card:   #ffffff;
  --ok:     #16a34a;       /* green-600 */
  --okGlow: rgba(22,163,74,.18);
  --bad:    #b91c1c;       /* red-700 */
  --badGlow:rgba(185,28,28,.15);
  --pillKeepFg:#065f46; --pillKeepBg:#d1fae5; --pillKeepBd:#6ee7b7;
  --pillRemFg:#7f1d1d; --pillRemBg:#fee2e2; --pillRemBd:#fecaca;
  --divider:#e5e7eb;
  --infoBg: #f8fafc;
}
@media (prefers-color-scheme: dark){
  :root{
    --border:#334155;      /* slate-700 */
    --text:#e5e7eb;        /* slate-200 */
    --card:#111827;        /* slate-900-ish */
    --ok:#22c55e;          /* green-500 */
    --okGlow:rgba(34,197,94,.20);
    --bad:#ef4444;         /* red-500 */
    --badGlow:rgba(239,68,68,.20);
    --pillKeepFg:#052e1e; --pillKeepBg:#86efac; --pillKeepBd:#4ade80;
    --pillRemFg:#450a0a;  --pillRemBg:#fecaca; --pillRemBd:#fca5a5;
    --divider:#374151;
    --infoBg:#0b1220;
  }
}

.dp-card {
  border: 2px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: var(--card);
}
.dp-card.green {
  border-color: var(--ok);
  box-shadow: inset 0 0 0 2px var(--okGlow);
}
.dp-card.red {
  border-color: var(--bad);
  box-shadow: inset 0 0 0 2px var(--badGlow);
}
.row-top {
  display:flex; align-items:center; justify-content:space-between;
  gap:10px; margin-bottom:8px;
}
.title { font-weight: 800; color: var(--text); }
.dp-text { color: var(--text); }

.pill {
  display:inline-block; font-weight:700; font-size:.85rem;
  padding:2px 10px; border-radius:9999px; border:1px solid transparent;
}
.pill.keep   { color:var(--pillKeepFg); background:var(--pillKeepBg); border-color:var(--pillKeepBd); }
.pill.remove { color:var(--pillRemFg);  background:var(--pillRemBg);  border-color:var(--pillRemBd);  }

.review-footer {
  position: relative;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--divider);
  background: transparent;
}
</style>
"""

def _class_and_pill(is_removed: bool) -> Tuple[str, str]:
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
    Unified review UI (SR & Cram):
      • Default = Kept (green). Clicking Remove marks red.
      • Status pill + card border update immediately.
      • Bottom buttons Back / Apply / Submit work reliably.
      • Keys are unique per render to avoid collisions.
    """
    topbar(title, back_to=back_to)
    st.markdown(REVIEW_CSS, unsafe_allow_html=True)

    # Per-render key prefix
    inst = uuid.uuid4().hex[:6]
    KP = f"{route_key}_rb_{inst}"

    # Route-scoped removed set (persisted via list in session_state)
    removed = _get_removed(route_key)

    st.caption(f"Total selected dotpoints: **{len(rows)}**")

    # Render each selected dotpoint
    for idx, item in enumerate(rows):
        s, m, iq, dp = item
        k = _stable_key(item)
        is_removed = (k in removed)

        card_class, pill_html = _class_and_pill(is_removed)

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
                    if k in removed:
                        removed.remove(k)
                        _set_removed(route_key, removed)
                        _rerun()
            with c2:
                if st.button("Remove", key=f"{KP}_remove_{idx}", use_container_width=True):
                    if k not in removed:
                        removed.add(k)
                        _set_removed(route_key, removed)
                        _rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # end card

    kept_count = len(rows) - len(removed)
    st.info(f"Kept: {kept_count}   |   Removed: {len(removed)}")

    # Footer buttons
    st.markdown('<div class="review-footer">', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)

    with f1:
        if st.button("← Back", key=f"{KP}_back"):
            go(back_to)

    def _apply(go_next: bool):
        # Final kept = all rows except those in `removed`
        kept_items = {itm for itm in rows if _stable_key(itm) not in removed}
        st.session_state["sel_dotpoints"] = kept_items
        st.success("Selection updated.")
        if go_next:
            # clear route cache so next visit starts fresh
            _set_removed(route_key, set())
            go(after_submit_route)

    with f2:
        if st.button("Apply changes", key=f"{KP}_apply", type="primary"):
            _apply(go_next=False)

    with f3:
        if st.button("Submit & Continue", key=f"{KP}_submit", type="primary"):
            _apply(go_next=True)

    st.markdown("</div>", unsafe_allow_html=True)  # end footer

# ---- PAGE FUNCTIONS (imported by streamlit_app) ----
def page_cram_review():
    rows = sorted(list(st.session_state.get("sel_dotpoints", set())))
    review_box(
        route_key="cram",
        title="Review Selection (Cram)",
        rows=rows,
        back_to="cram_subjects",
        after_submit_route="cram_how",
    )

def page_srs_review():
    rows = sorted(list(st.session_state.get("sel_dotpoints", set())))
    review_box(
        route_key="srs",
        title="Review Selection (SR)",
        rows=rows,
        back_to="srs_subjects",
        after_submit_route="srs_menu",
    )
