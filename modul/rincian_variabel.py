"""Modul 6 - Rincian kesebelas variabel prediktor pada grid terpilih."""
import pandas as pd
import streamlit as st

from domain.grid import Grid
from domain.sumber_data_service import SumberDataService
from modul.tampilan import BULAN, angka

# Urutan sama dengan FEATURE_COLS: (nomor, kolom, nama, satuan, desimal)
DINAMIS = [
    (3, "curah_hujan_mm", "Curah hujan", "mm", 1),
    (4, "suhu_maks_c", "Suhu maks.", "°C", 1),
    (5, "kelembapan_persen", "Kelembapan", "%", 1),
    (6, "angin_maks_kmh", "Angin maks.", "km/jam", 1),
    (7, "hari_kering_maks", "Hari kering", "hari", 0),
]


def _jarak(meter: float) -> tuple[str, str]:
    return (angka(meter / 1000, 1), "km") if meter >= 1000 else (angka(meter), "m")


def _ubin(nomor: int, nama: str, nilai: str, satuan: str = "", banding: str = "",
          teks: bool = False) -> str:
    satuan = f"<small>{satuan}</small>" if satuan else ""
    kelas = "rv-nilai rv-teks" if teks else "rv-nilai"
    banding = f'<div class="rv-banding">{banding}</div>' if banding else ""
    return (f'<div class="rv-ubin"><div class="rv-nama"><span class="rv-nomor">{nomor:02d}'
            f'</span>{nama}</div><div class="{kelas}">{nilai}{satuan}</div>{banding}</div>')


def _banding(nilai: float, rata: float, satuan: str, desimal: int) -> str:
    """Selisih terhadap rata-rata bulan yang sama di dataset."""
    if pd.isna(rata):
        return ""
    selisih = nilai - rata
    arah = "" if abs(selisih) < 10 ** -desimal / 2 else ("↑ " if selisih > 0 else "↓ ")
    return f"{arah}rata-rata <b>{angka(rata, desimal)}</b>"


def render(sumber: SumberDataService, grid: Grid) -> None:
    k = grid.kondisi[0]
    bulan = int(k.tahun_bulan[5:])
    rata = sumber.rata_rata_bulan(grid.grid_id, bulan)

    dinamis = "".join(
        _ubin(no, nama, angka(getattr(k, kol), des), sat,
              _banding(getattr(k, kol), rata[kol], sat, des))
        for no, kol, nama, sat, des in DINAMIS
    )
    air, s_air = _jarak(grid.jarak_air_meter)
    jalan, s_jalan = _jarak(grid.jarak_jalan_meter)
    statis = "".join([
        _ubin(1, "Ketinggian", angka(grid.ketinggian_meter), "m dpl"),
        _ubin(2, "Kemiringan", angka(grid.kemiringan_lereng, 2), "°"),
        _ubin(8, "Jarak air", air, s_air),
        _ubin(9, "Jarak jalan", jalan, s_jalan),
        _ubin(10, "Tutupan lahan", grid.tutupan_lahan.replace("/", "/<wbr>"), teks=True),
        _ubin(11, "Gambut", grid.gambut, teks=True),
    ])
    asal = ("kondisi tercatat di basis data" if k.komposisi is None
            else "disusun dari data cuaca harian Open-Meteo")
    st.markdown(
        '<div class="kl-h2">Rincian variabel prediktor</div>'
        f'<div class="kl-kecil">Sebelas nilai yang menjadi masukan kedua model. Cuaca '
        f'{asal}; pembanding = rata-rata {BULAN[bulan - 1]} '
        f'{rata["tahun_awal"]}–{rata["tahun_akhir"]} di grid ini.</div>'
        f'<div class="rv-grup">Cuaca bulanan · berubah tiap bulan</div>'
        f'<div class="rv-kisi">{dinamis}</div>'
        f'<div class="rv-grup">Karakteristik grid · tetap</div>'
        f'<div class="rv-kisi">{statis}</div>',
        unsafe_allow_html=True,
    )
