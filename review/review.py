from typing import List, Tuple
import streamlit as st
from common.ui import topbar, get_go, stable_key_tuple

# Removed key set stored deterministically (no random keys)
def _get_removed(route_key: str) -> set[str]:
    k = f"review:{route_key}:removed"
    if k not in st.session_state:
        st.session_state[k] = set()
    val = st.session_state[k]
    if isinstance(val, list):
        val = {str(x) for x in val}
        st.session_state[k] = val
    return val

def _save_removed(route_key: str, removed: set[str]):
    # store as list for stable serialization
    st.session_state[f"review:{route_key}:removed"] = list(removed)

# theme-aware CSS
REVIEW_CSS = """
<style>
:root{
  --border: #e5e7eb; --text:#111827; --card:#ffffff;
  --ok:#16a34a; --okGlow:rgba(22,163,74,.18);
  --bad:#b91c1c; --badGlow:rgba(185,28,28,.15);
  --divider:#e5e7eb;
}
@media (prefers-color-scheme: dark){
  :root{
    --border:#334155; --text:#e5e7eb; --card:#111827;
    --ok:#22c55e; --okGlow:rgba(34,197,94,.20);
    --bad:#ef4444; --badGlow:rgba(239,68,68,.20);
    --divider:#374151;
  }
}
.dp-card { border:2px solid var(--border); border-radius:12px; padding:12px 14px; margin-bottom:14px; background:var(--card); }
.dp-card.green { border-color:var(--ok); box-shadow: inset 0 0 0 2px var(--okGlow); }
.dp-card.red   { border-color:var(--bad); box-shadow: inset 0 0 0 2px var(--badGlow); }
.row-top { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
.title { font-weight:800; color:var(--text); }
.dp-text { color:var(--text); }
.pill { display:inline-block; font-weight:700; font-size:.85rem; padding:2px 10px; border-radius:9999px; border:1px solid transparent; }
.pill.keep   { color:#065f46; background:#d1fae5; border-color:#6ee7b7; }
.pill.remove { color:#7f1d1d; background:#fee2e2; border-color:#fecaca; }
.review-footer { position:relative; margin-top:16px; padding-top:12px; border-top:1px solid var(--divider); }
</style>
"""

def _pill(is_removed: bool) -> str:
    return '<span class="pill remove">Removed</span>' if is_removed else '<span class="pill keep">Kept</span>'

def _class(is_removed: bool) -> str:
    return "dp-card red" if is_removed else "dp-card green"

def _toggle_label(is_removed: bool) -> str:
    return "🔁 Mark Kept" if is_removed else "🔁 Mark Removed"

def _render_cards(route_key: str, rows: List[Tuple[str, str, str, str]]) -> tuple[int, int]:
    removed = _get_removed(route_key)
    kept_count = 0
    removed_count = 0

    # Each card is a small form so clicks don't interfere with each other.
    # Use the list index as part of the stable key so that identical dotpoints
    # (same subject/module/iq/text) can still be toggled independently. This
    # prevents a toggle on one card from unexpectedly affecting another with
    # the same content.
    for idx, item in enumerate(rows):
        s, m, iq, dp = item
        sk = stable_key_tuple((str(idx),) + item)
        is_removed = (sk in removed)
        cls = _class(is_removed)
        pill = _pill(is_removed)

        with st.container(border=False):
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            st.markdown('<div class="row-top">', unsafe_allow_html=True)
            st.markdown(f'<div class="title">{s} → {m} → {iq}</div>', unsafe_allow_html=True)
            st.markdown(pill, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="dp-text">{dp}</div>', unsafe_allow_html=True)

            with st.form(key=f"frm:card:{route_key}:{idx}"):
                if st.form_submit_button(_toggle_label(is_removed), use_container_width=True):
                    if is_removed:
                        removed.discard(sk)
                    else:
                        removed.add(sk)
                    _save_removed(route_key, removed)
            st.markdown("</div>", unsafe_allow_html=True)

        if sk in removed:
            removed_count += 1
        else:
            kept_count += 1

    return kept_count, removed_count

def review_box(
    route_key: str,
    title: str,
    rows: List[Tuple[str,str,str,str]],
    back_to: str,
    after_submit_route: str,
):
    go = get_go()
    topbar(title, back_to=back_to)
    st.markdown(REVIEW_CSS, unsafe_allow_html=True)

    kept, dropped = _render_cards(route_key, rows)
    st.info(f"Kept: {kept}   |   Removed: {dropped}")

    # Footer as one form so clicks are atomic
    with st.form(key=f"form:footer:{route_key}"):
        c1, c2, c3 = st.columns(3)
        back_click   = c1.form_submit_button("← Back")
        apply_click  = c2.form_submit_button("Apply changes", use_container_width=True)
        submit_click = c3.form_submit_button("Submit & Continue", use_container_width=True)

        if back_click:
            go(back_to)

        if apply_click or submit_click:
            removed = _get_removed(route_key)
            kept_items = {
                itm for idx, itm in enumerate(rows)
                if stable_key_tuple((str(idx),) + itm) not in removed
            }
            st.session_state["sel_dotpoints"] = kept_items
            st.success("Selection updated.")
            # after applying the changes, reset removal marks so indexes stay in sync
            _save_removed(route_key, set())
            if submit_click:
                go(after_submit_route)

# ---- Pages ----
def page_cram_review():
    rows = sorted(list(st.session_state.get("sel_dotpoints", set())))
    review_box("cram", "Review Selection (Cram)", rows, back_to="cram_subjects", after_submit_route="cram_how")

def page_srs_review():
    rows = sorted(list(st.session_state.get("sel_dotpoints", set())))
    review_box("srs", "Review Selection (SR)", rows, back_to="srs_subjects", after_submit_route="srs_menu")
