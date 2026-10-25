"""Model pre-trained sesuai class diagram: ModelKlasifikasi (abstrak) dengan turunan
RandomForestModel dan XGBoostModel.

Hanya memuat .pkl lalu memanggil predict()/predict_proba(). Tidak ada fit() di sini.
Cara pemanggilan mengikuti catatan.md persis.
"""
from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st
from sklearn.preprocessing import LabelEncoder

from domain.grid import HasilPrediksi

ROOT = Path(__file__).resolve().parent.parent

FEATURE_COLS = [
    "ketinggian_meter", "kemiringan_lereng", "curah_hujan_mm", "suhu_maks_c",
    "kelembapan_persen", "angin_maks_kmh", "hari_kering_maks", "jarak_air_meter",
    "jarak_jalan_meter", "tutupan_lahan", "gambut",
]
CAT_COLS = ["tutupan_lahan", "gambut"]
KELAS = ["Rendah", "Sedang", "Tinggi"]

le = LabelEncoder(); le.fit(KELAS)


@st.cache_resource
def _muat_pkl(path: str):
    return joblib.load(ROOT / path)


def siapkan(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode lalu samakan kolomnya dengan waktu pelatihan."""
    kolom_encoded = _muat_pkl("data/model/feature_columns_encoded.pkl")
    return (pd.get_dummies(df[FEATURE_COLS], columns=CAT_COLS)
              .reindex(columns=kolom_encoded, fill_value=0))


def kategori_dikenal(kolom: str) -> set[str]:
    """Nilai kategori yang punya kolom one-hot saat pelatihan."""
    awalan = f"{kolom}_"
    return {c[len(awalan):] for c in _muat_pkl("data/model/feature_columns_encoded.pkl")
            if c.startswith(awalan)}


class ModelKlasifikasi(ABC):
    """Kelas abstrak: setiap model mengembalikan HasilPrediksi per baris input."""
    nama: str

    def __init__(self, path: str):
        self.model = _muat_pkl(path)

    @abstractmethod
    def kelas_model(self) -> list[str]:
        """Nama kelas (teks) sesuai urutan kolom predict_proba."""

    @abstractmethod
    def _predict_teks(self, X: pd.DataFrame) -> list[str]:
        """Kelas prediksi dalam bentuk teks."""

    def predict(self, X: pd.DataFrame) -> list[HasilPrediksi]:
        kelas = self._predict_teks(X)
        proba = self.model.predict_proba(X)
        urutan = self.kelas_model()
        hasil = []
        for k, p in zip(kelas, proba):
            peluang = dict(zip(urutan, map(float, p)))
            hasil.append(HasilPrediksi(
                model=self.nama, kelas=k, confidence=float(p.max()),
                probabilitas={c: peluang[c] for c in KELAS},
            ))
        return hasil


class RandomForestModel(ModelKlasifikasi):
    """Dilatih dengan label TEKS -> keluarannya sudah teks."""
    nama = "Random Forest"

    def __init__(self):
        super().__init__("data/model/model_rf_final.pkl")

    def kelas_model(self) -> list[str]:
        return list(self.model.classes_)

    def _predict_teks(self, X: pd.DataFrame) -> list[str]:
        return list(self.model.predict(X))


class XGBoostModel(ModelKlasifikasi):
    """Dilatih dengan label ANGKA -> wajib di-inverse_transform."""
    nama = "XGBoost"

    def __init__(self):
        super().__init__("data/model/model_xgb_final.pkl")

    def kelas_model(self) -> list[str]:
        return list(le.inverse_transform(self.model.classes_))

    def _predict_teks(self, X: pd.DataFrame) -> list[str]:
        return list(le.inverse_transform(self.model.predict(X)))
