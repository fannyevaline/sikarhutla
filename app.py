"""Titik masuk Streamlit - Dashboard Klasifikasi Kerawanan Karhutla Kalimantan.

Jalankan dengan:  streamlit run app.py

Tugas berkas ini hanya tiga: memasang CSS, menggambar sidebar, dan memanggil
halaman yang dipilih. Isi tiap halaman ada di modul/, logikanya di domain/.
"""
import streamlit as st

from domain.sumber_data_service import SumberDataService
from modul import bantuan, beranda, klasifikasi, performa_model, simulasi
from modul.tampilan import muat_css

st.set_page_config(page_title="SiKarhutla", page_icon="🔥", layout="wide")

# Semua berkas di assets/css/, urut dari yang paling umum. Dipasang sekali di sini
# supaya tiap halaman tidak perlu memuat CSS-nya sendiri.
CSS = ["global", "komponen", "beranda", "klasifikasi", "peta", "rincian_variabel",
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
