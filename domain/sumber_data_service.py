"""Pengambilan data historis (basis data) dan cuaca Open-Meteo untuk dashboard."""
import calendar
import json
import math
import sqlite3
import threading
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from domain import open_meteo
from domain.grid import Grid, HasilPrediksi, KomposisiCuaca, KondisiBulanan
from domain.konstanta import (KELAS, PATH_CONFUSION_MATRIX,
                              PATH_CONFUSION_MATRIX_EKSTERNAL, PATH_CUTOFF, PATH_DB,
                              PATH_METRIK_EKSTERNAL_PER_KELAS,
                              PATH_METRIK_EKSTERNAL_RINGKASAN, PATH_METRIK_PER_KELAS,
                              PATH_METRIK_RINGKASAN, PATH_PERBANDINGAN, PATH_WILAYAH,
                              SKENARIO_FINAL, UKURAN_GRID)

WIB = timezone(timedelta(hours=7))
_kunci_tulis = threading.Lock()  # koneksi dipakai bersama antar-thread

# Kolom tabel GRID yang menjadi variabel statis model, beserta penanda grid-nya.
SQL_GRID_STATIS = (
    "SELECT grid_id, grid_lat, grid_lon, ketinggian_meter, kemiringan_lereng, "
    "       jarak_air_meter, jarak_jalan_meter, tutupan_lahan, gambut "
    "FROM GRID WHERE ada_di_dataset = 1"
)


# ---- akses basis data dan berkas ---------------------------------------------------

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


def _tambah_wilayah(grid: pd.DataFrame) -> pd.DataFrame:
    """Tambahkan kolom provinsi dan kabupaten (None kalau grid_wilayah.csv belum ada)."""
    wilayah = _baca_wilayah()
    if wilayah is None:
        return grid.assign(provinsi=None, kabupaten=None)
    hasil = grid.merge(wilayah, on=["grid_lat", "grid_lon"], how="left")
    if len(hasil) != len(grid):
        raise ValueError("grid_wilayah.csv punya koordinat ganda; harus satu baris per grid")
    return hasil


def _baca_perbandingan_final() -> pd.DataFrame:
    """Baris perbandingan_smotenc.csv untuk skenario model final, indeks = Model."""
    hasil = pd.read_csv(PATH_PERBANDINGAN)
    return hasil[hasil["Skenario"] == SKENARIO_FINAL].set_index("Model")


