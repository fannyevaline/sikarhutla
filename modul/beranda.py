"""Modul 1 - Beranda."""
import streamlit as st

from domain.sumber_data_service import SumberDataService

WARNA = {"Rendah": "#2e7d4f", "Sedang": "#c28e0e", "Tinggi": "#c0392b"}

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

LANGKAH = [
    ("Pilih grid wilayah", "Lewat peta atau daftar grid"),
    ("Pilih periode", "Bulan lampau atau sampai 16 hari ke depan"),
    ("Jalankan klasifikasi", "Kedua model dijalankan sekaligus"),
    ("Baca hasilnya", "Kategori, confidence, dan nilai variabel"),
]

SUMBER_DATA = [
    ("Titik panas", "NASA FIRMS"),
    ("Cuaca", "Open-Meteo"),
    ("Tutupan lahan", "ESA WorldCover"),
    ("Lahan gambut", "BIG"),
    ("Jalan dan air", "OpenStreetMap"),
    ("Batas wilayah", "GADM v4.1"),
]

CSS = """
<style>
.bd-judul { font-size: 2.6rem; font-weight: 800; color: #1a1a1a; margin: 0; line-height: 1.15; }
.bd-sub { color: #77706a; font-size: 1.1rem; margin: 0.4rem 0 1.2rem; }
.bd-garis { border: none; border-top: 1px solid #ddd8d2; margin: 0 0 1.6rem; }
.bd-kartu {
    background: #fff; border: 1px solid #e6e1db; border-radius: 12px;
    padding: 1.6rem 1.8rem;
}
.bd-ringkas { display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 1.2rem; margin-bottom: 2rem; }
.bd-ringkas-judul { font-size: 1.35rem; font-weight: 700; color: #1a1a1a; }
.bd-kecil { color: #77706a; font-size: 0.95rem; }
.bd-angka-grup { display: flex; gap: 2.5rem; flex-wrap: wrap; }
.bd-angka { text-align: center; min-width: 7rem; }
.bd-angka-nilai { font-size: 2.8rem; font-weight: 800; line-height: 1.1; }
.bd-h2 { font-size: 1.45rem; font-weight: 700; color: #1a1a1a; margin: 0; }
.bd-kategori-grup { display: flex; gap: 1.2rem; flex-wrap: wrap; margin: 1rem 0 2rem; }
.bd-kategori {
    flex: 1 1 14rem; background: #fff; border: 1px solid #e6e1db;
    border-left-width: 6px; border-radius: 12px; padding: 1.1rem 1.4rem;
}
.bd-kategori-nama { font-size: 1.25rem; font-weight: 700; color: #1a1a1a; }
.bd-langkah { display: flex; gap: 1rem; margin-top: 1.1rem; }
.bd-nomor {
    width: 2.1rem; height: 2.1rem; border-radius: 50%; background: #b8243a; color: #fff;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; flex-shrink: 0;
}
.bd-langkah-judul { font-weight: 700; font-size: 1.1rem; color: #1a1a1a; }
.bd-baris { display: flex; justify-content: space-between; gap: 1rem;
    padding: 0.75rem 0; border-bottom: 1px solid #ece8e3; }
.bd-baris:last-child { border-bottom: none; }
.bd-baris b { color: #1a1a1a; text-align: right; }
</style>
"""


def _nama_periode(tahun_bulan: str) -> str:
    tahun, bulan = tahun_bulan.split("-")
    return f"{BULAN[int(bulan) - 1]} {tahun}"


def _html_ringkasan(periode: str, ringkasan, total: int) -> str:
    angka = "".join(
        f'<div class="bd-angka">'
        f'<div class="bd-angka-nilai" style="color:{WARNA[k]}">{int(ringkasan[k])}</div>'
        f'<div class="bd-kecil">Grid berkategori {k.lower()}</div></div>'
        for k in ["Tinggi", "Sedang", "Rendah"]
    )
    return (
        f'<div class="bd-kartu bd-ringkas">'
        f'<div><div class="bd-ringkas-judul">Kondisi {_nama_periode(periode)}</div>'
        f'<div class="bd-kecil">Ringkasan hasil klasifikasi terakhir untuk {total} grid</div></div>'
        f'<div class="bd-angka-grup">{angka}</div></div>'
    )


def _html_kategori(p33: int, p67: int) -> str:
    batas = {
        "Rendah": f"sampai {p33} titik panas",
        "Sedang": f"{p33 + 1} sampai {p67} titik panas",
        "Tinggi": f"lebih dari {p67} titik panas",
    }
    kartu = "".join(
        f'<div class="bd-kategori" style="border-left-color:{WARNA[k]}">'
        f'<div class="bd-kategori-nama">{k}</div><div class="bd-kecil">{t}</div></div>'
        for k, t in batas.items()
    )
    return (
        '<div class="bd-h2">Tiga kategori kerawanan</div>'
        '<div class="bd-kecil">Ditentukan dari jumlah titik panas per grid tiap bulan</div>'
        f'<div class="bd-kategori-grup">{kartu}</div>'
    )


def _html_langkah() -> str:
    isi = "".join(
        f'<div class="bd-langkah"><div class="bd-nomor">{i}</div>'
        f'<div><div class="bd-langkah-judul">{judul}</div>'
        f'<div class="bd-kecil">{ket}</div></div></div>'
        for i, (judul, ket) in enumerate(LANGKAH, 1)
    )
    return f'<div class="bd-h2">Cara menggunakan</div>{isi}'


def _html_sumber() -> str:
    baris = "".join(
        f'<div class="bd-baris"><span class="bd-kecil">{nama}</span><b>{sumber}</b></div>'
        for nama, sumber in SUMBER_DATA
    )
    return (f'<div class="bd-kartu"><div class="bd-h2" style="margin-bottom:0.4rem">'
            f'Sumber data</div>{baris}</div>')


def render(sumber: SumberDataService) -> None:
    periode = sumber.periode_terakhir()
    ringkasan = sumber.ringkasan_kategori(periode)
    total = int(ringkasan.sum())
    cut = sumber.muat_cutoff()

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="bd-judul">Kerawanan karhutla Kalimantan</div>'
        '<div class="bd-sub">Klasifikasi tingkat kerawanan per grid dengan '
        'Random Forest dan XGBoost</div><hr class="bd-garis">'
        + _html_ringkasan(periode, ringkasan, total)
        + _html_kategori(int(cut["p33"]), int(cut["p67"])),
        unsafe_allow_html=True,
    )

    kiri, kanan = st.columns(2, gap="large")
    kiri.markdown(_html_langkah(), unsafe_allow_html=True)
    kanan.markdown(_html_sumber(), unsafe_allow_html=True)
