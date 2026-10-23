"""Cuaca harian Open-Meteo untuk modul Informasi Periode Mendatang.

Dipakai oleh SumberDataService. Satu bulan penuh disusun dari tiga sumber, lalu
diagregasi persis seperti data pelatihan (ambil_meteorologi_v2.py di proyek
pengolahan data). Hari ke-d, dengan observasi tersedia sampai hari ke-t:
    d <= t           observasi, Archive API (t paling lambat kemarin)
    t < d <= t + 16  ramalan, Forecast API
    d > t + 16       rata-rata klimatologis tanggal yang sama, 2021-2026

Open-Meteo menghitung tiap lokasi sebagai satu panggilan (batas 600 per menit).
Supaya peta 221 grid tetap ringan, nilai arsip untuk tanggal yang sudah final
disimpan di .cache/cuaca_harian.csv dan tidak diminta ulang.
"""
import calendar
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PATH_CACHE = ROOT / ".cache/cuaca_harian.csv"

URL_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
URL_FORECAST = "https://api.open-meteo.com/v1/forecast"
VAR_HARIAN = ["precipitation_sum", "temperature_2m_max",
              "relative_humidity_2m_mean", "wind_speed_10m_max"]
# Dipatok sama dengan periode data pelatihan (Jan 2021 - Jun 2026) supaya baseline
# klimatologi setara dengan kondisi yang dipelajari model.
KLIMATOLOGI = (date(2021, 1, 1), date(2026, 6, 30))
JANGKAUAN_RAMALAN = 16  # hari
AMBANG_KERING_MM = 1.0

UKURAN_BATCH = 100      # lokasi per permintaan
TUNGGU_DETIK = 62       # jeda saat batas per menit tercapai
UMUR_FINAL = 7          # arsip yang lebih tua dari ini (hari) dianggap tidak berubah
UMUR_SEGAR = 3600       # detik; umur cache observasi terbaru dan ramalan

Lokasi = tuple[float, float]
Kabar = Callable[[str], None]
_kunci = threading.Lock()


class GagalAmbilCuaca(RuntimeError):
    """Open-Meteo tidak bisa dihubungi atau mengembalikan galat."""


def _diam(_: str) -> None:
    pass


# ---- permintaan ke Open-Meteo ----------------------------------------------------

def _minta(url: str, lokasi: list[Lokasi], awal: date, akhir: date,
           kabar: Kabar) -> dict[Lokasi, pd.DataFrame]:
    """Satu permintaan untuk beberapa lokasi; indeks tiap DataFrame = tanggal."""
    params = {"latitude": ",".join(str(la) for la, _ in lokasi),
              "longitude": ",".join(str(lo) for _, lo in lokasi),
              "start_date": str(awal), "end_date": str(akhir),
              "daily": ",".join(VAR_HARIAN), "timezone": "auto"}
    for _ in range(4):
        try:
            r = requests.get(url, params=params, timeout=120)
            data = r.json()
        except (requests.RequestException, ValueError) as e:
            raise GagalAmbilCuaca(f"tidak dapat menghubungi Open-Meteo ({e.__class__.__name__})")
        alasan = str(data.get("reason", "")) if isinstance(data, dict) else ""
        if r.status_code == 429 and "Minutely" in alasan:
            kabar(f"Batas permintaan per menit Open-Meteo tercapai, menunggu "
                  f"{TUNGGU_DETIK} detik...")
            time.sleep(TUNGGU_DETIK)
            continue
        if r.status_code != 200:
            raise GagalAmbilCuaca(alasan or f"HTTP {r.status_code}")
        daftar = data if isinstance(data, list) else [data]
        hasil = {}
        for loc, d in zip(lokasi, daftar):
            harian = pd.DataFrame(d["daily"])
            harian.index = pd.to_datetime(harian.pop("time")).dt.date
            hasil[loc] = harian[VAR_HARIAN].dropna()
        return hasil
    raise GagalAmbilCuaca("batas permintaan Open-Meteo masih tercapai, coba lagi nanti")


def _minta_banyak(url: str, lokasi: list[Lokasi], awal: date, akhir: date,
                  kabar: Kabar) -> dict[Lokasi, pd.DataFrame]:
    hasil = {}
    for i in range(0, len(lokasi), UKURAN_BATCH):
        kabar(f"Mengambil data Open-Meteo ({min(i + UKURAN_BATCH, len(lokasi))} dari "
              f"{len(lokasi)} lokasi)...")
        hasil.update(_minta(url, lokasi[i:i + UKURAN_BATCH], awal, akhir, kabar))
    return hasil


# ---- cache -----------------------------------------------------------------------

