"""Orkestrator klasifikasi sesuai class diagram.

ModulKlasifikasi menyimpan kedua model sebagai atribut (asosiasi) dan memakai
SumberDataService (dependency) untuk mengambil data dan menyimpan hasil.
"""
import pandas as pd

from domain.grid import Grid, HasilPrediksi
from domain.model_klasifikasi import RandomForestModel, XGBoostModel, siapkan
from domain.sumber_data_service import SumberDataService


class ModulKlasifikasi:
    def __init__(self, sumber: SumberDataService):
        self.sumber = sumber
        self.rf = RandomForestModel()
        self.xgb = XGBoostModel()

    def klasifikasi(self, grid_id: str, tahun_bulan: str, simpan: bool = True) -> Grid | None:
        """Jalankan kedua model untuk satu grid-bulan. Hasilnya menempel di
        grid.kondisi[0].hasil (urutan: Random Forest, XGBoost).

        Periode di basis data memakai kondisi tercatat. Periode sesudahnya memakai
        cuaca yang disusun dari Open-Meteo (bisa melempar GagalAmbilCuaca); hasilnya
        tidak disimpan karena HASIL_PREDIKSI merujuk ke baris KONDISI_BULANAN."""
        if self.sumber.status_periode(tahun_bulan) == "historis":
            grid = self.sumber.muat_grid_kondisi(grid_id, tahun_bulan)
        else:
            grid = self.sumber.muat_grid_statis(grid_id)
            if grid is not None:
                grid.kondisi.append(self.sumber.susun_kondisi_cuaca(grid, tahun_bulan))
        if grid is None:
            return None
        kondisi = grid.kondisi[0]
        X = siapkan(pd.DataFrame([grid.baris_fitur(kondisi)]))
        kondisi.hasil = [self.rf.predict(X)[0], self.xgb.predict(X)[0]]
        if simpan and kondisi.kondisi_id is not None:
            self.sumber.simpan_hasil(kondisi.kondisi_id, kondisi.hasil)
        return grid

    def simulasi(self, nilai: dict) -> list[HasilPrediksi]:
        """Jalankan kedua model untuk sebelas nilai isian pengguna (urutan: Random
        Forest, XGBoost). Tidak disimpan ke HASIL_PREDIKSI karena tidak terikat grid
        maupun periode."""
        X = siapkan(pd.DataFrame([nilai]))
        return [self.rf.predict(X)[0], self.xgb.predict(X)[0]]

    def klasifikasi_bulan(self, tahun_bulan: str, kabar=None) -> pd.DataFrame:
        """Jalankan kedua model untuk semua grid pada bulan di luar basis data (untuk
        mewarnai peta). Baris = grid_id; kolom kelas_rf, conf_rf, kelas_xgb, conf_xgb.
        Tidak disimpan ke HASIL_PREDIKSI."""
        statis = self.sumber.muat_grid_statis_semua().set_index("grid_id")
        cuaca = self.sumber.susun_cuaca_semua(tahun_bulan, kabar)
        X = siapkan(statis.join(cuaca))
        hasil = pd.DataFrame(index=statis.index)
        for akhiran, model in (("rf", self.rf), ("xgb", self.xgb)):
            prediksi = model.predict(X)
            hasil[f"kelas_{akhiran}"] = [h.kelas for h in prediksi]
            hasil[f"conf_{akhiran}"] = [h.confidence for h in prediksi]
        return hasil
