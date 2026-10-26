"""
Membentuk basis data SQLite sesuai ERD pada Gambar 3.7 laporan.

Dijalankan SEKALI dari folder aplikasi:
    python scripts/buat_database.py

Membaca  : data/dataset_final.csv, data/grid_kalimantan.csv,
           data/dataset_eksternal_final.csv (Juli-September 2026, pengujian eksternal)
Menghasil: data/karhutla.db  berisi tiga tabel

    GRID            -- data statis per grid wilayah
    KONDISI_BULANAN -- data dinamis per grid-bulan
    HASIL_PREDIKSI  -- hasil klasifikasi per model (diisi oleh aplikasi)

Script ini TIDAK mengubah berkas CSV mana pun dan TIDAK menyentuh model.
Menjalankannya ulang akan membangun ulang ketiga tabel dari awal.

GRID dan ada_di_dataset hanya dibentuk dari dataset_final.csv. Data eksternal hanya
menambah baris KONDISI_BULANAN untuk grid yang ada di dataset; kelasnya dipakai apa
adanya (sudah dilabeli dengan ambang dataset utama, P33 = 3, P67 = 11).

Pengaman: kalau HASIL_PREDIKSI sudah berisi riwayat klasifikasi, script menolak
berjalan. Untuk tetap membangun ulang, jalankan:
    python scripts/buat_database.py --paksa
Basis data lama lebih dulu disalin ke data/karhutla_cadangan_<waktu>.db.
"""
import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent  # folder aplikasi
PATH_DATASET = ROOT / "data" / "dataset_final.csv"
PATH_GRID = ROOT / "data" / "grid_kalimantan.csv"
PATH_EKSTERNAL = ROOT / "data" / "dataset_eksternal_final.csv"
PATH_DB = ROOT / "data" / "karhutla.db"

# Kolom statis: nilainya tetap untuk satu grid, tidak berubah tiap bulan
KOLOM_STATIS = [
    "ketinggian_meter", "kemiringan_lereng", "jarak_air_meter",
    "jarak_jalan_meter", "kode_worldcover", "tutupan_lahan", "gambut",
]
# Kolom dinamis: berubah tiap bulan
KOLOM_DINAMIS = [
    "curah_hujan_mm", "suhu_maks_c", "kelembapan_persen",
    "angin_maks_kmh", "hari_kering_maks", "jumlah_hotspot", "kerawanan",
]

SKEMA = """
DROP TABLE IF EXISTS HASIL_PREDIKSI;
DROP TABLE IF EXISTS KONDISI_BULANAN;
DROP TABLE IF EXISTS GRID;

CREATE TABLE GRID (
    grid_id           TEXT    PRIMARY KEY,
    grid_lat          REAL    NOT NULL,
    grid_lon          REAL    NOT NULL,
    ketinggian_meter  REAL,
    kemiringan_lereng REAL,
    jarak_air_meter   REAL,
    jarak_jalan_meter REAL,
    kode_worldcover   INTEGER,
    tutupan_lahan     TEXT,
    gambut            TEXT,
    ada_di_dataset    INTEGER NOT NULL
);

CREATE TABLE KONDISI_BULANAN (
    kondisi_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    grid_id           TEXT    NOT NULL,
    tahun_bulan       TEXT    NOT NULL,
    curah_hujan_mm    REAL,
    suhu_maks_c       REAL,
    kelembapan_persen REAL,
    angin_maks_kmh    REAL,
    hari_kering_maks  INTEGER,
    jumlah_hotspot    INTEGER,
    kerawanan         TEXT,
    UNIQUE (grid_id, tahun_bulan),
    FOREIGN KEY (grid_id) REFERENCES GRID (grid_id)
);

CREATE TABLE HASIL_PREDIKSI (
    prediksi_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    kondisi_id     INTEGER NOT NULL,
    model          TEXT    NOT NULL,
    kelas_prediksi TEXT    NOT NULL,
    probabilitas   REAL    NOT NULL,
    waktu          TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (kondisi_id) REFERENCES KONDISI_BULANAN (kondisi_id)
);

CREATE INDEX idx_kondisi_periode ON KONDISI_BULANAN (tahun_bulan);
CREATE INDEX idx_kondisi_grid    ON KONDISI_BULANAN (grid_id);
CREATE INDEX idx_prediksi_kondisi ON HASIL_PREDIKSI (kondisi_id);
"""


