"""Pengambilan data historis (dan nanti ramalan cuaca) untuk dashboard."""
import json
import math
import sqlite3
import threading
from pathlib import Path

import pandas as pd
import streamlit as st

from domain.grid import Grid, HasilPrediksi, KondisiBulanan

ROOT = Path(__file__).resolve().parent.parent
PATH_DB = ROOT / "data/karhutla.db"
PATH_CUTOFF = ROOT / "data/tertile_cutoff.json"
PATH_WILAYAH = ROOT / "data/grid_wilayah.csv"  # provinsi & kabupaten per grid (GADM v4.1)

KELAS = ["Rendah", "Sedang", "Tinggi"]
UKURAN_GRID = 0.5
_kunci_tulis = threading.Lock()  # koneksi dipakai bersama antar-thread

# Urutan kolom sama dengan dataset_final.csv, supaya muat_dataset() tetap setara.
SQL_DATASET = """
    SELECT g.grid_lat, g.grid_lon, k.tahun_bulan, k.jumlah_hotspot, k.kerawanan,
           g.ketinggian_meter, g.kemiringan_lereng, g.jarak_air_meter,
           g.kode_worldcover, g.tutupan_lahan, g.gambut, g.jarak_jalan_meter,
           k.curah_hujan_mm, k.suhu_maks_c, k.kelembapan_persen,
           k.angin_maks_kmh, k.hari_kering_maks
    FROM   KONDISI_BULANAN k
    JOIN   GRID g ON g.grid_id = k.grid_id
    ORDER  BY g.grid_lat, g.grid_lon, k.tahun_bulan
"""


@st.cache_resource
def _koneksi() -> sqlite3.Connection:
    """Satu koneksi untuk seluruh sesi. check_same_thread=False karena Streamlit
    menjalankan skrip di thread yang berbeda-beda."""
    kon = sqlite3.connect(PATH_DB, check_same_thread=False)
    kon.execute("PRAGMA foreign_keys = ON")
    return kon


def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, _koneksi(), params=params)


@st.cache_data
def _baca_wilayah() -> pd.DataFrame | None:
    if not PATH_WILAYAH.exists():
        return None
    return pd.read_csv(PATH_WILAYAH)[["grid_lat", "grid_lon", "provinsi", "kabupaten"]]


