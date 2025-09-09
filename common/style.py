import streamlit as st

def inject_css():
    st.markdown("""
<style>
  .block-container { max-width: 1200px; padding-top: 6px; margin: auto; }
  header {visibility: hidden;}
  #MainMenu {visibility: hidden;} footer {visibility: hidden;}

  /* Top bar */
  .topbar { display:flex; align-items:center; justify-content:space-between; margin: 0 0 8px 0; }
  .topbar-left { display:flex; align-items:center; gap:8px; }

  /* Buttons */
  .btn { padding:8px 12px; border-radius:10px; border:1px solid #d1d5db; background:#fff; font-weight:600; }
  .btn.primary { background:#3b82f6; color:#fff; border-color:#2563eb; }
  .btn.ghost { background:#f8fafc; }
  .btn.warn { background:#fee2e2; color:#991b1b; border-color:#fecaca; }

  /* Selection grid cards */
  .grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(320px,1fr)); gap:16px; }
  .card { border:2px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; position:relative; }
  .card.selected { border-color:#3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset; }
  .card-title { font-weight:800; margin-bottom:.35rem; color:#111; }
  .card-sub { color:#4b5563; font-size:.95rem; margin-bottom:.5rem; }

  /* (older AI list class, left for compatibility) */
  .dp-item {
    display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; margin-bottom:10px; background:#fff;
  }
  .dp-item.selected { border-color:#16a34a; box-shadow: inset 0 0 0 2px rgba(22,163,74,.2); }

  /* --- Shared REVIEW CARD styling (used by SR/Cram/AI review) --- */
  .dp-card {
    border: 2px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 14px;
    background: #ffffff;
  }
  .dp-card.green {
    border-color: #16a34a; /* green-600 */
    box-shadow: inset 0 0 0 2px rgba(22,163,74,.18);
  }
  .dp-card.red {
    border-color: #b91c1c; /* red-700 */
    box-shadow: inset 0 0 0 2px rgba(185,28,28,.15);
  }
  .row-top {
    display:flex; align-items:center; justify-content:space-between;
    gap:10px; margin-bottom:8px;
  }
  .title { font-weight: 800; color: #111827; }
  .dp-text { color:#111827; }
  .pill {
    display:inline-block; font-weight:700; font-size:.85rem;
    padding:2px 10px; border-radius:9999px; border:1px solid transparent;
  }
  .pill.keep   { color:#065f46; background:#d1fae5; border-color:#6ee7b7; }
  .pill.remove { color:#7f1d1d; background:#fee2e2; border-color:#fecaca; }

  .review-footer {
    position: relative;
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid #e5e7eb;
  }
</style>
""", unsafe_allow_html=True)
