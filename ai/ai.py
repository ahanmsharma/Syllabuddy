import streamlit as st
from common.ui import topbar

def page_ai_select():
    go = st.session_state["_go"]
    SUBJECTS = st.session_state["_SUBJECTS"]
    MODS     = st.session_state["_MODS"]
    IQS      = st.session_state["_IQS"]
    DPS      = st.session_state["_DPS"]

    topbar("AI selection — enter weaknesses", back_to="select_subject_main")
    st.write("Type what you struggle with; we’ll propose dotpoints that match (placeholder suggestions for now).")
    st.session_state["ai_weakness_text"] = st.text_area("Weaknesses", key="ai_wk2", height=150,
                      placeholder="e.g., equilibrium constants; vectors; cell transport")
    if st.button("Get suggestions", type="primary"):
        suggestions = []
        for s in SUBJECTS:
            for m in MODS.get(s, []):
                for iq in IQS.get((s, m), []):
                    for dp in DPS.get((s, m, iq), []):
                        suggestions.append((s, m, iq, dp))
        st.session_state["ai_suggested"] = suggestions[:30]
        st.session_state["ai_chosen"] = set()
        go("ai_review")

def page_ai_review():
    go = st.session_state["_go"]
    topbar("Review suggested dotpoints", back_to="ai_select")
    st.write("Click ✅ to keep or ❌ to remove. Green border = kept. The middle scrolls; header & footer stick.")

    chosen = set(st.session_state.get("ai_chosen", set()))
    suggestions = st.session_state.get("ai_suggested", [])

    st.markdown('<div class="scroll-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="scroll-head">AI suggested dotpoints</div>', unsafe_allow_html=True)
    st.markdown('<div class="scroll-body">', unsafe_allow_html=True)

    temp = []
    for idx, item in enumerate(suggestions):
        s, m, iq, dp = item
        sel = item in chosen
        klass = "dp-item selected" if sel else "dp-item"
        st.markdown(f'<div class="{klass}">', unsafe_allow_html=True)
        st.write(f"**{s} → {m} → {iq}** — {dp}")
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("✅ Keep", key=f"ai_keep_{idx}", use_container_width=True):
                chosen.add(item)
        with c2:
            if st.button("❌ Remove", key=f"ai_drop_{idx}", use_container_width=True):
                st.markdown('</div>', unsafe_allow_html=True)
                continue
        st.markdown('</div>', unsafe_allow_html=True)
        temp.append(item)

    st.markdown('</div>', unsafe_allow_html=True)  # body

    st.markdown('<div class="scroll-foot">', unsafe_allow_html=True)
    left, mid, right = st.columns([1,1,1])
    with left:
        if st.button("← Back to Choose Subject"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            go("cram_subjects")
    with mid:
        if st.button("Apply selection", type="primary"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            for it in chosen:
                st.session_state["sel_dotpoints"].add(it)
            st.success("Added selected dotpoints.")
    with right:
        if st.button("Done"):
            st.session_state["ai_suggested"] = temp
            st.session_state["ai_chosen"] = chosen
            go("home")
    st.markdown('</div>', unsafe_allow_html=True)  # foot
    st.markdown('</div>', unsafe_allow_html=True)  # wrap