@st.cache_resource
def _gudang() -> dict[Lokasi, pd.DataFrame]:
    """Arsip harian yang sudah final, dimuat dari disk sekali per proses."""
    if not PATH_CACHE.exists():
        return {}
    df = pd.read_csv(PATH_CACHE)
    df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
    return {(la, lo): g.set_index("tanggal")[VAR_HARIAN]
            for (la, lo), g in df.groupby(["lat", "lon"])}


def _simpan_gudang(baru: dict[Lokasi, pd.DataFrame]) -> None:
    gudang = _gudang()
    for loc, df in baru.items():
        lama = gudang.get(loc)
        gabung = df if lama is None else pd.concat([lama, df])
        gudang[loc] = gabung[~gabung.index.duplicated(keep="last")].sort_index()
    semua = pd.concat(
        [df.rename_axis("tanggal").reset_index().assign(lat=la, lon=lo)
         for (la, lo), df in gudang.items()], ignore_index=True)
    PATH_CACHE.parent.mkdir(exist_ok=True)
    semua[["lat", "lon", "tanggal", *VAR_HARIAN]].to_csv(PATH_CACHE, index=False)


@st.cache_resource
def _segar() -> dict:
    """Cache singkat di memori: kunci -> (waktu, nilai)."""
    return {}


def ingat(kunci, fungsi: Callable):
    """Nilai fungsi() untuk kunci, diingat selama UMUR_SEGAR detik."""
    simpanan = _segar()
    with _kunci:
        ada = simpanan.get(kunci)
    if ada and time.time() - ada[0] < UMUR_SEGAR:
        return ada[1]
    nilai = fungsi()
    with _kunci:
        simpanan[kunci] = (time.time(), nilai)
    return nilai


# ---- sumber data -----------------------------------------------------------------

def arsip(lokasi: list[Lokasi], awal: date, akhir: date, hari_ini: date,
          kabar: Kabar = _diam) -> dict[Lokasi, pd.DataFrame]:
    """Observasi Archive API. Tanggal yang sudah final diambil dari / disimpan ke
    cache disk; tanggal terbaru diminta ulang paling lama tiap jam."""
    hasil = {loc: [] for loc in lokasi}
    batas_final = hari_ini - timedelta(days=UMUR_FINAL)

    if awal <= batas_final:
        a, b = awal, min(akhir, batas_final)
        perlu_hari = (b - a).days + 1
        with _kunci:
            gudang = _gudang()
            kurang = [loc for loc in lokasi
                      if loc not in gudang or len(gudang[loc].loc[a:b]) < perlu_hari]
        if kurang:
            baru = _minta_banyak(URL_ARCHIVE, kurang, a, b, kabar)
            with _kunci:
                _simpan_gudang(baru)
        with _kunci:
            for loc in lokasi:
                if loc in _gudang():
                    hasil[loc].append(_gudang()[loc].loc[a:b])

    if akhir > batas_final:
        a = max(awal, batas_final + timedelta(days=1))
        terbaru = ingat(("arsip", tuple(lokasi), a, akhir),
                         lambda: _minta_banyak(URL_ARCHIVE, lokasi, a, akhir, kabar))
        for loc in lokasi:
            hasil[loc].append(terbaru[loc])

    kosong = pd.DataFrame(columns=VAR_HARIAN)
    return {loc: pd.concat(bagian) if bagian else kosong for loc, bagian in hasil.items()}


def ramalan(lokasi: list[Lokasi], awal: date, akhir: date,
            kabar: Kabar = _diam) -> dict[Lokasi, pd.DataFrame]:
    return ingat(("ramalan", tuple(lokasi), awal, akhir),
                  lambda: _minta_banyak(URL_FORECAST, lokasi, awal, akhir, kabar))


def klimatologi(lokasi: list[Lokasi], tanggal: list[tuple[int, int]], hari_ini: date,
                kabar: Kabar = _diam) -> dict[Lokasi, pd.DataFrame]:
    """Rata-rata tiap tanggal kalender (bulan, hari) selama rentang dataset.
    Diminta per tahun hanya untuk tanggal yang diperlukan, lewat cache arsip."""
    per_lokasi = {loc: [] for loc in lokasi}
    for tahun in range(KLIMATOLOGI[0].year, KLIMATOLOGI[1].year + 1):
        tgl = [date(tahun, b, h) for b, h in tanggal
               if h <= calendar.monthrange(tahun, b)[1]
               and KLIMATOLOGI[0] <= date(tahun, b, h) <= KLIMATOLOGI[1]]
        if not tgl:
            continue
        kabar(f"Menyusun rata-rata klimatologis tahun {tahun}...")
        data = arsip(lokasi, min(tgl), max(tgl), hari_ini, kabar)
        for loc in lokasi:
            per_lokasi[loc].append(data[loc].loc[[d for d in tgl if d in data[loc].index]])
    hasil = {}
    for loc, bagian in per_lokasi.items():
        df = pd.concat(bagian)
        tanggal_ = pd.to_datetime(pd.Series(df.index, index=df.index))
        hasil[loc] = df.groupby([tanggal_.dt.month, tanggal_.dt.day]).mean()
    return hasil