class SumberDataService:
    """Sumber data historis dari basis data karhutla.db dan ambang tertile."""

    def muat_cutoff(self) -> dict:
        with open(PATH_CUTOFF, encoding="utf-8") as f:
            return json.load(f)

    def model_terbaik(self) -> str:
        """Model dengan F1-macro tertinggi pada skenario model final (DENGAN SMOTENC,
        sesuai train_model_compare.py), menurut perbandingan_smotenc.csv."""
        return _baca_perbandingan_final()["F1_Macro"].idxmax()

    def f1_per_kelas(self) -> pd.DataFrame:
        """F1 tiap kelas pada skenario model final (baris = model, kolom = KELAS)."""
        return _baca_perbandingan_final()[[f"F1_{k}" for k in KELAS]].set_axis(KELAS, axis=1)

    # ---- untuk modul Performa Model (hanya dibaca, tidak dihitung ulang) -------------

    def metrik_ringkasan(self) -> pd.DataFrame:
        """Metrik keseluruhan empat skenario (2 skenario x 2 model), urut seperti di
        metrik_lengkap_ringkasan.csv."""
        return pd.read_csv(PATH_METRIK_RINGKASAN)

    def metrik_per_kelas(self, skenario: str, model: str) -> pd.DataFrame:
        """Metrik tiap kelas untuk satu skenario dan model (indeks = KELAS), dari
        metrik_lengkap_per_kelas.csv."""
        df = pd.read_csv(PATH_METRIK_PER_KELAS)
        pilih = df[(df["Skenario"] == skenario) & (df["Model"] == model)]
        return pilih.set_index("Kelas").reindex(KELAS)

    def confusion_matrix(self, skenario: str, model: str) -> pd.DataFrame:
        """Confusion matrix satu skenario dan model dari confusion_matrix.csv.
        Baris = kelas sebenarnya (urut KELAS); kolom Prediksi_Rendah, Prediksi_Sedang,
        Prediksi_Tinggi, dan Jumlah_data."""
        df = pd.read_csv(PATH_CONFUSION_MATRIX)
        pilih = df[(df["Skenario"] == skenario) & (df["Model"] == model)]
        return pilih.set_index("Kelas_sebenarnya").reindex(KELAS)

    # Pengujian eksternal: berkasnya tidak memakai kolom Skenario, melainkan Periode
    # ("Keseluruhan" atau "YYYY-MM"); confusion matrix-nya hanya untuk keseluruhan periode.

    def berkas_eksternal_kurang(self) -> list[str]:
        """Nama berkas pengujian eksternal yang belum ada (kosong = lengkap)."""
        return [p.name for p in (PATH_METRIK_EKSTERNAL_RINGKASAN,
                                 PATH_METRIK_EKSTERNAL_PER_KELAS,
                                 PATH_CONFUSION_MATRIX_EKSTERNAL) if not p.exists()]

    def metrik_eksternal_ringkasan(self) -> pd.DataFrame:
        """Metrik keseluruhan pengujian eksternal, per periode dan model."""
        return pd.read_csv(PATH_METRIK_EKSTERNAL_RINGKASAN)

    def metrik_eksternal_per_kelas(self, periode: str, model: str) -> pd.DataFrame:
        """Metrik tiap kelas pengujian eksternal untuk satu periode dan model
        (indeks = KELAS)."""
        df = pd.read_csv(PATH_METRIK_EKSTERNAL_PER_KELAS)
        pilih = df[(df["Periode"] == periode) & (df["Model"] == model)]
        return pilih.set_index("Kelas").reindex(KELAS)

    def confusion_matrix_eksternal(self, model: str) -> pd.DataFrame:
        """Confusion matrix pengujian eksternal satu model, seluruh periode.
        Baris = kelas sebenarnya (urut KELAS)."""
        df = pd.read_csv(PATH_CONFUSION_MATRIX_EKSTERNAL)
        return df[df["Model"] == model].set_index("Kelas_sebenarnya").reindex(KELAS)

    # ---- ringkasan untuk Beranda -------------------------------------------------

    def periode_terakhir(self) -> str:
        return _koneksi().execute(
            "SELECT MAX(tahun_bulan) FROM KONDISI_BULANAN").fetchone()[0]

    def daftar_periode(self) -> list[str]:
        """Semua periode "YYYY-MM" yang ada di dataset, urut naik."""
        return [b[0] for b in _koneksi().execute(
            "SELECT DISTINCT tahun_bulan FROM KONDISI_BULANAN ORDER BY tahun_bulan")]

    def ringkasan_kategori(self, tahun_bulan: str) -> pd.Series:
        """Jumlah grid per kelas kerawanan pada satu periode."""
        df = _query("SELECT kerawanan, COUNT(*) AS jumlah FROM KONDISI_BULANAN "
                    "WHERE tahun_bulan = ? GROUP BY kerawanan", (tahun_bulan,))
        return (df.set_index("kerawanan")["jumlah"]
                  .rename_axis(None)
                  .reindex(KELAS, fill_value=0))

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

    # ---- grid untuk peta dan pemilihan wilayah ------------------------------------

    def muat_grid(self) -> pd.DataFrame:
        """232 grid resmi (titik pusat), termasuk yang tidak ada di dataset, beserta
        provinsi dan kabupatennya."""
        return _tambah_wilayah(_query("SELECT grid_lat, grid_lon FROM GRID ORDER BY rowid"))

    def kategori_per_grid(self, tahun_bulan: str) -> pd.DataFrame:
        """Kelas kerawanan tiap grid resmi pada satu periode; grid tanpa data diberi
        label "Tidak ada data"."""
        periode = _query(
            "SELECT g.grid_id, g.grid_lat, g.grid_lon, g.ada_di_dataset, "
            "       k.kerawanan, k.jumlah_hotspot "
            "FROM GRID g LEFT JOIN KONDISI_BULANAN k "
            "  ON k.grid_id = g.grid_id AND k.tahun_bulan = ? "
            "ORDER BY g.rowid", (tahun_bulan,))
        hasil = self.muat_grid().merge(periode, on=["grid_lat", "grid_lon"], how="left")
        hasil["kerawanan"] = hasil["kerawanan"].fillna("Tidak ada data")
        return hasil

    def daftar_grid_tersedia(self) -> pd.DataFrame:
        """Grid yang ada di dataset (ada_di_dataset = 1) beserta nama wilayahnya,
        urut provinsi lalu kabupaten."""
        grid = _tambah_wilayah(_query("SELECT grid_id, grid_lat, grid_lon FROM GRID "
                                      "WHERE ada_di_dataset = 1"))
        urutan = (["grid_lat", "grid_lon"] if grid["provinsi"].isna().all()
                  else ["provinsi", "kabupaten", "grid_lat", "grid_lon"])
        return grid.sort_values(urutan, ignore_index=True)

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

    # ---- untuk modul Simulasi ----------------------------------------------------

    def rentang_variabel(self) -> tuple[pd.DataFrame, dict[str, list[str]]]:
        """Min, max, dan median tiap variabel numerik (baris = kolom), serta nilai unik
        variabel kategorikal urut dari yang paling sering. Variabel statis dihitung
        dari 221 grid (satu nilai per grid), variabel cuaca dari seluruh grid-bulan."""
        statis = _query(SQL_GRID_STATIS).drop(columns=["grid_id", "grid_lat", "grid_lon"])
        cuaca = _query("SELECT curah_hujan_mm, suhu_maks_c, kelembapan_persen, "
                       "       angin_maks_kmh, hari_kering_maks FROM KONDISI_BULANAN")
        numerik = pd.concat([statis.select_dtypes("number"), cuaca], axis=1)
        rentang = numerik.agg(["min", "max", "median"]).T
        kategori = {k: statis[k].value_counts().index.tolist()
                    for k in ("tutupan_lahan", "gambut")}
        return rentang, kategori

    # ---- periode -----------------------------------------------------------------

    def hari_ini(self) -> date:
        return datetime.now(WIB).date()

    def daftar_periode_pilihan(self) -> list[str]:
        """Periode di basis data, disambung bulan-bulan sesudahnya sampai bulan yang
        masih terjangkau ramalan (hari ini + 15, batas akhir Forecast API)."""
        daftar = self.daftar_periode()
        batas = self.hari_ini() + timedelta(days=open_meteo.JANGKAUAN_RAMALAN - 1)
        tambahan = pd.period_range(pd.Period(daftar[-1], "M") + 1, pd.Period(batas, "M"),
                                   freq="M")
        return daftar + [str(p) for p in tambahan]

    def status_periode(self, tahun_bulan: str) -> str:
        """historis = ada di basis data; selesai = sudah lewat tetapi belum ada di
        basis data; berjalan = memuat hari ini; mendatang = belum dimulai."""
        if tahun_bulan <= self.periode_terakhir():
            return "historis"
        hari_ini = self.hari_ini()
        tahun, bulan = map(int, tahun_bulan.split("-"))
        if date(tahun, bulan, calendar.monthrange(tahun, bulan)[1]) < hari_ini:
            return "selesai"
        if (tahun, bulan) == (hari_ini.year, hari_ini.month):
            return "berjalan"
        return "mendatang"

    # ---- grid dan kondisi bulanan ----------------------------------------------------

    def muat_grid_statis_semua(self) -> pd.DataFrame:
        """Variabel statis semua grid yang ada di dataset (221 baris)."""
        return _query(SQL_GRID_STATIS + " ORDER BY rowid")

    def muat_grid_statis(self, grid_id: str) -> Grid | None:
        """Grid beserta variabel statisnya (tanpa kondisi bulanan); None kalau grid
        tidak ada di dataset."""
        baris = _tambah_wilayah(_query(SQL_GRID_STATIS + " AND grid_id = ?", (grid_id,)))
        if baris.empty:
            return None
        r = baris.iloc[0]
        return Grid(
            grid_id=r.grid_id, grid_lat=float(r.grid_lat), grid_lon=float(r.grid_lon),
            ketinggian_meter=r.ketinggian_meter, kemiringan_lereng=r.kemiringan_lereng,
            jarak_air_meter=r.jarak_air_meter, jarak_jalan_meter=r.jarak_jalan_meter,
            tutupan_lahan=r.tutupan_lahan, gambut=r.gambut,
            provinsi=r.provinsi, kabupaten=r.kabupaten,
        )

    def muat_grid_kondisi(self, grid_id: str, tahun_bulan: str) -> Grid | None:
        """Grid beserta KondisiBulanan-nya dari basis data; None kalau tidak ada."""
        grid = self.muat_grid_statis(grid_id)
        baris = _query(
            "SELECT kondisi_id, tahun_bulan, curah_hujan_mm, suhu_maks_c, "
            "       kelembapan_persen, angin_maks_kmh, hari_kering_maks, "
            "       jumlah_hotspot, kerawanan "
            "FROM KONDISI_BULANAN WHERE grid_id = ? AND tahun_bulan = ?",
            (grid_id, tahun_bulan))
        if grid is None or baris.empty:
            return None
        r = baris.iloc[0]
        grid.kondisi.append(KondisiBulanan(
            kondisi_id=int(r.kondisi_id), tahun_bulan=r.tahun_bulan,
            curah_hujan_mm=r.curah_hujan_mm, suhu_maks_c=r.suhu_maks_c,
            kelembapan_persen=r.kelembapan_persen, angin_maks_kmh=r.angin_maks_kmh,
            hari_kering_maks=int(r.hari_kering_maks), jumlah_hotspot=int(r.jumlah_hotspot),
            kerawanan=r.kerawanan,
        ))
        return grid

    def rata_rata_bulan(self, grid_id: str, bulan: int) -> pd.Series:
        """Rata-rata variabel dinamis grid pada bulan kalender yang sama di dataset."""
        return _query(
            "SELECT AVG(curah_hujan_mm) AS curah_hujan_mm, AVG(suhu_maks_c) AS suhu_maks_c, "
            "       AVG(kelembapan_persen) AS kelembapan_persen, "
            "       AVG(angin_maks_kmh) AS angin_maks_kmh, "
            "       AVG(hari_kering_maks) AS hari_kering_maks, "
            "       MIN(substr(tahun_bulan, 1, 4)) AS tahun_awal, "
            "       MAX(substr(tahun_bulan, 1, 4)) AS tahun_akhir "
            "FROM KONDISI_BULANAN WHERE grid_id = ? AND substr(tahun_bulan, 6, 2) = ?",
            (grid_id, f"{bulan:02d}")).iloc[0]

    # ---- cuaca bulan di luar basis data (Open-Meteo) --------------------------------

    def susun_cuaca_semua(self, tahun_bulan: str, kabar=None) -> pd.DataFrame:
        """Lima variabel cuaca bulanan semua grid untuk bulan di luar basis data,
        disusun dari Open-Meteo (lihat domain/open_meteo.py). Baris = grid_id."""
        grid = self.muat_grid_statis_semua()
        lokasi = list(zip(grid.grid_lat.astype(float), grid.grid_lon.astype(float)))
        hari_ini = self.hari_ini()
        cuaca = open_meteo.ingat(
            ("bulan", tahun_bulan, hari_ini),
            lambda: open_meteo.susun_bulan(lokasi, tahun_bulan, hari_ini,
                                           kabar or (lambda _: None)))
        return cuaca.set_axis(grid.grid_id).rename_axis("grid_id")

    def susun_kondisi_cuaca(self, grid: Grid, tahun_bulan: str) -> KondisiBulanan:
        """KondisiBulanan satu grid untuk bulan di luar basis data. Diambil dari hasil
        susun_cuaca_semua() supaya sama persis dengan yang dipakai peta."""
        r = self.susun_cuaca_semua(tahun_bulan).loc[grid.grid_id]
        return KondisiBulanan(
            kondisi_id=None, tahun_bulan=tahun_bulan,
            curah_hujan_mm=r.curah_hujan_mm, suhu_maks_c=r.suhu_maks_c,
            kelembapan_persen=r.kelembapan_persen, angin_maks_kmh=r.angin_maks_kmh,
            hari_kering_maks=int(r.hari_kering_maks), jumlah_hotspot=None, kerawanan=None,
            komposisi=KomposisiCuaca(int(r.hari_observasi), int(r.hari_ramalan),
                                     int(r.hari_klimatologi)),
        )

    # ---- penyimpanan ---------------------------------------------------------------

    def simpan_hasil(self, kondisi_id: int, hasil: list[HasilPrediksi]) -> None:
        """Simpan hasil tiap model ke tabel HASIL_PREDIKSI."""
        with _kunci_tulis:
            kon = _koneksi()
            with kon:  # commit otomatis, rollback kalau gagal
                kon.executemany(
                    "INSERT INTO HASIL_PREDIKSI (kondisi_id, model, kelas_prediksi, probabilitas) "
                    "VALUES (?, ?, ?, ?)",
                    [(kondisi_id, h.model, h.kelas, h.confidence) for h in hasil])
