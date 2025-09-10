# srs/srs.py
import streamlit as st
from common.ui import go, ns, get_param

# --- Demo data + helpers ---
def get_items_to_review():
    return [{"id": f"item-{i}", "text": f"Dotpoint {i+1}"} for i in range(5)]

def apply_staged_changes():
    pass

def go_to_next_item():
    st.session_state["review_idx"] += 1
    if st.session_state["review_idx"] >= len(st.session_state["review_items"]):
        go("srs_menu")

def go_to_prev_item():
    st.session_state["review_idx"] = max(0, st.session_state["review_idx"] - 1)

# --- Pages ---
def page_srs_menu():
    st.header("Spaced Repetition")
    if st.button("Review now", key=ns("srs_menu", "review")):
        st.session_state["review_items"] = get_items_to_review()
        st.session_state["review_idx"] = 0
        go("cram_review")

def page_srs_subjects():
    st.header("Subjects")
    st.write("TODO")

def page_srs_modules():
    subject = get_param("subject", "Biology")
    st.header(f"Modules · {subject}")
    st.write("TODO")

def page_srs_iqs():
    st.header("Inquiry Questions")
    st.write("TODO")

def page_srs_dotpoints():
    st.header("Dotpoints")
    st.write("TODO")

# --- Review UI ---
def review_box(item, idx: int):
    box_id = ns("review", item["id"], idx)

    st.subheader(f"📍 {item['text']}")
    answer_key = ns(box_id, "answer")
    st.text_area("Your answer…", key=answer_key, height=120)

    action_key = ns(box_id, "action")
    action = st.radio(
        "Action", ["Keep", "Remove"], index=0, horizontal=True, key=action_key
    )
    if action == "Remove":
        st.error("This item will be removed when you apply changes.")

    note_key = ns(box_id, "note")
    st.text_input("Notes (optional)", key=note_key)

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("← Back", key=ns(box_id, "back")):
        go_to_prev_item()
    if c2.button("Apply", key=ns(box_id, "apply")):
        st.session_state.setdefault("pending_changes", {})[item["id"]] = {
            "action": action,
            "note": st.session_state.get(note_key),
            "answer": st.session_state.get(answer_key),
        }
        st.success("Changes staged.")
    if c3.button("Submit & Continue", key=ns(box_id, "submit")):
        st.session_state.setdefault("pending_changes", {})[item["id"]] = {
            "action": action,
            "note": st.session_state.get(note_key),
            "answer": st.session_state.get(answer_key),
        }
        apply_staged_changes()
        go_to_next_item()

def page_cram_review():
    st.header("Cram Review")
    if "review_items" not in st.session_state:
        st.info("No items queued. Go to SRS menu first.")
        if st.button("Back to menu", key=ns("cram_review", "to_menu")):
            go("srs_menu")
        return

    items = st.session_state["review_items"]
    idx = st.session_state.get("review_idx", 0)
    idx = max(0, min(idx, len(items) - 1))

    st.caption(f"Item {idx+1} of {len(items)}")
    review_box(items[idx], idx)
