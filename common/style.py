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

  /* Cards / grid */
  .grid { display:grid; grid-template-columns: repeat(auto-fill,minmax(320px,1fr)); gap:16px; }
  .card { border:2px solid #e5e7eb; border-radius:14px; padding:14px; background:#fff; position:relative; }
  .card.selected { border-color:#3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.25) inset; }
  .card-title { font-weight:800; margin-bottom:.35rem; color:#111; }
  .card-sub { color:#4b5563; font-size:.95rem; margin-bottom:.5rem; }

  /* Generic dp-item used in AI review page */
  .dp-item {
    display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:10px 12px; border:1px solid #e5e7eb; border-radius:10px; margin-bottom:10px; background:#fff;
  }
  .dp-item.selected { border-color:#16a34a; box-shadow: inset 0 0 0 2px rgba(22,163,74,.2); }
</style>
""", unsafe_allow_html=True)
