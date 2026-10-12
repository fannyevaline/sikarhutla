"""Modul 1 - Beranda."""
import pandas as pd
import streamlit as st

from domain.sumber_data_service import KELAS, SumberDataService

WARNA = {"Rendah": "#2e7d32", "Sedang": "#f9a825", "Tinggi": "#c62828"}
NAMA_WARNA = {"Rendah": "hijau", "Sedang": "kuning", "Tinggi": "merah"}

SUMBER_DATA = [
    ("Titik panas (hotspot)",
     "NASA FIRMS (MODIS Terra & Aqua, VIIRS Suomi-NPP), layanan Fire Archive Download"),
    ("Batas administratif", "GADM versi 4.1"),
    ("Ketinggian", "Open-Meteo Elevation API (Copernicus DEM GLO-90)"),
    ("Kemiringan lereng", "Diturunkan dari data ketinggian"),
    ("Curah hujan, suhu maksimum, kelembapan, angin maksimum",
     "Open-Meteo Archive API (reanalisis ECMWF ERA5)"),
    ("Hari kering berturut-turut",
     "Diturunkan dari curah hujan harian, definisi CDD ETCCDI (< 1 mm)"),
    ("Tutupan lahan", "ESA WorldCover 10 m 2021 v200"),
    ("Status gambut", "Peta Lahan Gambut Badan Informasi Geospasial (BIG)"),
    ("Jarak ke badan air dan jarak ke jalan", "OpenStreetMap melalui Geofabrik"),
    ("Ramalan cuaca periode mendatang", "Open-Meteo Forecast API, hingga 16 hari"),
]

LANGKAH = [
    "Buka **Pemilihan Wilayah dan Periode**, pilih grid lewat peta atau dropdown nama "
    "wilayah, lalu pilih bulan dan tahun (historis atau mendatang).",
    "Jalankan **Klasifikasi Kerawanan** untuk memproses pilihan dengan model "
    "Random Forest dan XGBoost.",
    "Lihat **Hasil Klasifikasi dan Confidence** untuk membandingkan kategori dan "
    "confidence kedua model secara berdampingan.",
    "Periksa **Rincian Variabel Prediktor** untuk melihat nilai kesebelas variabel "
    "pada grid terpilih.",
    "Untuk bulan yang belum selesai, cek **Informasi Periode Mendatang** untuk melihat "
    "komposisi sumber data cuacanya.",
    "Buka **Perbandingan Performa Model** untuk melihat metrik evaluasi kedua model.",
]


def _nama_bulan(tahun_bulan: str) -> str:
    return pd.Period(tahun_bulan, freq="M").strftime("%B %Y")


def _kartu(kelas: str, jumlah: int, total: int) -> str:
    persen = jumlah / total * 100 if total else 0
    return (
        f'<div style="border-left:6px solid {WARNA[kelas]};padding:0.6rem 1rem;'
        f'border-radius:6px;background:rgba(128,128,128,0.08)">'
        f'<div style="font-size:0.95rem;opacity:0.8">{kelas}</div>'
        f'<div style="font-size:2rem;font-weight:700;color:{WARNA[kelas]}">{jumlah}</div>'
        f'<div style="font-size:0.85rem;opacity:0.7">{persen:.1f}% dari {total} grid</div>'
        f'</div>'
    )


def render(sumber: SumberDataService) -> None:
    st.title("Dashboard Klasifikasi Kerawanan Karhutla Kalimantan")
    st.caption(
        "Perbandingan Random Forest dan XGBoost untuk klasifikasi tingkat kerawanan "
        "kebakaran hutan dan lahan di Kalimantan berbasis data titik panas satelit."
    )

    # Ringkasan bulan terakhir
    periode = sumber.periode_terakhir()
    ringkasan = sumber.ringkasan_kategori(periode)
    total = int(ringkasan.sum())

    st.subheader(f"Ringkasan kerawanan — {_nama_bulan(periode)}")
    st.write(f"Jumlah grid per kategori pada periode terakhir di basis data ({periode}).")
    for kolom, kelas in zip(st.columns(3), KELAS):
        kolom.markdown(_kartu(kelas, int(ringkasan[kelas]), total), unsafe_allow_html=True)

    # Penjelasan kategori
    cut = sumber.muat_cutoff()
    p33, p67 = int(cut["p33"]), int(cut["p67"])
    st.subheader("Kategori kerawanan")
    st.write(
        "Kategori ditentukan dari jumlah titik panas per grid dalam satu bulan, "
        f"dengan ambang tertile P33 = {p33} dan P67 = {p67}."
    )
    st.table(pd.DataFrame({
        "Kategori": KELAS,
        "Jumlah hotspot per grid-bulan": [f"x ≤ {p33}", f"{p33 + 1} ≤ x ≤ {p67}",
                                          f"x ≥ {p67 + 1}"],
        "Arti": [
            "Aktivitas titik panas sedikit atau tidak ada.",
            "Aktivitas titik panas mulai menonjol; perlu diwaspadai.",
            "Aktivitas titik panas tinggi; prioritas pemantauan.",
        ],
        "Warna di peta": [NAMA_WARNA[k] for k in KELAS],
    }).set_index("Kategori"))

    # Langkah penggunaan
    st.subheader("Langkah penggunaan")
    st.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(LANGKAH, 1)))

    # Sumber data
    st.subheader("Sumber data")
    st.table(pd.DataFrame(SUMBER_DATA, columns=["Data", "Sumber"]).set_index("Data"))
