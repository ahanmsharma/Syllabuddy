import streamlit as st

# ------------------------------
# Central rerun + navigation
# ------------------------------

def safe_rerun():
    """
    Wrapper around st.rerun for compatibility with older/newer Streamlit versions.
    """
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        raise RuntimeError("No rerun method available in this Streamlit version.")

def set_go(go=None):
    """
    Inject a 'go' function into ``st.session_state`` for navigation.

    If ``go`` is ``None`` a default implementation is created which sets the
    ``route`` entry in ``session_state`` and triggers a rerun.  The function
    stored in ``session_state['_go']`` is returned.
    """
    if go is None:
        def go(route: str):
            st.session_state["route"] = route
            safe_rerun()

    # Put it in session_state for global access
    st.session_state["_go"] = go
    return go

def get_go():
    """Helper to retrieve the navigation function from session state."""
    return st.session_state.get("_go")

# ------------------------------
# UI helpers
# ------------------------------

def topbar(title: str, back_to: str = None):
    """
    Simple top bar with optional back button.
    """
    c1, c2 = st.columns([1,6], vertical_alignment="center")
    with c1:
        if back_to:
            if st.button("⬅ Back", key=f"back_{title}"):
                st.session_state["_go"](back_to)
    with c2:
        st.title(title)

# ---------- key helpers (stable keys for widgets) ----------
def k_subject_open(subject: str, prefix: str) -> str:
    return f"{prefix}_subject_open_{subject}"

def k_subject_toggle(subject: str, prefix: str) -> str:
    return f"{prefix}_subject_toggle_{subject}"

def k_module_open(subject: str, module: str, prefix: str) -> str:
    return f"{prefix}_module_open_{subject}_{module}"

def k_module_toggle(subject: str, module: str, prefix: str) -> str:
    return f"{prefix}_module_toggle_{subject}_{module}"

def k_iq_open(subject: str, module: str, iq: str, prefix: str) -> str:
    return f"{prefix}_iq_open_{subject}_{module}_{iq}"

def k_iq_toggle(subject: str, module: str, iq: str, prefix: str) -> str:
    return f"{prefix}_iq_toggle_{subject}_{module}_{iq}"

def k_dp_toggle(subject: str, module: str, iq: str, dp: str, prefix: str) -> str:
    return f"{prefix}_dp_toggle_{subject}_{module}_{iq}_{dp}"

def stable_key_tuple(item: tuple[str, ...]) -> str:
    """Create a stable string key from a tuple of strings.

    The previous implementation simply joined the parts with ``|`` which could
    lead to collisions if any item itself contained that character.  We now
    prefix each part with its length to ensure a reversible, collision‑free
    representation suitable for use as a Streamlit widget key.
    """
    return "|".join(f"{len(part)}:{part}" for part in item)
