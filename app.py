"""Titik masuk Streamlit - Dashboard Klasifikasi Kerawanan Karhutla Kalimantan.

Jalankan dengan:  streamlit run app.py

Tugas berkas ini hanya tiga: memasang CSS, menggambar sidebar, dan memanggil
halaman yang dipilih. Isi tiap halaman ada di modul/, logikanya di domain/.
"""
import streamlit as st

from domain.sumber_data_service import SumberDataService
from modul import bantuan, beranda, klasifikasi, performa_model, simulasi
from modul.tampilan import muat_css

st.set_page_config(page_title="SiKarhutla", page_icon="🔥", layout="wide", initial_sidebar_state="auto")

# Semua berkas di assets/css/, urut dari yang paling umum. Dipasang sekali di sini
# supaya tiap halaman tidak perlu memuat CSS-nya sendiri.
CSS = ["global", "komponen", "beranda", "klasifikasi", "rincian_variabel",
       "periode_mendatang", "simulasi", "performa_model", "bantuan"]

# Lima menu sidebar: nama -> (ikon Material, fungsi render; None = belum dibangun)
HALAMAN = {
    "Beranda": (":material/home:", beranda.render),
    "Klasifikasi": (":material/travel_explore:", klasifikasi.render),
    "Simulasi": (":material/tune:", simulasi.render),
    "Performa Model": (":material/insights:", performa_model.render),
    "Bantuan": (":material/help:", bantuan.render),
}

LOGO = """
<div class="sk-logo">
  <div class="sk-logo-ikon"><svg viewBox="0 0 24 24"><path d="M19.48 12.35c-1.57-4.08-7.16-4.3-5.81-10.23.1-.44-.37-.78-.75-.55C9.29 3.71 6.68 8 8.87 13.62c.18.46-.36.89-.75.59-1.81-1.37-2-3.34-1.84-4.75.06-.52-.62-.77-.91-.34C4.69 10.16 4 11.84 4 14.37c.38 5.6 5.11 7.32 6.81 7.54 2.43.31 5.06-.14 6.95-1.87 2.08-1.93 2.84-5.01 1.72-7.69zM10.2 17.38c1.44-.35 2.18-1.39 2.38-2.31.33-1.43-.96-2.83-.09-5.09.33 1.87 3.27 3.04 3.27 5.08.08 2.53-2.66 4.7-5.56 2.32z"/></svg></div>
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
    """Gambar menu dan kembalikan nama halaman yang aktif."""
    if st.session_state.get("menu") not in HALAMAN:
        st.session_state.menu = "Beranda"
    with st.sidebar:
        st.markdown(LOGO, unsafe_allow_html=True)
        for nama, (ikon, _) in HALAMAN.items():
            aktif = st.session_state.menu == nama
            if st.button(nama, key=f"menu_{nama}", icon=ikon, width="stretch",
                         type="primary" if aktif else "secondary"):
                st.session_state.menu = nama
                st.rerun()
        st.markdown(MODEL_AKTIF, unsafe_allow_html=True)
    return st.session_state.menu


muat_css(*CSS)
pilihan = sidebar()
_, render = HALAMAN[pilihan]
if render is None:
    st.title(pilihan)
    st.info("Modul ini belum dibangun.")
else:
    render(SumberDataService())
