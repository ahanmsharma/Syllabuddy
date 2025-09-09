import json, os
import streamlit as st
from typing import Dict, Tuple, List

@st.cache_data(show_spinner=False)
def load_syllabus() -> Dict:
    """
    Loads syllabus.json if present, else returns fallback.
    Structure: {Subject: {Module: {IQ: [dotpoints...]}}}
    """
    # look in repo root (one level up from this file's folder)
    here = os.path.dirname(__file__)
    path = os.path.join(os.path.dirname(here), "syllabus.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    # Fallback (from your monolith)
    return {
        "Biology": {
            "Module 6: Genetic Change": {
                "IQ1: Mutations": [
                    "Describe point vs frameshift mutations",
                    "Explain mutagens and mutation rates"
                ],
                "IQ2: Biotechnology": [
                    "Outline PCR steps and applications",
                    "Summarise CRISPR-Cas9 mechanism"
                ]
            }
        },
        "Chemistry": {
            "Module 5: Equilibrium": {
                "IQ1: Le Chatelier": [
                    "Predict shifts for concentration, pressure, temperature changes",
                    "Relate Kc to reaction quotient Q"
                ]
            }
        }
    }

def explode_syllabus(data: Dict) -> Tuple[List[str], Dict, Dict, Dict]:
    subjects = list(data.keys())
    modules_by_subject = {s: list(data[s].keys()) for s in subjects}
    iqs_by_subject_module = {}
    dps_by_smi = {}
    for s in subjects:
        for m in data[s]:
            iqs = list(data[s][m].keys())
            iqs_by_subject_module[(s, m)] = iqs
            for iq in iqs:
                dps_by_smi[(s, m, iq)] = list(data[s][m][iq])
    return subjects, modules_by_subject, iqs_by_subject_module, dps_by_smi

def ensure_core_state():
    st.session_state.setdefault("sel_dotpoints", set())  # {(s,m,iq,dp)}
    st.session_state.setdefault("focus_subject", None)
    st.session_state.setdefault("focus_module", None)    # (s,m)
    st.session_state.setdefault("focus_iq", None)        # (s,m,iq)
    st.session_state.setdefault("cram_mode", False)
    st.session_state.setdefault("prioritization_mode", False)
    st.session_state.setdefault("ai_weakness_text", "")
    st.session_state.setdefault("ai_strength_text", "")
    st.session_state.setdefault("ai_suggested", [])
    st.session_state.setdefault("ai_chosen", set())