def buat_grid_id(lat, lon) -> str:
    """Penanda grid, sama dengan yang dipakai saat pelatihan model."""
    return f"{round(float(lat), 2)}_{round(float(lon), 2)}"


def jumlah_hasil_tersimpan() -> int:
    """Banyak baris di HASIL_PREDIKSI pada basis data yang sudah ada (0 kalau belum ada)."""
    if not PATH_DB.exists():
        return 0
    kon = sqlite3.connect(f"file:{PATH_DB}?mode=ro", uri=True)
    try:
        return kon.execute("SELECT COUNT(*) FROM HASIL_PREDIKSI").fetchone()[0]
    except sqlite3.OperationalError:  # tabel belum ada
        return 0
    finally:
        kon.close()


def amankan_riwayat(paksa: bool) -> None:
    """Hentikan script kalau ada riwayat klasifikasi, kecuali --paksa (dengan cadangan)."""
    n = jumlah_hasil_tersimpan()
    if n == 0:
        return
    if not paksa:
        print(f"DIBATALKAN: HASIL_PREDIKSI berisi {n:,} riwayat klasifikasi yang akan "
              f"terhapus kalau basis data dibangun ulang.\n"
              f"Tidak ada yang diubah. Untuk tetap membangun ulang (riwayat disalin "
              f"dulu ke cadangan), jalankan:\n    python scripts/buat_database.py --paksa")
        sys.exit(1)
    cadangan = PATH_DB.with_name(f"karhutla_cadangan_{datetime.now():%Y%m%d_%H%M%S}.db")
    shutil.copy2(PATH_DB, cadangan)
    print(f"Cadangan dibuat: {cadangan.relative_to(ROOT)} ({n:,} riwayat klasifikasi)")


