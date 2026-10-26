"""Alat bantu tampilan yang dipakai bersama semua halaman: pemuat CSS, warna kelas,
nama bulan, format angka, dan gaya grafik Plotly.

CSS-nya sendiri ada di assets/css/, satu berkas per halaman atau modul.
"""
from pathlib import Path

import streamlit as st

FOLDER_CSS = Path(__file__).resolve().parent.parent / "assets/css"

# Warna tanda (peta, batang), warna teks yang lebih gelap supaya tetap terbaca,
# dan warna latar pucat untuk kartu.
WARNA = {"Rendah": "#1f9d55", "Sedang": "#e0a000", "Tinggi": "#e03131"}
WARNA_TEKS = {"Rendah": "#137a3f", "Sedang": "#9a6700", "Tinggi": "#b42323"}
WARNA_LATAR = {"Rendah": "#dcf3e5", "Sedang": "#fff0c4", "Tinggi": "#ffe1e1"}

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

FONT = "Plus Jakarta Sans, sans-serif"

# Nilai kolom gambut di data -> teks tampilan (Rincian Variabel dan Simulasi)
LABEL_GAMBUT = {"Ya": "Gambut", "Tidak": "Bukan gambut"}

# Sumber data, dipakai Beranda (ringkas) dan Bantuan (lengkap):
# (jenis data, nama sumber, rincian, warna ikon)
SUMBER_DATA = [
    ("Titik panas", "NASA FIRMS", "Satelit MODIS dan VIIRS", "#f76707"),
    ("Cuaca dan topografi", "Open-Meteo", "Archive API dan Forecast API", "#1c7ed6"),
    ("Tutupan lahan", "ESA WorldCover", "Resolusi 10 m, tahun 2021, versi v200", "#2b8a3e"),
    ("Lahan gambut", "BIG", "Badan Informasi Geospasial", "#9c5b2a"),
    ("Jarak ke air dan jalan", "OpenStreetMap", "Diunduh lewat Geofabrik", "#0c8599"),
    ("Batas wilayah", "GADM v4.1", "Nama provinsi dan kabupaten tiap grid", "#7048e8"),
]


@st.cache_data
def _baca_css(nama: str) -> str:
    return (FOLDER_CSS / f"{nama}.css").read_text(encoding="utf-8")


def muat_css(*nama: str) -> None:
    """Pasang berkas assets/css/<nama>.css ke halaman, misalnya muat_css("beranda")."""
    isi = "\n".join(_baca_css(n) for n in nama)
    st.markdown(f"<style>{isi}</style>", unsafe_allow_html=True)


def nama_periode(tahun_bulan: str) -> str:
    """"2026-06" -> "Juni 2026"."""
    tahun, bulan = tahun_bulan.split("-")
    return f"{BULAN[int(bulan) - 1]} {tahun}"


def angka(x: float, desimal: int = 0) -> str:
    """Format angka gaya Indonesia: titik ribuan, koma desimal."""
    return f"{x:,.{desimal}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def gaya_grafik(tinggi: int, margin_atas: int, legenda_y: float) -> dict:
    """Layout Plotly bersama: latar transparan, huruf aplikasi, legenda kanan atas,
    tooltip putih, tanpa geser/zoom."""
    return {
        "height": tinggi,
        "margin": {"l": 0, "r": 0, "t": margin_atas, "b": 0},
        "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": FONT, "color": "#756d66", "size": 12},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": legenda_y, "x": 1,
                   "xanchor": "right", "font": {"color": "#4f4842"}, "traceorder": "normal"},
        "hoverlabel": {"bgcolor": "#ffffff", "bordercolor": "#e6dfd7",
                       "font": {"family": FONT, "color": "#1f1b18", "size": 13}},
        "dragmode": False,
    }
