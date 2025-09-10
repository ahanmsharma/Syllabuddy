import uuid
import streamlit as st
from common.ui import topbar, go

def _key_for(item) -> str:
    s, m, iq, dp = item
    return f"{s}||{m}||{iq}||{dp}"

def _rerun():
    r = getattr(st, "rerun", None)
    if callable(r):
        r()

# Theme-aware card CSS matches review pages
AI_CSS = """
<style>
:root{
  --border: #e5e7eb; --text:#111827; --card:#ffffff;
  --ok:#16a34a; --okGlow:rgba(22,163,74,.18);
  --bad:#b91c1c; --badGlow:rgba(185,28,28,.15);
  --pillKeepFg:#065f46; --pillKeepBg:#d1fae5; --pillKeepBd:#6ee7b7;
  --pillRemFg:#7f1d1d; --pillRemBg:#fee2e2; --pillRemBd:#fecaca;
  --divider:#e5e7eb;
}
@media (prefers-color-scheme: dark){
  :root{
    --border:#334155; --text:#e5e7eb; --card:#111827;
    --ok:#22c55e; --okGlow:rgba(34,197,94,.20);
    --bad:#ef4444; --badGlow:rgba(239,68,68,.20);
    --pillKeepFg:#052e1e; --pillKeepBg:#86efac; --pillKeepBd:#4ade80;
    --pillRemFg:#450a0a; --pillRemBg:#fecaca; --pillRemBd:#fca5a5;
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
.pill.keep   { color:var(--pillKeepFg); background:var(--pillKeepBg); border-color:var(--pillKeepBd); }
.pill.remove { color:var(--pillRemFg);  background:var(--pillRemBg);  border-color:var(--pillRemBd);  }
.review-footer { position:relative; margin-top:16px; padding-top:12px; border-top:1px solid var(--divider); }
</style>
"""

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

        # Use status dict; default is Kept (green) unless explicitly removed
        st.session_state["ai_removed"] = []  # list of keys that user removed
        go("ai_review")

def page_ai_review():
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.markdown(AI_CSS, unsafe_allow_html=True)
    st.write("Click ✅ Keep (green) or ❌ Remove (red). Tally updates live. Use 'Apply selection' to add kept items.")

    suggested = st.session_state.get("ai_suggested", [])
    removed_keys: list = st.session_state.get("ai_removed", [])
    removed = set(removed_keys)

    inst = uuid.uuid4().hex[:6]
    KP = f"ai_rev_{inst}"

    kept_count = 0
    removed_count = 0

    for idx, item in enumerate(suggested):
        k = _key_for(item)
        is_removed = (k in removed)
        card_class = "dp-card red" if is_removed else "dp-card green"
        pill_html  = '<span class="pill remove">Removed</span>' if is_removed else '<span class="pill keep">Kept</span>'

        if is_removed: removed_count += 1
        else: kept_count += 1

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
                    if k in removed:
                        removed.remove(k)
                        st.session_state["ai_removed"] = list(removed)
                        _rerun()
            with c2:
                if st.button("❌ Remove", key=f"{KP}_remove_{idx}", use_container_width=True):
                    if k not in removed:
                        removed.add(k)
                        st.session_state["ai_removed"] = list(removed)
                        _rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # end card

    st.info(f"Kept: {kept_count}   |   Removed: {removed_count}")

    # Footer
    st.markdown('<div class="review-footer">', unsafe_allow_html=True)
    left, mid, right = st.columns(3)
    with left:
        if st.button("← Back to Choose Subject", key=f"{KP}_back"):
            go("cram_subjects")

    def _apply_selection(go_home: bool):
        sel = st.session_state.get("sel_dotpoints", set())
        for item in suggested:
            if _key_for(item) not in removed:
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
