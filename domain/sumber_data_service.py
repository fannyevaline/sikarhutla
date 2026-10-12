"""Pengambilan data historis (dan nanti ramalan cuaca) untuk dashboard."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PATH_DATASET = ROOT / "data/04_final/dataset_final.csv"
PATH_CUTOFF = ROOT / "data/02_grid/tertile_cutoff.json"

KELAS = ["Rendah", "Sedang", "Tinggi"]


@st.cache_data
def _baca_dataset() -> pd.DataFrame:
    return pd.read_csv(PATH_DATASET)


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
