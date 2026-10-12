"""Titik masuk Streamlit - Dashboard Klasifikasi Kerawanan Karhutla Kalimantan."""
import streamlit as st

from domain.sumber_data_service import SumberDataService
from modul import beranda

st.set_page_config(page_title="SiKarhutla", page_icon="🔥", layout="wide")

MODUL = [
    "Beranda",
    "Peta kerawanan",
    "Wilayah dan periode",
    "Klasifikasi",
    "Hasil dan confidence",
    "Rincian variabel",
    "Periode mendatang",
    "Performa model",
    "Bantuan",
]

CSS = """
<style>
[data-testid="stSidebar"] { min-width: 300px; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.15rem; }
[data-testid="stSidebar"] button {
    justify-content: flex-start; border: none; border-radius: 0;
    border-left: 4px solid transparent; padding: 0.7rem 1rem;
    background: transparent; color: #b5aea6; font-size: 1.05rem;
}
[data-testid="stSidebar"] button:hover { background: #262423; color: #ffffff; }
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: #262423; color: #ffffff; font-weight: 700;
    border-left-color: #b8243a;
}
[data-testid="stSidebar"] button > div { justify-content: flex-start; width: 100%; }
[data-testid="stSidebar"] button p { font-size: 1.05rem; text-align: left; }
.sk-logo { display: flex; gap: 0.8rem; align-items: center; margin-bottom: 1.5rem; }
.sk-logo-ikon {
    width: 46px; height: 46px; border-radius: 10px; background: #b8243a;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.sk-logo-ikon div { width: 9px; height: 22px; border-radius: 5px; background: #fff; }
.sk-logo-nama { color: #fff; font-size: 1.45rem; font-weight: 700; line-height: 1.1; }
.sk-logo-sub { color: #9a938b; font-size: 0.85rem; line-height: 1.3; }
.sk-model {
    border-top: 1px solid #34312e; margin-top: 3rem; padding: 1.2rem 0.5rem 0;
}
.sk-model-label { color: #8a837b; font-size: 0.8rem; }
.sk-model-nama { color: #fff; font-weight: 700; font-size: 1.05rem; line-height: 1.4; }
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
  <div class="sk-model-nama">Random Forest<br>XGBoost</div>
</div>
"""


def sidebar() -> str:
    st.session_state.setdefault("menu", MODUL[0])
    with st.sidebar:
        st.markdown(LOGO, unsafe_allow_html=True)
        for nama in MODUL:
            aktif = st.session_state.menu == nama
            if st.button(nama, key=f"menu_{nama}", width="stretch",
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
else:
    st.title(pilihan)
    st.info("Modul ini belum dibangun.")