# ---- penyusunan satu bulan penuh -------------------------------------------------

def hari_kering_beruntun(hujan: pd.Series, ambang_mm: float = AMBANG_KERING_MM) -> int:
    """Hari kering (hujan < 1 mm) berturut-turut terpanjang; sama dengan pelatihan."""
    maks = run = 0
    for kering in hujan < ambang_mm:
        run = run + 1 if kering else 0
        maks = max(maks, run)
    return maks


def agregasi(harian: pd.DataFrame) -> dict:
    """Deret harian satu bulan -> lima variabel bulanan, sama dengan pelatihan."""
    return {
        "curah_hujan_mm": float(harian["precipitation_sum"].sum()),
        "suhu_maks_c": float(harian["temperature_2m_max"].mean()),
        "kelembapan_persen": float(harian["relative_humidity_2m_mean"].mean()),
        "angin_maks_kmh": float(harian["wind_speed_10m_max"].mean()),
        "hari_kering_maks": hari_kering_beruntun(harian["precipitation_sum"]),
    }


def susun_bulan(lokasi: list[Lokasi], tahun_bulan: str, hari_ini: date,
                kabar: Kabar = _diam) -> pd.DataFrame:
    """Lima variabel cuaca bulanan untuk tiap lokasi, beserta jumlah hari dari tiap
    sumber. Baris = lokasi (indeks lat, lon)."""
    tahun, bulan = map(int, tahun_bulan.split("-"))
    awal = date(tahun, bulan, 1)
    akhir = date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    kemarin = hari_ini - timedelta(days=1)
    satu = timedelta(days=1)

    # Hari ini belum selesai, jadi observasi paling lambat sampai kemarin.
    obs = (arsip(lokasi, awal, min(akhir, kemarin), hari_ini, kabar) if awal <= kemarin
           else {loc: pd.DataFrame(columns=VAR_HARIAN) for loc in lokasi})
    t = {}  # hari observasi terakhir yang bersambung sejak tanggal 1
    for loc in lokasi:
        t[loc] = awal - satu
        while t[loc] + satu in obs[loc].index:
            t[loc] += satu

    batas_api = min(akhir, hari_ini + timedelta(days=JANGKAUAN_RAMALAN - 1))
    batas = {loc: min(batas_api, t[loc] + timedelta(days=JANGKAUAN_RAMALAN)) for loc in lokasi}
    perlu_ram = [loc for loc in lokasi if t[loc] < batas[loc]]
    ram = {}
    if perlu_ram:
        mulai = max(awal, min(t[loc] for loc in perlu_ram) + satu)
        ram = ramalan(perlu_ram, mulai, max(batas[loc] for loc in perlu_ram), kabar)

    asal = {}
    for loc in lokasi:
        asal[loc] = []
        for d in pd.date_range(awal, akhir).date:
            if d <= t[loc]:
                asal[loc].append("observasi")
            elif d <= batas[loc] and loc in ram and d in ram[loc].index:
                asal[loc].append("ramalan")
            else:
                asal[loc].append("klimatologi")

    hari_klim = sorted({(d.month, d.day) for loc in lokasi
                        for d, a in zip(pd.date_range(awal, akhir).date, asal[loc])
                        if a == "klimatologi"})
    perlu_klim = [loc for loc in lokasi if "klimatologi" in asal[loc]]
    klim = klimatologi(perlu_klim, hari_klim, hari_ini, kabar) if perlu_klim else {}

    baris = []
    for loc in lokasi:
        deret = []
        for d, a in zip(pd.date_range(awal, akhir).date, asal[loc]):
            sumber = {"observasi": obs, "ramalan": ram}.get(a)
            deret.append(sumber[loc].loc[d] if sumber else klim[loc].loc[(d.month, d.day)])
        harian = pd.DataFrame(deret, columns=VAR_HARIAN).reset_index(drop=True)
        baris.append({"lat": loc[0], "lon": loc[1], **agregasi(harian),
                      "hari_observasi": asal[loc].count("observasi"),
                      "hari_ramalan": asal[loc].count("ramalan"),
                      "hari_klimatologi": asal[loc].count("klimatologi")})
    return pd.DataFrame(baris).set_index(["lat", "lon"])
