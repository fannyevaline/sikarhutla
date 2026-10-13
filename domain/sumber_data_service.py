"""Pengambilan data historis (dan nanti ramalan cuaca) untuk dashboard."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PATH_DATASET = ROOT / "data/dataset_final.csv"
PATH_CUTOFF = ROOT / "data/tertile_cutoff.json"
PATH_GRID = ROOT / "data/grid_kalimantan.csv"
PATH_WILAYAH = ROOT / "data/grid_wilayah.csv"  # provinsi & kabupaten per grid (GADM v4.1)

KELAS = ["Rendah", "Sedang", "Tinggi"]


@st.cache_data
def _baca_dataset() -> pd.DataFrame:
    return pd.read_csv(PATH_DATASET)


@st.cache_data
def _baca_grid() -> pd.DataFrame:
    grid = pd.read_csv(PATH_GRID)
    if not PATH_WILAYAH.exists():
        return grid.assign(provinsi=None, kabupaten=None)
    wilayah = pd.read_csv(PATH_WILAYAH)[["grid_lat", "grid_lon", "provinsi", "kabupaten"]]
    hasil = grid.merge(wilayah, on=["grid_lat", "grid_lon"], how="left")
    if len(hasil) != len(grid):
        raise ValueError("grid_wilayah.csv punya koordinat ganda; harus satu baris per grid")
    return hasil


class SumberDataService:
    """Sumber data historis dari dataset_final.csv dan ambang tertile."""

    def muat_dataset(self) -> pd.DataFrame:
        return _baca_dataset()

    def muat_cutoff(self) -> dict:
        with open(PATH_CUTOFF, encoding="utf-8") as f:
            return json.load(f)

    def periode_terakhir(self) -> str:
        return self.muat_dataset()["tahun_bulan"].max()

    def ringkasan_kategori(self, tahun_bulan: str) -> pd.Series:
        """Jumlah grid per kelas kerawanan pada satu periode."""
        df = self.muat_dataset()
        return (df.loc[df["tahun_bulan"] == tahun_bulan, "kerawanan"]
                  .value_counts()
                  .reindex(KELAS, fill_value=0))

    def muat_grid(self) -> pd.DataFrame:
        """232 grid resmi (titik pusat), termasuk yang tidak ada di dataset, beserta
        provinsi dan kabupatennya (None kalau grid_wilayah.csv belum ada)."""
        return _baca_grid()

    def kategori_per_grid(self, tahun_bulan: str) -> pd.DataFrame:
        """Kelas kerawanan tiap grid resmi pada satu periode; grid tanpa data diberi
        label "Tidak ada data"."""
        df = self.muat_dataset()
        periode = df.loc[df["tahun_bulan"] == tahun_bulan,
                         ["grid_lat", "grid_lon", "kerawanan", "jumlah_hotspot"]]
        hasil = self.muat_grid().merge(periode, on=["grid_lat", "grid_lon"], how="left")
        hasil["kerawanan"] = hasil["kerawanan"].fillna("Tidak ada data")
        return hasil

    def daftar_periode(self) -> list[str]:
        """Semua periode "YYYY-MM" yang ada di dataset, urut naik."""
        return sorted(self.muat_dataset()["tahun_bulan"].unique())

    def tren_kategori(self) -> pd.DataFrame:
        """Jumlah grid per kelas kerawanan untuk tiap periode (baris = tahun_bulan)."""
        return (self.muat_dataset()
                    .groupby(["tahun_bulan", "kerawanan"]).size()
                    .unstack(fill_value=0)
                    .reindex(columns=KELAS, fill_value=0))
