"""Modul 7 - Informasi periode mendatang: komposisi sumber data cuaca untuk bulan
yang tidak diambil dari basis data historis."""
import streamlit as st

from domain.grid import KomposisiCuaca
from modul.tampilan import BULAN, nama_periode

SUMBER = [
    ("hari_observasi", "Data aktual", "Open-Meteo Archive, nilai yang benar-benar terjadi",
     "#1f9d55", "#137a3f"),
    ("hari_ramalan", "Ramalan cuaca", "Open-Meteo Forecast, jangkauan maksimal 16 hari",
     "#e0a000", "#9a6700"),
    ("hari_klimatologi", "Rata-rata historis",
     "Rata-rata tanggal yang sama 2021–2026, dipakai bila ramalan belum mencapai akhir bulan",
     "#8a827a", "#6f6760"),
]

JUDUL = {
    "selesai": ("{p} sudah selesai, tetapi belum ada di basis data",
                "Nilai cuaca diambil dari data harian Open-Meteo lalu diagregasi seperti data "
                "pelatihan."),
    "berjalan": ("{p} belum selesai",
                 "Nilai cuaca satu bulan penuh disusun dari tiga sumber agar sebanding dengan "
                 "data pelatihan."),
    "mendatang": ("{p} belum dimulai",
                  "Nilai cuaca satu bulan penuh disusun dari ramalan dan rata-rata historis "
                  "agar sebanding dengan data pelatihan."),
}


def _rentang(awal: int, n: int, bulan: str) -> str:
    if n == 0:
        return "Tidak terpakai"
    if n == 1:
        return f"{awal} {bulan}"
    return f"{awal} – {awal + n - 1} {bulan}"


def render(komposisi: KomposisiCuaca, tahun_bulan: str, status: str) -> None:
    bulan = BULAN[int(tahun_bulan[5:]) - 1]
    n = komposisi.n_hari
    judul, sub = JUDUL[status]

    batang, baris, hari_ke = "", "", 1
    for atribut, nama, ket, warna, warna_teks in SUMBER:
        jumlah = getattr(komposisi, atribut)
        if jumlah:
            label = f"{jumlah} hari" if jumlah / n >= 0.12 else str(jumlah)
            batang += (f'<div style="flex:{jumlah};background:{warna}" '
                       f'title="{nama}: {jumlah} hari">{label}</div>')
        warna_rentang = warna_teks if jumlah else "#b0a79e"
        baris += (f'<div class="pm-baris" style="border-left-color:{warna}">'
                  f'<div><div class="pm-judul">{nama} · {jumlah} hari</div>'
                  f'<div class="kl-kecil">{ket}</div></div>'
                  f'<div class="pm-rentang" style="color:{warna_rentang}">'
                  f'{_rentang(hari_ke, jumlah, bulan)}</div></div>')
        hari_ke += jumlah

    catatan = ""
    if komposisi.hari_klimatologi:
        catatan = ('<div class="pm-catatan"><b>Bagian rata-rata historis adalah perkiraan, '
                   'bukan ramalan cuaca.</b> Makin besar porsinya, makin lemah dasar hasil '
                   'klasifikasi untuk bulan ini.</div>')

    st.markdown(
        f'<div class="kl-h2">{judul.format(p=nama_periode(tahun_bulan))}</div>'
        f'<div class="kl-kecil">{sub}</div>'
        f'<div class="pm-batang">{batang}</div>'
        f'<div class="pm-skala"><span>1 {bulan}</span><span>Komposisi {n} hari</span>'
        f'<span>{n} {bulan}</span></div>'
        f'{baris}{catatan}',
        unsafe_allow_html=True,
    )
