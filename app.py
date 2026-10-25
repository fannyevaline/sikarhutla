"""Titik masuk Streamlit - Dashboard Klasifikasi Kerawanan Karhutla Kalimantan."""
import streamlit as st

from domain.sumber_data_service import SumberDataService
from modul import beranda, klasifikasi, simulasi

st.set_page_config(page_title="SiKarhutla", page_icon="🔥", layout="wide")

# Lima halaman; nama -> ikon Material
MODUL = {
    "Beranda": ":material/home:",
    "Klasifikasi": ":material/travel_explore:",
    "Simulasi": ":material/tune:",
    "Performa Model": ":material/insights:",
    "Bantuan": ":material/help:",
}

CSS = """
<style>
[data-testid="stHeader"] { background: transparent; }
.block-container { padding: 1.8rem 2.5rem 3rem; max-width: 100%; }
[class*="st-key-bento"] {
    background: #ffffff; border: 1px solid #ece5dc; border-radius: 18px;
    padding: 1.3rem 1.4rem; box-shadow: 0 1px 2px rgba(60,40,20,0.04);
    transition: box-shadow 0.2s, transform 0.2s;
}
@media (max-width: 1000px) {
    .block-container [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
    .block-container [data-testid="stColumn"] { flex: 1 1 100% !important; min-width: 100%; }
}
[class*="st-key-bento"]:hover {
    box-shadow: 0 10px 28px rgba(60,40,20,0.08); transform: translateY(-2px);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1f1b18 0%, #1a1715 60%, #221714 100%); }
[data-testid="stSidebar"][aria-expanded="true"] { min-width: 290px; }
[data-testid="stSidebar"][aria-expanded="false"] { min-width: 0 !important; width: 0 !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.2rem; }
[data-testid="stSidebar"] button {
    justify-content: flex-start; border: none; border-radius: 10px;
    padding: 0.6rem 0.95rem; background: transparent; color: #b3aba2;
    transition: background 0.15s, color 0.15s;
}
[data-testid="stSidebar"] button:hover { background: #2a2522; color: #ffffff; }
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, rgba(255,146,43,0.25), rgba(224,49,49,0.10));
    color: #ffffff; font-weight: 600; border: none !important;
    box-shadow: inset 3px 0 0 #ff922b;
}
[data-testid="stSidebar"] button > div { justify-content: flex-start; width: 100%; }
[data-testid="stSidebar"] button p { font-size: 0.98rem; text-align: left; }
[data-testid="stSidebar"] button [data-testid="stIconMaterial"] { font-size: 1.25rem;
    margin-right: 0.35rem; color: #8a837b; }
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]
    [data-testid="stIconMaterial"] { color: #ffa94d; }
.sk-logo { display: flex; gap: 0.8rem; align-items: center;
    padding-bottom: 1.3rem; margin-bottom: 1rem; border-bottom: 1px solid #312b27; }
.sk-logo-ikon {
    width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
    background: linear-gradient(135deg, #ffa94d 0%, #f76707 45%, #e03131 100%);
    box-shadow: 0 6px 16px rgba(226,86,43,0.35);
    display: flex; align-items: center; justify-content: center;
}
.sk-logo-ikon div { width: 8px; height: 20px; border-radius: 5px; background: #fff; }
.sk-logo-nama { color: #fff; font-size: 1.35rem; font-weight: 800; line-height: 1.1;
    letter-spacing: -0.01em; }
.sk-logo-sub { color: #9a938b; font-size: 0.8rem; line-height: 1.3; margin-top: 0.15rem; }
.sk-model {
    margin-top: 2.2rem; padding: 0.9rem 1rem; border-radius: 12px;
    background: #24201d; border: 1px solid #332d29;
}
.sk-model-label { color: #8a837b; font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.08em; font-weight: 600; margin-bottom: 0.45rem; }
.sk-model-nama { color: #f1ede8; font-weight: 600; font-size: 0.92rem;
    display: flex; align-items: center; gap: 0.5rem; line-height: 1.8; }
.sk-model-nama span { width: 7px; height: 7px; border-radius: 50%; background: #3fae6a;
    box-shadow: 0 0 0 3px rgba(63,174,106,0.18); }
</style>
"""

LOGO = """
<div class="sk-logo">
  <div class="sk-logo-ikon"><div></div></div>
  <div><div class="sk-logo-nama">SiKarhutla</div>
  <div class="sk-logo-sub">Kerawanan karhutla Kalimantan</div></div>
</div>
"""

MODEL_AKTIF = """
<div class="sk-model">
  <div class="sk-model-label">Model aktif</div>
  <div class="sk-model-nama"><span></span>Random Forest</div>
  <div class="sk-model-nama"><span></span>XGBoost</div>
</div>
"""


def sidebar() -> str:
    if st.session_state.get("menu") not in MODUL:
        st.session_state.menu = "Beranda"
    with st.sidebar:
        st.markdown(LOGO, unsafe_allow_html=True)
        for nama, ikon in MODUL.items():
            aktif = st.session_state.menu == nama
            if st.button(nama, key=f"menu_{nama}", icon=ikon, width="stretch",
                         type="primary" if aktif else "secondary"):
                st.session_state.menu = nama
                st.rerun()
        st.markdown(MODEL_AKTIF, unsafe_allow_html=True)
    return st.session_state.menu


st.markdown(CSS, unsafe_allow_html=True)
sumber = SumberDataService()
pilihan = sidebar()

if pilihan == "Beranda":
    beranda.render(sumber)
elif pilihan == "Klasifikasi":
    klasifikasi.render(sumber)
elif pilihan == "Simulasi":
    simulasi.render(sumber)
else:
    st.title(pilihan)
    st.info("Modul ini belum dibangun.")
