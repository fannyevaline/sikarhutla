"""Orkestrator klasifikasi sesuai class diagram.

ModulKlasifikasi menyimpan kedua model sebagai atribut (asosiasi) dan memakai
SumberDataService (dependency) untuk mengambil data dan menyimpan hasil.
"""
import pandas as pd

from domain.grid import Grid
from domain.model_klasifikasi import RandomForestModel, XGBoostModel, siapkan
from domain.sumber_data_service import SumberDataService


class ModulKlasifikasi:
    def __init__(self, sumber: SumberDataService):
        self.sumber = sumber
        self.rf = RandomForestModel()
        self.xgb = XGBoostModel()

    def klasifikasi(self, grid_id: str, tahun_bulan: str, simpan: bool = True) -> Grid | None:
        """Jalankan kedua model untuk satu grid-bulan. Hasilnya menempel di
        grid.kondisi[0].hasil (urutan: Random Forest, XGBoost)."""
        grid = self.sumber.muat_grid_kondisi(grid_id, tahun_bulan)
        if grid is None:
            return None
        kondisi = grid.kondisi[0]
        X = siapkan(pd.DataFrame([grid.baris_fitur(kondisi)]))
        kondisi.hasil = [self.rf.predict(X)[0], self.xgb.predict(X)[0]]
        if simpan:
            self.sumber.simpan_hasil(kondisi.kondisi_id, kondisi.hasil)
        return grid
