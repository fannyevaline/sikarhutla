"""Modul 9 - Bantuan."""
import streamlit as st

from domain.konstanta import SKENARIO_FINAL, UKURAN_GRID
from domain.sumber_data_service import SumberDataService
from modul.tampilan import SUMBER_DATA, WARNA, WARNA_LATAR, WARNA_TEKS, angka

CARA_PAKAI = [
    ("Beranda", "Ringkasan bulan terakhir yang tercatat: jumlah grid tiap kategori, "
                "sebaran per provinsi, dan tren kerawanan bulanan."),
    ("Klasifikasi", "Pilih grid lewat peta, daftar wilayah, atau koordinat, lalu pilih bulan "
                    "dan tahun. Tekan <b>Jalankan klasifikasi</b> untuk melihat hasil kedua "
                    "model berdampingan beserta nilai kesebelas variabelnya."),
    ("Simulasi", "Isi sendiri kesebelas variabel prediktor untuk mencoba kondisi tertentu, "
                 "lalu bandingkan kategori dan confidence kedua model."),
    ("Performa Model", "Lihat akurasi, F1, AUC, confusion matrix, dan kesalahan Tinggi → "
                       "Rendah kedua model pada pengujian internal dan eksternal."),
]


def _istilah(n_grid: int) -> list[tuple[str, str]]:
    ukuran = angka(UKURAN_GRID, 1)
    return [
        ("Grid", f"Kotak berukuran {ukuran}° × {ukuran}°. Kalimantan dibagi menjadi "
                 f"{n_grid} grid, dan klasifikasi dilakukan per grid."),
        ("Grid-bulan", "Satu grid pada satu bulan, yaitu satuan data yang diklasifikasikan."),
        ("Titik panas", "Lokasi bersuhu tinggi yang dideteksi satelit MODIS dan VIIRS, "
                        "dipakai sebagai penanda kebakaran."),
        ("Confidence", "Probabilitas tertinggi yang diberikan model untuk kelas hasil "
                       "prediksinya. Makin tinggi berarti model makin yakin, tetapi bukan "
                       "jaminan hasilnya benar."),
        ("SMOTENC", "Teknik menambah data sintetis untuk kelas yang datanya sedikit, khusus "
                    "data campuran numerik dan kategorikal, supaya model tidak berat sebelah "
                    "ke kelas mayoritas."),
    ]


def _keterbatasan(p33: int, p67: int, f1_sedang: float) -> list[tuple[str, str]]:
    return [
        ("Kelas Sedang paling sulit dikenali",
         f"Rentangnya sempit ({p33 + 1}–{p67} titik panas), sehingga mudah tertukar dengan "
         f"Rendah atau Tinggi. F1 kelas ini pada model final hanya {angka(f1_sedang, 3)}."),
        ("Bulan yang belum selesai",
         "Data cuacanya disusun dari observasi, ramalan (paling jauh 16 hari ke depan), dan "
         "rata-rata klimatologis 2021–2026 pada tanggal yang sama. Makin banyak hari "
         "klimatologis, makin lemah dasar hasilnya."),
        ("Variabel statis tidak diperbarui",
         "Tutupan lahan memakai peta tahun 2021, sehingga perubahan lahan setelahnya tidak "
         "tercermin dalam hasil."),
        ("Bersifat indikatif",
         "Hasil klasifikasi ditujukan untuk perencanaan dan kewaspadaan, bukan pengganti "
         "pemantauan lapangan."),
    ]


