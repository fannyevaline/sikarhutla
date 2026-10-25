"""Konstanta bersama seluruh backend: kelas, fitur model, ukuran grid, dan lokasi berkas.

Semua path relatif terhadap folder aplikasi, supaya bisa dijalankan di komputer lain.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---- berkas data -------------------------------------------------------------------
PATH_DB = ROOT / "data/karhutla.db"
PATH_CUTOFF = ROOT / "data/tertile_cutoff.json"
PATH_WILAYAH = ROOT / "data/grid_wilayah.csv"  # provinsi & kabupaten per grid (GADM v4.1)
PATH_PERBANDINGAN = ROOT / "data/model/perbandingan_smotenc.csv"
PATH_METRIK_RINGKASAN = ROOT / "data/model/metrik_lengkap_ringkasan.csv"
PATH_METRIK_PER_KELAS = ROOT / "data/model/metrik_lengkap_per_kelas.csv"
PATH_CONFUSION_MATRIX = ROOT / "data/model/confusion_matrix.csv"
PATH_MODEL_RF = ROOT / "data/model/model_rf_final.pkl"
PATH_MODEL_XGB = ROOT / "data/model/model_xgb_final.pkl"
PATH_KOLOM_ENCODED = ROOT / "data/model/feature_columns_encoded.pkl"
PATH_CACHE_CUACA = ROOT / ".cache/cuaca_harian.csv"

SKENARIO_FINAL = "DENGAN SMOTENC"  # skenario yang disimpan sebagai *_final.pkl

# ---- kelas dan fitur (dikunci di Bab 3; jangan diubah) ------------------------------
KELAS = ["Rendah", "Sedang", "Tinggi"]

FEATURE_COLS = [
    "ketinggian_meter", "kemiringan_lereng", "curah_hujan_mm", "suhu_maks_c",
    "kelembapan_persen", "angin_maks_kmh", "hari_kering_maks", "jarak_air_meter",
    "jarak_jalan_meter", "tutupan_lahan", "gambut",
]
CAT_COLS = ["tutupan_lahan", "gambut"]

UKURAN_GRID = 0.5  # derajat
