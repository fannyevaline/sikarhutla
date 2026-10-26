"""Modul 9 - Bantuan."""
import streamlit as st

from domain.sumber_data_service import SumberDataService
from modul.tampilan import SUMBER_DATA, WARNA

CARA_PAKAI = [
    ("Beranda", "Ringkasan kondisi periode tercatat terakhir: jumlah grid tiap kategori, "
                "sebaran per provinsi, dan tren kerawanan bulanan."),
    ("Klasifikasi", "Pilih grid lewat klik peta, daftar wilayah, atau koordinat, lalu pilih "
                    "bulan dan tahun. Tekan <b>Jalankan klasifikasi</b> untuk melihat hasil "
                    "Random Forest dan XGBoost berdampingan beserta rincian sebelas variabel. "
                    "Bila bulannya belum tercatat, komposisi sumber data cuaca ikut ditampilkan."),
    ("Simulasi", "Isi sendiri kesebelas variabel prediktor, lalu lihat kategori dan "
                 "confidence dari kedua model."),
    ("Performa Model", "Perbandingan F1, AUC, dan confusion matrix kedua model pada "
                       "pengujian internal dan eksternal."),
]

KETERBATASAN = [
    "Keandalan kelas Sedang lebih rendah dibanding Rendah dan Tinggi, karena batas "
    "antar kelas berdekatan.",
    "Periode di luar basis data memakai gabungan data observasi, ramalan cuaca "
    "(paling jauh 16 hari), dan rata-rata klimatologis, yaitu rata-rata historis "
    "tanggal yang sama tahun 2021–2026.",
    "Hasil klasifikasi bersifat indikatif untuk perencanaan, bukan pengganti "
    "pemantauan lapangan.",
]


def _html_kategori(p33: int, p67: int) -> str:
    batas = {
        "Rendah": (f"≤ {p33}", f"Sampai {p33} titik panas per grid dalam sebulan."),
        "Sedang": (f"{p33 + 1}–{p67}", f"{p33 + 1} sampai {p67} titik panas per grid dalam sebulan."),
        "Tinggi": (f"> {p67}", f"Lebih dari {p67} titik panas per grid dalam sebulan."),
    }
    isi = "".join(
        f'<div class="bt-kartu bt-kategori">'
        f'<div class="bt-lencana" style="background:{WARNA[k]}">{angka}</div>'
        f'<div><div class="bt-nama">{k}</div><div class="kl-kecil">{teks}</div></div></div>'
        for k, (angka, teks) in batas.items()
    )
    return (
        '<div class="bt-h2">Tiga kategori kerawanan</div>'
        f'{isi}'
        '<div class="kl-kecil bt-catatan">Ambang diambil dari tertile P33 dan P67 jumlah '
        'titik panas per grid-bulan, data Januari 2021 – Juni 2026.</div>'
    )


def _html_cara_pakai() -> str:
    isi = "".join(
        f'<div class="bt-kartu"><div class="bt-istilah">{judul}</div>'
        f'<div class="kl-kecil">{teks}</div></div>'
        for judul, teks in CARA_PAKAI
    )
    return f'<div class="bt-h2">Cara memakai tiap halaman</div>{isi}'


def _html_keterbatasan() -> str:
    isi = "".join(f"<li>{teks}</li>" for teks in KETERBATASAN)
    return f'<div class="bt-h2">Keterbatasan</div><ul class="bt-daftar">{isi}</ul>'


def _html_sumber() -> str:
    baris = "".join(
        f'<div class="bt-baris"><span class="kl-kecil">{nama}</span>'
        f'<span class="bt-sumber"><b>{sumber}</b><small>{rincian}</small></span></div>'
        for nama, sumber, rincian, _ in SUMBER_DATA
    )
    return f'<div class="bt-h2">Sumber data</div>{baris}'


def render(sumber: SumberDataService) -> None:
    cut = sumber.muat_cutoff()
    st.markdown(
        '<div class="kl-label">Bantuan</div>'
        '<div class="kl-judul">Panduan pemakaian</div>'
        '<div class="kl-sub">Arti kategori, cara memakai tiap halaman, sumber data, dan '
        'keterbatasan sistem.</div>',
        unsafe_allow_html=True,
    )
    kiri, kanan = st.columns([1.25, 1], gap="large")
    with kiri:
        st.markdown(_html_kategori(int(cut["p33"]), int(cut["p67"])), unsafe_allow_html=True)
        st.markdown(_html_cara_pakai(), unsafe_allow_html=True)
    with kanan:
        st.markdown(_html_keterbatasan(), unsafe_allow_html=True)
        with st.container(key="bento_bantuan_sumber"):
            st.markdown(_html_sumber(), unsafe_allow_html=True)
