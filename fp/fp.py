# fp/fp.py
from __future__ import annotations
import random, re, pathlib
from typing import Dict, List, Tuple, Optional

import streamlit as st
from common.ui import topbar, go
import streamlit.components.v1 as components

# ---------- Try to attach your existing DnD component ----------
# Expected build path: <repo_root>/frontend/build
# This file is <repo_root>/fp/fp.py → so go up one and into frontend/build
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DND_BUILD = _REPO_ROOT / "frontend" / "build"
if _DND_BUILD.exists():
    _dnd_cloze_comp = components.declare_component("dnd_cloze", path=str(_DND_BUILD))
else:
    _dnd_cloze_comp = None  # will fall back to click-place UI


# ---------- FP engine state ----------
def ensure_fp_state():
    ss = st.session_state
    ss.setdefault("fp_stage", "report")   # report, cloze, post_cloze, followups, done
    ss.setdefault("fp_reports", {"weaknesses":"", "strengths":""})
    ss.setdefault("fp_weak_list", [])
    ss.setdefault("fp_queue", [])         # [{"name": str, "phase": "specific"|"general"}]
    ss.setdefault("fp_ptr", 0)
    ss.setdefault("fp_phase_attempts", 0)

    # cloze state
    ss.setdefault("fp_current_cloze", None)
    ss.setdefault("fp_cloze_specificity", 0)  # 0 general, 1 specific
    ss.setdefault("fp_segs", None)
    ss.setdefault("fp_answers", None)
    ss.setdefault("fp_bank", None)
    ss.setdefault("fp_fills", None)       # List[Optional[str]]
    ss.setdefault("fp_flags", None)       # List[bool]
    ss.setdefault("fp_last_score", None)  # (correct,total)


def _current_target() -> Tuple[Optional[str], Optional[str]]:
    ss = st.session_state
    if 0 <= ss.get("fp_ptr",0) < len(ss.get("fp_queue",[])):
        item = ss["fp_queue"][ss["fp_ptr"]]
        return item["name"], item["phase"]
    return None, None


# ---------- Cloze generation ----------
def _placeholder_cloze(weakness: str, specificity: int) -> str:
    w = weakness or "the topic"
    if specificity == 1:
        bank = [
            f"{w} requires [stepwise] [reasoning] from [first principles].",
            f"In {w}, common pitfalls include [confusing] [definitions] and [examples].",
            f"To approach {w}, first [define] the [system], then [isolate] variables."
        ]
    else:
        bank = [
            f"{w} focuses on [understanding] [core] [ideas].",
            f"Good practice for {w} is [clarity], [accuracy], and [consistency].",
            f"A routine for {w} is [recall], [apply], then [reflect]."
        ]
    return random.choice(bank)


def _split_cloze(text: str) -> Tuple[List[str], List[str]]:
    parts = re.split(r"\[([^\]]+)\]", text)
    segs, ans = [], []
    for i,p in enumerate(parts):
        if i % 2 == 0:
            segs.append(p)
        else:
            ans.append(p)
    if len(segs) == len(ans):
        segs.append("")
    return segs, ans


# ---------- UI: your DnD component (preferred) OR click-to-place fallback ----------
def _render_cloze_with_dnd(segs: List[str], answers: List[str], fills: List[Optional[str]], keyp: str) -> List[Optional[str]]:
    """
    Calls your compiled component at frontend/build.
    Contract (flexible to your previous version):
      - We pass: segments, answers, initial_bank, initial_fills
      - We expect back a dict with 'fills' (List[str|None]). If None/empty, keep old fills.
    """
    placed = [f if (f is None or isinstance(f, str)) else str(f) for f in fills]
    # initial bank = answers (shuffled)
    bank = answers[:]
    random.shuffle(bank)

    result = _dnd_cloze_comp(
        segments=segs,
        answers=answers,
        initial_bank=bank,
        initial_fills=placed,
        key=f"dnd_{keyp}",
        default=None,
    )
    if isinstance(result, dict) and "fills" in result and isinstance(result["fills"], list):
        new_fills = []
        for x in result["fills"]:
            if x in (None, "", " "):
                new_fills.append(None)
            else:
                new_fills.append(str(x))
        return new_fills
    # defensive: keep prior fills if component returns nothing
    return fills


