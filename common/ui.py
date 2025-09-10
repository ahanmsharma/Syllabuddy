import streamlit as st

# ---------- Router & rerun (stable) ----------
def safe_rerun():
    r = getattr(st, "rerun", None)
    if callable(r):
        r()

def go(route: str):
    st.session_state["route"] = route
    safe_rerun()

# ---------- One-time app state init ----------
def ensure_app_state():
    ss = st.session_state
    ss.setdefault("route", "home")

    # data holders that other pages expect (you already populate these elsewhere)
    ss.setdefault("_SUBJECTS", [])
    ss.setdefault("_MODS", {})     # subject -> [modules]
    ss.setdefault("_IQS", {})      # (subject,module) -> [iqs]
    ss.setdefault("_DPS", {})      # (subject,module,iq) -> [dotpoints]

    # global selection of dotpoints {(s,m,iq,dp)}
    ss.setdefault("sel_dotpoints", set())

# ---------- Topbar ----------
def topbar(title: str, back_to: str | None = None):
    c1, c2 = st.columns([1,6])
    with c1:
        if back_to:
            st.button("← Back", key=f"back_{title}", on_click=go, args=(back_to,), use_container_width=True)
    with c2:
        st.title(title)

# ---------- Deterministic stable keys ----------
def k_subject_open(s: str, prefix: str):   return f"{prefix}:open:subject:{s}"
def k_subject_toggle(s: str, prefix: str): return f"{prefix}:toggle:subject:{s}"
def k_module_open(s: str, m: str, prefix: str):   return f"{prefix}:open:module:{s}:{m}"
def k_module_toggle(s: str, m: str, prefix: str): return f"{prefix}:toggle:module:{s}:{m}"
def k_iq_open(s: str, m: str, iq: str, prefix: str):   return f"{prefix}:open:iq:{s}:{m}:{iq}"
def k_iq_toggle(s: str, m: str, iq: str, prefix: str): return f"{prefix}:toggle:iq:{s}:{m}:{iq}"
def k_dp_toggle(s: str, m: str, iq: str, dp: str, prefix: str): return f"{prefix}:toggle:dp:{s}:{m}:{iq}:{dp}"
def stable_key_tuple(item: tuple[str,str,str,str]) -> str:
    s,m,iq,dp = item
    return f"{s}||{m}||{iq}||{dp}"
