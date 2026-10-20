"""Modul 7 - Informasi periode mendatang: komposisi sumber data cuaca untuk bulan
yang tidak diambil dari basis data historis."""
import streamlit as st

from domain.grid import KomposisiCuaca
from modul.beranda import BULAN, _nama_periode

CSS = """
<style>
.pm-batang { display: flex; height: 2.6rem; border-radius: 10px; overflow: hidden;
    margin-top: 0.9rem; gap: 2px; }
.pm-batang div { display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 700; font-size: 0.9rem; white-space: nowrap; min-width: 0;
    overflow: hidden; }
.pm-skala { display: flex; justify-content: space-between; font-size: 0.78rem;
    color: #8a827a; margin-top: 0.3rem; }
.pm-baris { display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    flex-wrap: wrap; padding: 0.8rem 1rem; margin-top: 0.6rem; border-radius: 12px;
    border: 1px solid #efe8e0; border-left: 5px solid; background: #fcfaf8; }
.pm-judul { font-weight: 700; color: #1f1b18; font-size: 0.98rem; }
.pm-rentang { font-weight: 700; font-size: 0.92rem; text-align: right; }
.pm-catatan { margin-top: 0.8rem; padding: 0.7rem 1rem; border-radius: 12px;
    background: #fff4ea; border: 1px solid #ffd8bd; font-size: 0.88rem; color: #4f4842; }
</style>
"""

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
        CSS +
        f'<div class="kl-h2">{judul.format(p=_nama_periode(tahun_bulan))}</div>'
        f'<div class="kl-kecil">{sub}</div>'
        f'<div class="pm-batang">{batang}</div>'
        f'<div class="pm-skala"><span>1 {bulan}</span><span>Komposisi {n} hari</span>'
        f'<span>{n} {bulan}</span></div>'
        f'{baris}{catatan}',
        unsafe_allow_html=True,
    )