def _render_cloze_click_place(segs: List[str], answers: List[str], fills: List[Optional[str]], keyp: str) -> List[Optional[str]]:
    """
    Fallback if the DnD component isn't available.
    Click a bank chip, then click a blank. Click a filled blank to clear.
    """
    st.markdown("""
    <style>
    .fp-sent { font-size:1.05rem; line-height:1.7; }
    .chip { display:inline-block; margin:6px 6px 0 0; padding:6px 10px;
            border-radius:999px; border:1px solid var(--border, #d1d5db); background:#fff; }
    .chip.used { opacity:.45; }
    .blank { display:inline-block; min-width:8ch; padding:2px 8px; margin:0 4px;
             border-bottom:2px solid #94a3b8; border-radius:6px; background:#f8fafc; cursor:pointer; }
    @media (prefers-color-scheme: dark){
      .chip{ background:#111827; border-color:#334155; }
      .blank{ background:#0b1220; }
    }
    </style>
    """, unsafe_allow_html=True)

    state_key = f"{keyp}:pending_word"
    if state_key not in st.session_state:
        st.session_state[state_key] = None

    def choose_word(w:str):
        st.session_state[state_key] = w

    def place_word(i:int):
        pending = st.session_state.get(state_key)
        if pending:
            fills[i] = pending
            st.session_state[state_key] = None

    def clear_word(i:int):
        fills[i] = None

    # sentence
    st.markdown('<div class="fp-sent">', unsafe_allow_html=True)
    for i in range(len(answers)):
        st.write(segs[i], unsafe_allow_html=True)
        label = fills[i] if fills[i] else "________"
        if st.button(label, key=f"{keyp}:blank:{i}", help="Click to place / clear"):
            if fills[i] is None:
                place_word(i)
            else:
                clear_word(i)
    st.write(segs[-1], unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # bank
    st.caption("Word bank")
    placed = set([f for f in fills if f])
    available = [w for w in answers if w not in placed]
    bank_cols = st.columns(max(1, min(4, len(available) or 1)))
    for idx, w in enumerate(available):
        with bank_cols[idx % len(bank_cols)]:
            if st.button(w, key=f"{keyp}:bank:{idx}"):
                choose_word(w)

    pending = st.session_state.get(state_key)
    if pending:
        st.info(f"Selected word: **{pending}** — now click a blank to place it.")

    return fills


def _render_cloze(segs: List[str], answers: List[str], fills: List[Optional[str]], keyp: str) -> List[Optional[str]]:
    if _dnd_cloze_comp is not None:
        return _render_cloze_with_dnd(segs, answers, fills, keyp)
    return _render_cloze_click_place(segs, answers, fills, keyp)


# ---------- Public pages ----------
def page_weakness_report():
    ensure_fp_state()
    topbar("AI selection — enter weaknesses", back_to="select_subject_main")
    st.write("Enter weaknesses (semicolon-separated). The flow will cover **specific** then **general** for each weakness. "
             "If you add **specific** sub-weaknesses later, they run before returning to the general item.")

    wk = st.text_area("Weaknesses", key="fp_wk_report", height=150,
                      placeholder="e.g., equilibrium constants; vectors; cell transport")
    stg = st.text_area("Strengths (optional)", key="fp_stg_report", height=100,
                      placeholder="e.g., definitions; diagrams")

    if st.button("Continue", type="primary", use_container_width=True):
        ss = st.session_state
        ss["fp_weak_list"] = [w.strip() for w in (wk or "").split(";") if w.strip()][:5]
        ss["fp_reports"]["strengths"] = stg or ""
        queue = []
        for w in ss["fp_weak_list"]:
            queue.append({"name": w, "phase": "specific"})
            queue.append({"name": w, "phase": "general"})
        ss["fp_queue"] = queue
        ss["fp_ptr"] = 0
        ss["fp_phase_attempts"] = 0

        # reset cloze state
        ss["fp_current_cloze"] = None
        ss["fp_cloze_specificity"] = 1 if queue else 0
        ss["fp_segs"] = None
        ss["fp_answers"] = None
        ss["fp_bank"] = None
        ss["fp_fills"] = None
        ss["fp_flags"] = None
        ss["fp_last_score"] = None

        ss["fp_stage"] = "cloze" if queue else "done"
        go("fp_flow")


def page_fp_flow():
    ensure_fp_state()
    ss = st.session_state

    topbar("Focused Practice (Specific → General)", back_to="weakness_report")

    if ss["fp_stage"] == "done":
        st.success("Weakness cycle complete. (You can return Home or add more weaknesses.)")
        if st.button("Add more weaknesses"):
            go("weakness_report")
        return

    # ---------- CLOZE ----------
    if ss["fp_stage"] == "cloze":
        wname, phase = _current_target()
        if wname is None:
            ss["fp_stage"] = "done"
            go("fp_flow")
            return

        ss["fp_cloze_specificity"] = 1 if phase == "specific" else 0

        if not ss["fp_current_cloze"]:
            text = _placeholder_cloze(wname, ss["fp_cloze_specificity"])
            segs, ans = _split_cloze(text)
            bank = ans[:]
            random.shuffle(bank)
            ss["fp_current_cloze"] = text
            ss["fp_segs"] = segs
            ss["fp_answers"] = ans
            ss["fp_bank"] = bank
            ss["fp_fills"] = [None] * len(ans)
            ss["fp_flags"] = None

        st.markdown(f"**Targeting:** `{wname}` — _{phase}_")

        # --- DnD (or fallback) ---
        ss["fp_fills"] = _render_cloze(ss["fp_segs"], ss["fp_answers"], ss["fp_fills"],
                                       keyp=f"fp:{ss['fp_ptr']}:{phase}")

        # Submit
        if st.button("Submit", type="primary", use_container_width=True, key=f"fp_submit_{ss['fp_ptr']}_{phase}"):
            got = [(x or "") for x in ss["fp_fills"]]
            flags = [a.strip().lower() == g.strip().lower() for a, g in zip(ss["fp_answers"], got)]
            ss["fp_flags"] = flags
            st.rerun()

        # Feedback + Continue
        if ss["fp_flags"] is not None:
            c = sum(ss["fp_flags"])
            total = len(ss["fp_flags"]) or 1
            ok = (c == total)
            st.info(f"Cloze result: **{c}/{total}** — {'🟢 Correct' if ok else '🟡 Mixed'}")
            if st.button("Continue", use_container_width=True, key=f"fp_cont_{ss['fp_ptr']}_{phase}"):
                ss["fp_last_score"] = (c, total)
                ss["fp_stage"] = "post_cloze"
                st.rerun()
        return

    # ---------- POST-CLOZE ----------
    if ss["fp_stage"] == "post_cloze":
        wname, phase = _current_target()
        c, t = ss["fp_last_score"] if ss["fp_last_score"] else (0,0)
        st.info(f"Cloze score: {c}/{t} — Target: {wname} / {phase}")

        colA, colB = st.columns([1,1], gap="large")
        with colA:
            rating = st.slider("Rate your understanding (0–10)", 0, 10, 6,
                               key=f"fp_rate_{ss['fp_ptr']}_{phase}")
        with colB:
            # Specific sub-weaknesses here jump ahead of current general
            more_w = st.text_input(
                "Add weaknesses (semicolon-separated)",
                key=f"fp_more_{ss['fp_ptr']}_{phase}",
                placeholder="e.g., boundary conditions; term definitions"
            )

        if st.button("Continue", use_container_width=True, key=f"fp_next_{ss['fp_ptr']}_{phase}"):
            # Insert sub-weaknesses **right after current item** (specific then general)
            insert_at = ss["fp_ptr"] + 1
            add_list = [w.strip() for w in (more_w or "").split(";") if w.strip()]
            for w in reversed(add_list):  # reversed → first entered appears first after current
                if not any(item["name"] == w for item in ss["fp_queue"]):
                    ss["fp_queue"].insert(insert_at, {"name": w, "phase": "general"})
                    ss["fp_queue"].insert(insert_at, {"name": w, "phase": "specific"})

            if rating <= 6:
                # retry same item with fresh cloze
                ss["fp_phase_attempts"] += 1
                ss["fp_current_cloze"] = None
                ss["fp_segs"] = None
                ss["fp_answers"] = None
                ss["fp_bank"] = None
                ss["fp_fills"] = None
                ss["fp_flags"] = None
                ss["fp_stage"] = "cloze"
            else:
                ss["fp_phase_attempts"] = 0
                ss["fp_stage"] = "followups"
            st.rerun()
        return

    # ---------- FOLLOW-UPS ----------
    if ss["fp_stage"] == "followups":
        wname, phase = _current_target()
        if wname is None:
            ss["fp_stage"] = "done"
            go("fp_flow")
            return

        st.markdown(f"**Follow-up first-principles questions for:** _{wname} / {phase}_")
        q1 = f"Explain {wname} in your own words, then give a simple example."
        q2 = f"List two common mistakes in {wname} and how to avoid them."

        with st.form(key=f"fp_follow_{ss['fp_ptr']}_{phase}"):
            a1 = st.text_area("Q1: " + q1, height=160)
            a2 = st.text_area("Q2: " + q2, height=160)
            submitted = st.form_submit_button("Next")
        if submitted:
            # advance pointer and reset cloze for next phase/item
            ss["fp_ptr"] += 1
            ss["fp_current_cloze"] = None
            ss["fp_segs"] = None
            ss["fp_answers"] = None
            ss["fp_bank"] = None
            ss["fp_fills"] = None
            ss["fp_flags"] = None
            ss["fp_cloze_specificity"] = 0
            ss["fp_stage"] = "cloze" if ss["fp_ptr"] < len(ss["fp_queue"]) else "done"
            st.rerun()
        return
