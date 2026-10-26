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
python scripts/buat_database.py   # sekali saja: membentuk data/karhutla.db
streamlit run app.py
```

`data/karhutla.db` tidak disimpan di git. Berkas ini dibentuk dari
`data/dataset_final.csv`, `data/grid_kalimantan.csv`, dan `data/dataset_eksternal_final.csv`
oleh `scripts/buat_database.py`. Data eksternal (Juli–September 2026) hanya menambah baris
KONDISI_BULANAN untuk 221 grid yang ada di dataset, dengan kelas apa adanya.
Kalau `HASIL_PREDIKSI` sudah berisi riwayat klasifikasi, skrip itu menolak
berjalan supaya riwayat tidak terhapus tanpa sengaja. Untuk tetap membangun ulang,
matikan aplikasi lalu jalankan `python scripts/buat_database.py --paksa`; basis data lama
disalin dulu ke `data/karhutla_cadangan_<waktu>.db`.

Aplikasi terbuka di `http://localhost:8501`.

Aplikasi tidak memerlukan API key. Data cuaca bulan mendatang diambil dari
Open-Meteo, yang terbuka tanpa kunci; tanpa koneksi internet, bulan historis tetap
berjalan normal.

---

## Isi aplikasi

Lima halaman yang memuat sepuluh modul fungsional sesuai rancangan pada Bab 3
(halaman Simulasi ditambahkan atas permintaan dosen pembimbing):

| Halaman        | Modul fungsional                                                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Beranda        | Beranda                                                                                                                                                                         |
| Klasifikasi    | Peta Interaktif Kerawanan · Pemilihan Wilayah dan Periode · Klasifikasi Kerawanan · Hasil Klasifikasi dan Confidence · Rincian Variabel Prediktor · Informasi Periode Mendatang |
| Simulasi       | Simulasi (isi sendiri sebelas variabel, lihat hasil kedua model)                                                                                                                |
| Performa Model | Perbandingan Performa Model                                                                                                                                                     |
| Bantuan        | Bantuan                                                                                                                                                                         |

-------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Beranda        | Beranda                                                                                                                                                                         |
| Klasifikasi    | Peta Interaktif Kerawanan · Pemilihan Wilayah dan Periode · Klasifikasi Kerawanan · Hasil Klasifikasi dan Confidence · Rincian Variabel Prediktor · Informasi Periode Mendatang |
| Performa Model | Perbandingan Performa Model                                                                                                                                                     |
| Bantuan        | Bantuan                                                                                                                                                                         |

---

## Struktur berkas

Satu aplikasi Streamlit (monolitik), dibagi tiga lapisan supaya mudah dipelajari:

```
app.py                      titik masuk: pasang CSS, gambar sidebar, panggil halaman

domain/                     BACKEND - data, model, cuaca (tanpa HTML/CSS)
  konstanta.py              kelas, sebelas fitur, ukuran grid, lokasi berkas data
  grid.py                   Grid, KondisiBulanan, HasilPrediksi (class diagram)
  model_klasifikasi.py      ModelKlasifikasi, RandomForestModel, XGBoostModel
  modul_klasifikasi.py      ModulKlasifikasi: orkestrator kedua model
  sumber_data_service.py    SumberDataService: query SQLite, simpan hasil
  open_meteo.py             cuaca harian Open-Meteo untuk bulan di luar basis data

modul/                      TAMPILAN - satu berkas per modul fungsional
  tampilan.py               warna kelas, nama bulan, format angka, gaya grafik
  beranda.py                Modul 1
  klasifikasi.py            Modul 3-5, merangkai peta, rincian, dan periode mendatang
  peta.py                   Modul 2
  rincian_variabel.py       Modul 6
  periode_mendatang.py      Modul 7
  simulasi.py               Modul 10

assets/css/                 GAYA - satu berkas CSS per halaman/modul
  global.css                tata letak, kartu, sidebar
  komponen.css              komponen bersama Klasifikasi & Simulasi
  beranda.css, klasifikasi.css, peta.css, rincian_variabel.css,
  periode_mendatang.css, simulasi.css

scripts/buat_database.py    membentuk data/karhutla.db dari berkas CSV
data/                       model pre-trained dan dataset
mockup/                     gambar rancangan antarmuka dari proposal
.streamlit/config.toml      tema tampilan
requirements.txt            daftar pustaka
```

Arah ketergantungan: `app.py` → `modul/` → `domain/`. Berkas di `domain/` tidak
pernah mengimpor `modul/`.

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
| `data/dataset_eksternal_final.csv`       | 696 baris, 232 grid, Juli – September 2026 (pengujian eksternal; 663 baris masuk basis data) |
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
