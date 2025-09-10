from typing import List, Tuple
import streamlit as st
from common.ui import topbar, get_go, stable_key_tuple

AI_CSS = """
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

def _get_removed_ai() -> set[str]:
    k = "ai:removed"
    if k not in st.session_state:
        st.session_state[k] = set()
    if isinstance(st.session_state[k], list):
        st.session_state[k] = set(st.session_state[k])
    return st.session_state[k]

def _save_removed_ai(removed: set[str]):
    st.session_state["ai:removed"] = set(removed)

def _pill(is_removed: bool) -> str:
    return '<span class="pill remove">Removed</span>' if is_removed else '<span class="pill keep">Kept</span>'

def _class(is_removed: bool) -> str:
    return "dp-card red" if is_removed else "dp-card green"

def page_ai_select():
    go = get_go()
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
        suggestions: list[Tuple[str,str,str,str]] = []
        for s in SUBJECTS:
            for m in MODS.get(s, []):
                for iq in IQS.get((s, m), []):
                    for dp in DPS.get((s, m, iq), []):
                        suggestions.append((s, m, iq, dp))
        st.session_state["ai_suggested"] = suggestions[:40]
        st.session_state["ai:removed"] = set()
        go("ai_review")

def page_ai_review():
    go = get_go()
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.markdown(AI_CSS, unsafe_allow_html=True)
    st.write("Toggle each card to Kept (green) or Removed (red). Tally updates live. Apply to add kept items.")

    suggested: List[Tuple[str,str,str,str]] = st.session_state.get("ai_suggested", [])
    removed = _get_removed_ai()

    kept_count = 0
    removed_count = 0

    for item in suggested:
        sk = stable_key_tuple(item)
        is_removed = (sk in removed)
        cls = _class(is_removed)
        pill = _pill(is_removed)

        s,m,iq,dp = item
        with st.container(border=False):
            st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
            st.markdown('<div class="row-top">', unsafe_allow_html=True)
            st.markdown(f'<div class="title">{s} → {m} → {iq}</div>', unsafe_allow_html=True)
            st.markdown(pill, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="dp-text">{dp}</div>', unsafe_allow_html=True)

            with st.form(key=f"form:ai:{sk}"):
                toggled = st.form_submit_button("🔁 Toggle Remove/Keep", use_container_width=True)
                if toggled:
                    if is_removed:
                        removed.discard(sk)
                    else:
                        removed.add(sk)
                    _save_removed_ai(removed)

            st.markdown("</div>", unsafe_allow_html=True)

        if sk in removed:
            removed_count += 1
        else:
            kept_count += 1

    st.info(f"Kept: {kept_count}   |   Removed: {removed_count}")

    with st.form(key="form:ai:footer"):
        left, mid, right = st.columns(3)
        back = left.form_submit_button("← Back to Choose Subject")
        apply_btn = mid.form_submit_button("Apply selection", use_container_width=True)
        done_btn  = right.form_submit_button("Done", use_container_width=True)

        if back:
            go("cram_subjects")

        if apply_btn or done_btn:
            sel = st.session_state.get("sel_dotpoints", set())
            for it in suggested:
                if stable_key_tuple(it) not in removed:
                    sel.add(it)
            st.session_state["sel_dotpoints"] = sel
            st.success("Added kept dotpoints.")
            if done_btn:
                go("home")