def _html_kategori(p33: int, p67: int) -> str:
    batas = {
        "Rendah": (f"≤ {p33}", f"Paling banyak {p33} titik panas per grid dalam sebulan."),
        "Sedang": (f"{p33 + 1}–{p67}", f"{p33 + 1} sampai {p67} titik panas per grid "
                                      "dalam sebulan."),
        "Tinggi": (f"≥ {p67 + 1}", f"{p67 + 1} titik panas atau lebih per grid dalam "
                                   "sebulan."),
    }
    isi = "".join(
        f'<div class="bt-kategori" style="background:{WARNA_LATAR[k]}">'
        f'<div class="bt-lencana" style="background:{WARNA[k]}">{rentang}</div>'
        f'<div><div class="bt-nama" style="color:{WARNA_TEKS[k]}">{k}</div>'
        f'<div class="bt-teks">{teks}</div></div></div>'
        for k, (rentang, teks) in batas.items()
    )
    return (
        '<div class="bt-h2">Tiga kategori kerawanan</div>'
        f'<div class="bt-kisi3">{isi}</div>'
        f'<div class="kl-kecil bt-catatan">Ambang ditetapkan dari persentil ke-33 (P33 = '
        f'{p33}) dan ke-67 (P67 = {p67}) jumlah titik panas per grid-bulan, data Januari '
        '2021 – Juni 2026.</div>'
    )


def _html_cara_pakai() -> str:
    isi = "".join(
        f'<div class="bt-langkah"><div class="bt-nomor">{i}</div><div>'
        f'<div class="bt-istilah">{judul}</div><div class="bt-teks">{teks}</div></div></div>'
        for i, (judul, teks) in enumerate(CARA_PAKAI, 1)
    )
    return f'<div class="bt-h2">Cara memakai tiap halaman</div><div class="bt-kisi2">{isi}</div>'


def _html_istilah(n_grid: int) -> str:
    isi = "".join(f'<div class="bt-def"><b>{judul}</b><span>{teks}</span></div>'
                  for judul, teks in _istilah(n_grid))
    return f'<div class="bt-h2">Istilah penting</div>{isi}'


def _html_sumber() -> str:
    baris = "".join(
        f'<div class="bt-baris"><div class="bt-baris-kiri"><i style="background:{warna}"></i>'
        f'<span>{nama}</span></div>'
        f'<span class="bt-sumber"><b>{sumber}</b><small>{rincian}</small></span></div>'
        for nama, sumber, rincian, warna in SUMBER_DATA
    )
    return f'<div class="bt-h2">Sumber data</div>{baris}'


def _html_keterbatasan(butir: list[tuple[str, str]]) -> str:
    isi = "".join(f'<div class="bt-batas"><b>{judul}</b><div class="bt-teks">{teks}</div></div>'
                  for judul, teks in butir)
    return f'<div class="bt-h2">Keterbatasan</div><div class="bt-kisi2">{isi}</div>'


def render(sumber: SumberDataService) -> None:
    cut = sumber.muat_cutoff()
    p33, p67 = int(cut["p33"]), int(cut["p67"])
    f1_sedang = sumber.metrik_per_kelas(SKENARIO_FINAL, sumber.model_terbaik()).loc["Sedang", "F1"]
    st.markdown(
        '<div class="kl-label">Bantuan</div>'
        '<div class="kl-judul">Panduan pemakaian</div>'
        '<div class="kl-sub">Arti kategori, cara memakai tiap halaman, istilah penting, '
        'sumber data, dan keterbatasan sistem.</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="bento_bt_kategori"):
        st.markdown(_html_kategori(p33, p67), unsafe_allow_html=True)
    with st.container(key="bento_bt_cara"):
        st.markdown(_html_cara_pakai(), unsafe_allow_html=True)
    kiri, kanan = st.columns([1.15, 1], gap="medium")
    with kiri, st.container(key="bento_bt_istilah", height="stretch"):
        st.markdown(_html_istilah(int(cut["n_grid"])), unsafe_allow_html=True)
    with kanan, st.container(key="bento_bt_sumber", height="stretch"):
        st.markdown(_html_sumber(), unsafe_allow_html=True)
    with st.container(key="bento_bt_batas"):
        st.markdown(_html_keterbatasan(_keterbatasan(p33, p67, f1_sedang)),
                    unsafe_allow_html=True)