class SumberDataService:
    """Sumber data historis dari basis data karhutla.db dan ambang tertile."""

    def muat_dataset(self) -> pd.DataFrame:
        """Seluruh grid-bulan dalam bentuk yang sama dengan dataset_final.csv."""
        return _query(SQL_DATASET)

    def muat_cutoff(self) -> dict:
        with open(PATH_CUTOFF, encoding="utf-8") as f:
            return json.load(f)

    def periode_terakhir(self) -> str:
        return _koneksi().execute(
            "SELECT MAX(tahun_bulan) FROM KONDISI_BULANAN").fetchone()[0]

    def ringkasan_kategori(self, tahun_bulan: str) -> pd.Series:
        """Jumlah grid per kelas kerawanan pada satu periode."""
        df = _query("SELECT kerawanan, COUNT(*) AS jumlah FROM KONDISI_BULANAN "
                    "WHERE tahun_bulan = ? GROUP BY kerawanan", (tahun_bulan,))
        return (df.set_index("kerawanan")["jumlah"]
                  .rename_axis(None)
                  .reindex(KELAS, fill_value=0))

    def muat_grid(self) -> pd.DataFrame:
        """232 grid resmi (titik pusat), termasuk yang tidak ada di dataset, beserta
        provinsi dan kabupatennya (None kalau grid_wilayah.csv belum ada)."""
        grid = _query("SELECT grid_lat, grid_lon FROM GRID ORDER BY rowid")
        wilayah = _baca_wilayah()
        if wilayah is None:
            return grid.assign(provinsi=None, kabupaten=None)
        hasil = grid.merge(wilayah, on=["grid_lat", "grid_lon"], how="left")
        if len(hasil) != len(grid):
            raise ValueError("grid_wilayah.csv punya koordinat ganda; harus satu baris per grid")
        return hasil

    def kategori_per_grid(self, tahun_bulan: str) -> pd.DataFrame:
        """Kelas kerawanan tiap grid resmi pada satu periode; grid tanpa data diberi
        label "Tidak ada data"."""
        periode = _query(
            "SELECT g.grid_lat, g.grid_lon, k.kerawanan, k.jumlah_hotspot "
            "FROM GRID g LEFT JOIN KONDISI_BULANAN k "
            "  ON k.grid_id = g.grid_id AND k.tahun_bulan = ? "
            "ORDER BY g.rowid", (tahun_bulan,))
        hasil = self.muat_grid().merge(periode, on=["grid_lat", "grid_lon"], how="left")
        hasil["kerawanan"] = hasil["kerawanan"].fillna("Tidak ada data")
        return hasil

    def daftar_periode(self) -> list[str]:
        """Semua periode "YYYY-MM" yang ada di dataset, urut naik."""
        return [b[0] for b in _koneksi().execute(
            "SELECT DISTINCT tahun_bulan FROM KONDISI_BULANAN ORDER BY tahun_bulan")]

    def tren_kategori(self) -> pd.DataFrame:
        """Jumlah grid per kelas kerawanan untuk tiap periode (baris = tahun_bulan)."""
        df = _query("SELECT tahun_bulan, kerawanan, COUNT(*) AS jumlah "
                    "FROM KONDISI_BULANAN GROUP BY tahun_bulan, kerawanan")
        return (df.pivot(index="tahun_bulan", columns="kerawanan", values="jumlah")
                  .fillna(0).astype(int)
                  .reindex(columns=KELAS, fill_value=0))

    def sebaran_provinsi(self, tahun_bulan: str) -> pd.DataFrame:
        """Jumlah grid per kelas kerawanan di tiap provinsi pada satu periode
        (baris = provinsi, kolom = KELAS). Kosong kalau grid_wilayah.csv belum ada."""
        grid = self.kategori_per_grid(tahun_bulan)
        grid = grid[grid["kerawanan"].isin(KELAS) & grid["provinsi"].notna()]
        return (grid.groupby(["provinsi", "kerawanan"]).size()
                    .unstack(fill_value=0)
                    .reindex(columns=KELAS, fill_value=0))

    # ---- untuk modul Klasifikasi -------------------------------------------------

    def daftar_grid_tersedia(self) -> pd.DataFrame:
        """Grid yang ada di dataset (ada_di_dataset = 1) beserta nama wilayahnya,
        urut provinsi lalu kabupaten."""
        grid = _query("SELECT grid_id, grid_lat, grid_lon FROM GRID "
                      "WHERE ada_di_dataset = 1")
        wilayah = _baca_wilayah()
        if wilayah is None:
            return grid.assign(provinsi=None, kabupaten=None).sort_values(
                ["grid_lat", "grid_lon"], ignore_index=True)
        return (grid.merge(wilayah, on=["grid_lat", "grid_lon"], how="left")
                    .sort_values(["provinsi", "kabupaten", "grid_lat", "grid_lon"],
                                 ignore_index=True))

    def cari_grid(self, lat: float, lon: float) -> tuple[str | None, bool]:
        """Grid 0,5 derajat yang memuat koordinat (lat, lon).
        Mengembalikan (grid_id, ada_di_dataset); grid_id None kalau di luar 232 grid."""
        pusat_lat = math.floor(lat / UKURAN_GRID) * UKURAN_GRID + UKURAN_GRID / 2
        pusat_lon = math.floor(lon / UKURAN_GRID) * UKURAN_GRID + UKURAN_GRID / 2
        baris = _koneksi().execute(
            "SELECT grid_id, ada_di_dataset FROM GRID "
            "WHERE ABS(grid_lat - ?) < 1e-6 AND ABS(grid_lon - ?) < 1e-6",
            (pusat_lat, pusat_lon)).fetchone()
        return (baris[0], bool(baris[1])) if baris else (None, False)

    def muat_grid_kondisi(self, grid_id: str, tahun_bulan: str) -> Grid | None:
        """Grid beserta KondisiBulanan-nya pada satu periode; None kalau tidak ada."""
        baris = _query(
            "SELECT g.grid_id, g.grid_lat, g.grid_lon, g.ketinggian_meter, "
            "       g.kemiringan_lereng, g.jarak_air_meter, g.jarak_jalan_meter, "
            "       g.tutupan_lahan, g.gambut, "
            "       k.kondisi_id, k.tahun_bulan, k.curah_hujan_mm, k.suhu_maks_c, "
            "       k.kelembapan_persen, k.angin_maks_kmh, k.hari_kering_maks, "
            "       k.jumlah_hotspot, k.kerawanan "
            "FROM GRID g JOIN KONDISI_BULANAN k ON k.grid_id = g.grid_id "
            "WHERE g.grid_id = ? AND k.tahun_bulan = ?", (grid_id, tahun_bulan))
        if baris.empty:
            return None
        r = baris.iloc[0]
        nama = {"provinsi": None, "kabupaten": None}
        wilayah = _baca_wilayah()
        if wilayah is not None:
            cocok = wilayah[(wilayah.grid_lat == r.grid_lat) & (wilayah.grid_lon == r.grid_lon)]
            if len(cocok):
                nama = cocok.iloc[0][["provinsi", "kabupaten"]].to_dict()
        grid = Grid(
            grid_id=r.grid_id, grid_lat=float(r.grid_lat), grid_lon=float(r.grid_lon),
            ketinggian_meter=r.ketinggian_meter, kemiringan_lereng=r.kemiringan_lereng,
            jarak_air_meter=r.jarak_air_meter, jarak_jalan_meter=r.jarak_jalan_meter,
            tutupan_lahan=r.tutupan_lahan, gambut=r.gambut, **nama,
        )
        grid.kondisi.append(KondisiBulanan(
            kondisi_id=int(r.kondisi_id), tahun_bulan=r.tahun_bulan,
            curah_hujan_mm=r.curah_hujan_mm, suhu_maks_c=r.suhu_maks_c,
            kelembapan_persen=r.kelembapan_persen, angin_maks_kmh=r.angin_maks_kmh,
            hari_kering_maks=int(r.hari_kering_maks), jumlah_hotspot=int(r.jumlah_hotspot),
            kerawanan=r.kerawanan,
        ))
        return grid

    def simpan_hasil(self, kondisi_id: int, hasil: list[HasilPrediksi]) -> None:
        """Simpan hasil tiap model ke tabel HASIL_PREDIKSI."""
        with _kunci_tulis:
            kon = _koneksi()
            with kon:  # commit otomatis, rollback kalau gagal
                kon.executemany(
                    "INSERT INTO HASIL_PREDIKSI (kondisi_id, model, kelas_prediksi, probabilitas) "
                    "VALUES (?, ?, ?, ?)",
                    [(kondisi_id, h.model, h.kelas, h.confidence) for h in hasil])
