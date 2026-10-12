"""Titik masuk Streamlit - Dashboard Klasifikasi Kerawanan Karhutla Kalimantan."""
import streamlit as st

from domain.sumber_data_service import SumberDataService
from modul import beranda

st.set_page_config(page_title="Kerawanan Karhutla Kalimantan", page_icon="🔥",
                   layout="wide")

MODUL = [
    "Beranda",
    "Peta Interaktif Kerawanan",
    "Pemilihan Wilayah dan Periode",
    "Klasifikasi Kerawanan",
    "Hasil Klasifikasi dan Confidence",
    "Rincian Variabel Prediktor",
    "Informasi Periode Mendatang",
    "Perbandingan Performa Model",
    "Bantuan",
]

sumber = SumberDataService()

pilihan = st.sidebar.radio("Menu", MODUL)

if pilihan == "Beranda":
    beranda.render(sumber)
else:
    st.title(pilihan)
    st.info("Modul ini belum dibangun.")
