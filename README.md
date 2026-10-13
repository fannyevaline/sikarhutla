# Dashboard Klasifikasi Tingkat Kerawanan Karhutla Kalimantan

Aplikasi web untuk mengklasifikasikan tingkat kerawanan kebakaran hutan dan lahan
di wilayah Kalimantan ke dalam tiga kategori — Rendah, Sedang, dan Tinggi — dengan
membandingkan algoritma **Random Forest** dan **XGBoost**.

Dibuat sebagai luaran skripsi:

> **Perbandingan Random Forest dan XGBoost untuk Klasifikasi Tingkat Kerawanan
> Kebakaran Hutan dan Lahan di Kalimantan Berbasis Data Titik Panas Satelit**
>
> Fanny Evaline S. — 535230203
> Program Studi Teknik Informatika, Fakultas Teknologi Informasi
> Universitas Tarumanagara

---

## Cara menjalankan

Butuh Python 3.11.

```bash
pip install -r requirements.txt
python database.py      # sekali saja: membentuk data/karhutla.db
streamlit run app.py
```

`data/karhutla.db` tidak disimpan di git. Berkas ini dibentuk dari
`data/dataset_final.csv` dan `data/grid_kalimantan.csv` oleh `database.py`.
Kalau `HASIL_PREDIKSI` sudah berisi riwayat klasifikasi, `database.py` menolak
berjalan supaya riwayat tidak terhapus tanpa sengaja. Untuk tetap membangun ulang,
matikan aplikasi lalu jalankan `python database.py --paksa`; basis data lama
disalin dulu ke `data/karhutla_cadangan_<waktu>.db`.

Aplikasi terbuka di `http://localhost:3000`.

Salin `.env.example` menjadi `.env` dan isi kunci API yang diperlukan untuk
pemanggilan data cuaca periode mendatang. Tanpa berkas itu, modul historis tetap
berjalan normal.

---

## Isi aplikasi

Empat halaman yang memuat sembilan modul fungsional sesuai rancangan pada Bab 3:

| Halaman        | Modul fungsional                                                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Beranda        | Beranda                                                                                                                                                                         |
| Klasifikasi    | Peta Interaktif Kerawanan · Pemilihan Wilayah dan Periode · Klasifikasi Kerawanan · Hasil Klasifikasi dan Confidence · Rincian Variabel Prediktor · Informasi Periode Mendatang |
| Performa Model | Perbandingan Performa Model                                                                                                                                                     |
| Bantuan        | Bantuan                                                                                                                                                                         |

---

## Struktur berkas

```
app.py                  titik masuk aplikasi Streamlit
database.py             membentuk data/karhutla.db dari berkas CSV
modul/                  satu berkas per halaman
domain/                 kelas sesuai class diagram (Gambar 3.8)
data/                   model pre-trained dan dataset
mockup/                 gambar rancangan antarmuka dari proposal
.streamlit/config.toml  tema tampilan
requirements.txt        daftar pustaka
```

Aplikasi hanya **memuat** model yang sudah dilatih sebelumnya dan memanggil
`predict()`. Tidak ada pelatihan model di dalam aplikasi ini. Seluruh pengolahan
data dan pelatihan dikerjakan pada proyek terpisah.

---

## Model dan data

| Berkas                                   | Keterangan                                           |
| ---------------------------------------- | ---------------------------------------------------- |
| `data/model/model_rf_final.pkl`          | Random Forest, `n_estimators=200`, `random_state=42` |
| `data/model/model_xgb_final.pkl`         | XGBoost, parameter disamakan                         |
| `data/model/feature_columns_encoded.pkl` | nama kolom setelah one-hot encoding                  |
| `data/model/perbandingan_smotenc.csv`    | hasil evaluasi kedua model                           |
| `data/dataset_final.csv`                 | 14.586 baris, 221 grid, Januari 2021 – Juni 2026     |
| `data/tertile_cutoff.json`               | ambang kelas: P33 = 3, P67 = 11 titik panas          |
| `data/grid_kalimantan.csv`               | 232 grid wilayah kajian berukuran 0,5° × 0,5°        |
| `data/grid_wilayah.csv`                  | provinsi & kabupaten (GADM v4.1) di titik pusat grid |
| `data/karhutla.db`                       | SQLite (tidak di git): GRID, KONDISI_BULANAN, HASIL_PREDIKSI |

Kedua model dilatih dengan data latih hasil SMOTENC, pembagian latih–uji
menggunakan `GroupShuffleSplit` 80:20 berdasarkan identitas grid.

### Kategori kerawanan

Ditentukan dari jumlah titik panas per grid dalam satu bulan:

| Kategori | Jumlah titik panas | Warna  |
| -------- | ------------------ | ------ |
| Rendah   | ≤ 3                | hijau  |
| Sedang   | 4 – 11             | kuning |
| Tinggi   | ≥ 12               | merah  |

### Sebelas variabel prediktor

Ketinggian, kemiringan lereng, curah hujan, suhu maksimum, kelembapan relatif,
kecepatan angin maksimum, hari kering berturut-turut, jarak ke badan air,
jarak ke jalan, tutupan lahan, dan status gambut.

---

## Sumber data

| Data                | Sumber                                             |
| ------------------- | -------------------------------------------------- |
| Titik panas         | NASA FIRMS (MODIS Terra & Aqua, VIIRS Suomi-NPP)   |
| Batas administratif | GADM versi 4.1                                     |
| Ketinggian          | Open-Meteo Elevation API (Copernicus DEM GLO-90)   |
| Cuaca historis      | Open-Meteo Archive API (reanalisis ECMWF ERA5)     |
| Ramalan cuaca       | Open-Meteo Forecast API, hingga 16 hari            |
| Tutupan lahan       | ESA WorldCover 10 m 2021 v200                      |
| Lahan gambut        | Peta Lahan Gambut Badan Informasi Geospasial (BIG) |
| Jalan dan perairan  | OpenStreetMap melalui Geofabrik                    |

Hari kering berturut-turut mengikuti definisi indeks Consecutive Dry Days (CDD)
dari ETCCDI, dengan ambang curah hujan harian di bawah 1 mm.
