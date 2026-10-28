"""Modul 6 - Rincian kesebelas variabel prediktor pada grid terpilih."""
import pandas as pd
import streamlit as st

from domain.grid import Grid
from domain.sumber_data_service import SumberDataService
from modul.tampilan import BULAN, LABEL_GAMBUT, angka

# Ikon garis 24x24 (isi elemen <svg>), satu per variabel
IKON = {
    "hujan": '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2"/>'
             '<path d="M16 14v6M8 14v6M12 16v6"/>',
    "suhu": '<path d="M14 4v10.5a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>',
    "lembap": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5S12.5 5.5 12 3c-.5 2.5-2 4.9-4 6.5'
              'S5 13 5 15a7 7 0 0 0 7 7z"/>',
    "angin": '<path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2M9.6 4.6A2 2 0 1 1 11 8H2'
             'M12.6 19.4A2 2 0 1 0 14 16H2"/>',
    "kering": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
              'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4"/>',
    "tinggi": '<path d="m8 3 4 8 5-5 5 15H2L8 3z"/>',
    "lereng": '<path d="M3 20h18V6L3 20z"/>',
    "air": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 '
           '1.3 0 1.9.5 2.5 1M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 '
           '2.5-2 5-2 1.3 0 1.9.5 2.5 1M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 '
           '2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
    "jalan": '<circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/>'
             '<path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/>',
    "lahan": '<path d="m17 14 3 3.3a1 1 0 0 1-.7 1.7H4.7a1 1 0 0 1-.7-1.7L7 14h-.3a1 1 0 0 1'
             '-.7-1.7L9 9h-.2A1 1 0 0 1 8 7.3L12 3l4 4.3a1 1 0 0 1-.8 1.7H15l3 3.3a1 1 0 0 1'
             '-.7 1.7H17ZM12 22v-3"/>',
    "gambut": '<path d="m12 2 10 5-10 5L2 7zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
}

# Urutan sama dengan FEATURE_COLS: (nomor, kolom, nama, satuan, desimal, ikon, warna)
DINAMIS = [
    (3, "curah_hujan_mm", "Curah hujan", "mm", 1, "hujan", "#1c7ed6"),
    (4, "suhu_maks_c", "Suhu maksimum", "°C", 1, "suhu", "#f76707"),
    (5, "kelembapan_persen", "Kelembapan", "%", 1, "lembap", "#0c8599"),
    (6, "angin_maks_kmh", "Angin maksimum", "km/jam", 1, "angin", "#5c7cfa"),
    (7, "hari_kering_maks", "Hari kering beruntun", "hari", 0, "kering", "#e8590c"),
]


def _jarak(meter: float) -> tuple[str, str]:
    return (angka(meter / 1000, 1), "km") if meter >= 1000 else (angka(meter), "m")


def _ubin(nomor: int, nama: str, nilai: str, satuan: str, ikon: str, warna: str,
          banding: str = "", teks: bool = False) -> str:
    satuan = f"<small>{satuan}</small>" if satuan else ""
    kelas = "rv-nilai rv-teks" if teks else "rv-nilai"
    return (f'<div class="rv-ubin">'
            f'<div class="rv-atas"><span class="rv-ikon" style="background:{warna};'
            f'box-shadow:0 4px 10px {warna}40"><svg viewBox="0 0 24 24">{IKON[ikon]}</svg></span>'
            f'<span class="rv-nomor" style="color:{warna}">{nomor:02d}</span></div>'
            f'<div class="rv-nama">{nama}</div>'
            f'<div class="{kelas}">{nilai}{satuan}</div>{banding}</div>')


def _banding(nilai: float, rata: float, desimal: int) -> str:
    """Teks pembanding dengan rata-rata bulan yang sama di dataset."""
    if pd.isna(rata):
        return ""
    selisih = nilai - rata
    arah = "" if abs(selisih) < 10 ** -desimal / 2 else ("↑ " if selisih > 0 else "↓ ")
    return f'<div class="rv-banding">{arah}rata-rata <b>{angka(rata, desimal)}</b></div>'


def render(sumber: SumberDataService, grid: Grid) -> None:
    k = grid.kondisi[0]
    bulan = int(k.tahun_bulan[5:])
    rata = sumber.rata_rata_bulan(grid.grid_id, bulan)

    dinamis = "".join(
        _ubin(no, nama, angka(getattr(k, kol), des), sat, ikon, warna,
              _banding(getattr(k, kol), rata[kol], des))
        for no, kol, nama, sat, des, ikon, warna in DINAMIS
    )
    air, s_air = _jarak(grid.jarak_air_meter)
    jalan, s_jalan = _jarak(grid.jarak_jalan_meter)
    statis = "".join([
        _ubin(1, "Ketinggian", angka(grid.ketinggian_meter), "m dpl", "tinggi", "#9c5b2a"),
        _ubin(2, "Kemiringan lereng", angka(grid.kemiringan_lereng, 2), "°", "lereng",
              "#7048e8"),
        _ubin(8, "Jarak ke badan air", air, s_air, "air", "#1971c2"),
        _ubin(9, "Jarak ke jalan", jalan, s_jalan, "jalan", "#495057"),
        _ubin(10, "Tutupan lahan", grid.tutupan_lahan.replace("/", "/<wbr>"), "", "lahan",
              "#2b8a3e", teks=True),
        _ubin(11, "Status gambut", LABEL_GAMBUT.get(grid.gambut, grid.gambut), "", "gambut",
              "#845028", teks=True),
    ])
    asal = ("diambil dari kondisi tercatat di basis data" if k.komposisi is None
            else "disusun dari data cuaca harian Open-Meteo")
    st.markdown(
        '<div class="kl-h2">Rincian variabel prediktor</div>'
        f'<div class="kl-kecil">Sebelas nilai yang menjadi masukan kedua model. Nilai cuaca '
        f'{asal}. Panah ↑/↓ membandingkan nilai cuaca dengan rata-rata bulan '
        f'{BULAN[bulan - 1]} tahun {rata["tahun_awal"]}–{rata["tahun_akhir"]} di grid ini.'
        f'</div>'
        f'<div class="rv-grup">Cuaca bulanan · berubah tiap bulan</div>'
        f'<div class="rv-kisi">{dinamis}</div>'
        f'<div class="rv-grup">Karakteristik grid · tidak berubah dari bulan ke bulan</div>'
        f'<div class="rv-kisi rv-kisi-statis">{statis}</div>',
        unsafe_allow_html=True,
    )