def main(paksa: bool = False) -> None:
    amankan_riwayat(paksa)

    print("Membaca berkas sumber...")
    df = pd.read_csv(PATH_DATASET)
    grid_resmi = pd.read_csv(PATH_GRID)
    eksternal = pd.read_csv(PATH_EKSTERNAL)
    print(f"  dataset_final.csv          : {len(df):,} baris")
    print(f"  grid_kalimantan.csv        : {len(grid_resmi):,} grid")
    print(f"  dataset_eksternal_final.csv: {len(eksternal):,} baris")

    df["grid_id"] = [buat_grid_id(a, b) for a, b in zip(df.grid_lat, df.grid_lon)]
    eksternal["grid_id"] = [buat_grid_id(a, b)
                            for a, b in zip(eksternal.grid_lat, eksternal.grid_lon)]
    grid_resmi["grid_id"] = [buat_grid_id(a, b)
                             for a, b in zip(grid_resmi.grid_lat, grid_resmi.grid_lon)]

    # --- periksa bahwa kolom statis memang tetap untuk tiap grid ---
    jml_nilai = df.groupby("grid_id")[KOLOM_STATIS].nunique()
    tidak_tetap = jml_nilai[(jml_nilai > 1).any(axis=1)]
    if len(tidak_tetap):
        print(f"\n  PERINGATAN: {len(tidak_tetap)} grid punya nilai statis yang berubah "
              f"antar bulan. Diambil nilai barisnya yang pertama.")
    else:
        print("  Kolom statis konsisten untuk setiap grid. OK")

    # --- GRID: seluruh 232 grid resmi, atribut diisi untuk yang ada di dataset ---
    statis = (df.sort_values("tahun_bulan")
                .groupby("grid_id", as_index=False)[KOLOM_STATIS].first())
    tabel_grid = grid_resmi[["grid_id", "grid_lat", "grid_lon"]].merge(
        statis, on="grid_id", how="left")
    tabel_grid["ada_di_dataset"] = tabel_grid["ketinggian_meter"].notna().astype(int)

    # --- data eksternal: hanya grid yang ada di dataset, statisnya harus sama ---
    grid_dataset = set(tabel_grid.loc[tabel_grid.ada_di_dataset == 1, "grid_id"])
    dibuang = eksternal[~eksternal.grid_id.isin(grid_dataset)]
    eksternal = eksternal[eksternal.grid_id.isin(grid_dataset)]
    print(f"\n  Data eksternal: {len(eksternal):,} baris dipakai, {len(dibuang)} baris dari "
          f"{dibuang.grid_id.nunique()} grid tanpa data dibuang")
    acuan = statis.set_index("grid_id").loc[eksternal.grid_id, KOLOM_STATIS]
    beda = pd.Series(False, index=eksternal.index)
    for k in KOLOM_STATIS:
        a, b = eksternal[k].to_numpy(), acuan[k].to_numpy()
        if pd.api.types.is_numeric_dtype(eksternal[k]):
            beda |= ~np.isclose(a.astype(float), b.astype(float), equal_nan=True)
        else:
            beda |= a != b
    if beda.any():
        print(f"GAGAL: {beda.sum()} baris eksternal punya nilai statis yang "
              f"berbeda dari dataset_final.csv. Tidak ada yang diubah.")
        sys.exit(1)

    # --- KONDISI_BULANAN ---
    kolom = ["grid_id", "tahun_bulan"] + KOLOM_DINAMIS
    tabel_kondisi = pd.concat([df[kolom], eksternal[kolom]], ignore_index=True)
    ganda = tabel_kondisi.duplicated(["grid_id", "tahun_bulan"]).sum()
    if ganda:
        print(f"GAGAL: {ganda} pasangan grid-bulan muncul di kedua berkas. "
              f"Tidak ada yang diubah.")
        sys.exit(1)

    # --- tulis ke SQLite ---
    try:
        PATH_DB.unlink(missing_ok=True)
    except PermissionError:
        print(f"GAGAL: {PATH_DB.relative_to(ROOT)} sedang dipakai program lain "
              f"(biasanya aplikasi Streamlit). Matikan aplikasinya dulu, lalu ulangi.\n"
              f"Tidak ada yang diubah.")
        sys.exit(1)
    with sqlite3.connect(PATH_DB) as kon:
        kon.executescript(SKEMA)
        kon.execute("PRAGMA foreign_keys = ON")
        tabel_grid.to_sql("GRID", kon, if_exists="append", index=False)
        tabel_kondisi.to_sql("KONDISI_BULANAN", kon, if_exists="append", index=False)
        kon.commit()

        print(f"\nTersimpan: {PATH_DB.relative_to(ROOT)}")
        print("\nIsi basis data:")
        for tabel in ("GRID", "KONDISI_BULANAN", "HASIL_PREDIKSI"):
            n = kon.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]
            print(f"  {tabel:<16}: {n:>6,} baris")

        n_pakai = kon.execute(
            "SELECT COUNT(*) FROM GRID WHERE ada_di_dataset = 1").fetchone()[0]
        n_kosong = kon.execute(
            "SELECT COUNT(*) FROM GRID WHERE ada_di_dataset = 0").fetchone()[0]
        print(f"\n  Grid dengan data   : {n_pakai}")
        print(f"  Grid tanpa data    : {n_kosong}  (dikeluarkan saat penyaringan)")

        print("\nContoh gabungan GRID + KONDISI_BULANAN:")
        contoh = kon.execute("""
            SELECT g.grid_lat, g.grid_lon, k.tahun_bulan,
                   k.curah_hujan_mm, k.jumlah_hotspot, k.kerawanan
            FROM   KONDISI_BULANAN k
            JOIN   GRID g ON g.grid_id = k.grid_id
            ORDER  BY k.tahun_bulan DESC, k.jumlah_hotspot DESC
            LIMIT  5
        """).fetchall()
        print("  lat     lon      periode   hujan   hotspot  kerawanan")
        for b in contoh:
            print(f"  {b[0]:<7} {b[1]:<8} {b[2]}  {b[3]:>6}  {b[4]:>7}  {b[5]}")

        print("\nSebaran kelas pada periode terakhir:")
        periode = kon.execute(
            "SELECT MAX(tahun_bulan) FROM KONDISI_BULANAN").fetchone()[0]
        for kelas, n in kon.execute(
                "SELECT kerawanan, COUNT(*) FROM KONDISI_BULANAN "
                "WHERE tahun_bulan = ? GROUP BY kerawanan", (periode,)):
            print(f"  {periode}  {kelas:<7}: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bentuk data/karhutla.db dari berkas CSV.")
    parser.add_argument("--paksa", action="store_true",
                        help="bangun ulang walau HASIL_PREDIKSI berisi riwayat "
                             "(riwayat disalin ke cadangan lebih dulu)")
    main(parser.parse_args().paksa)