"""Halaman Klasifikasi: modul 2-7 dalam satu alur dari atas ke bawah.

2. Peta interaktif kerawanan        (modul/peta.py)
3. Pemilihan wilayah dan periode
4. Klasifikasi kerawanan            (hanya saat tombol Jalankan klasifikasi ditekan)
5. Hasil klasifikasi dan confidence
6. Rincian variabel prediktor       (modul/rincian_variabel.py)
7. Informasi periode mendatang      (modul/periode_mendatang.py)
"""
import streamlit as st

from domain.grid import Grid, HasilPrediksi, nama_wilayah
from domain.konstanta import KELAS
from domain.modul_klasifikasi import ModulKlasifikasi
from domain.open_meteo import GagalAmbilCuaca
from domain.sumber_data_service import SumberDataService
from modul import peta, periode_mendatang, rincian_variabel
from modul.tampilan import BULAN, WARNA, WARNA_LATAR, WARNA_TEKS, angka, nama_periode

STATUS = {  # label chip, warna teks, warna latar
    "historis": ("Tercatat", "#137a3f", "#dcf3e5"),
    "selesai": ("Di luar basis data", "#6f6760", "#efe9e2"),
    "berjalan": ("Bulan berjalan", "#b8460b", "#ffe8d6"),
    "mendatang": ("Bulan mendatang", "#7048e8", "#ece6ff"),
}
AKHIRAN_BULAN = {"historis": "", "selesai": " · di luar basis data",
                 "berjalan": " · berjalan", "mendatang": " · mendatang"}


def _label_grid(baris) -> str:
    """Teks dropdown wilayah; koordinat selalu ikut supaya grid sekabupaten bisa dibedakan."""
    nama = nama_wilayah(baris.kabupaten, baris.provinsi, baris.grid_lat, baris.grid_lon)
    if isinstance(baris.kabupaten, str):
        return f"{nama}  ·  {_koordinat(baris.grid_lat, baris.grid_lon, 2)}"
    return nama


def _koordinat(lat: float, lon: float, desimal: int) -> str:
    """Lintang dan bujur dengan koma desimal; titik koma sebagai pemisah supaya tidak
    tertukar dengan koma desimalnya, misalnya "0,75; 108,75"."""
    return f"{angka(lat, desimal)}; {angka(lon, desimal)}"


# ---- 3. Pemilihan wilayah dan periode ---------------------------------------------

def _pilih_koordinat(sumber: SumberDataService, lat: float, lon: float, asal: str) -> None:
    """Ubah pilihan grid dari koordinat (klik peta atau masukan manual). Pesannya
    ditampilkan sebagai toast pada render berikutnya."""
    grid_id, ada = sumber.cari_grid(lat, lon)
    lokasi = _koordinat(lat, lon, 3)
    if grid_id is None:
        st.session_state.kl_pesan = (f"{asal} {lokasi} berada di luar 232 grid wilayah "
                                     "kajian.", ":material/wrong_location:")
    elif not ada:
        st.session_state.kl_pesan = (f"Grid {grid_id} tidak memiliki data, jadi tidak bisa "
                                     "diklasifikasi.", ":material/block:")
    elif asal == "Koordinat":  # klik peta sudah terlihat dari bingkai, tidak perlu toast
        st.session_state.kl_grid = grid_id
        st.session_state.kl_pesan = (f"Koordinat {lokasi} berada di grid {grid_id}.",
                                     ":material/check_circle:")
    else:
        st.session_state.kl_grid = grid_id


def _pakai_koordinat(sumber: SumberDataService) -> None:
    """Callback tombol pada popover koordinat manual."""
    _pilih_koordinat(sumber, st.session_state.kl_lat, st.session_state.kl_lon, "Koordinat")


def _periode_aktif(sumber: SumberDataService, daftar: list[str]) -> str:
    """Rapikan pilihan tahun/bulan di session_state sebelum widgetnya dibuat, supaya
    peta (yang digambar lebih dulu) memakai periode yang sama dengan dropdown.
    Pertama kali dibuka: periode tercatat terakhir, sama dengan Beranda."""
    if "kl_tahun" not in st.session_state:
        terakhir = sumber.periode_terakhir()
        st.session_state.kl_tahun, st.session_state.kl_bulan = int(terakhir[:4]), int(terakhir[5:])
    tahun_ada = sorted({int(p[:4]) for p in daftar})
    if st.session_state.kl_tahun not in tahun_ada:
        st.session_state.kl_tahun = tahun_ada[-1]
    bulan_ada = [int(p[5:]) for p in daftar if p.startswith(str(st.session_state.kl_tahun))]
    if st.session_state.get("kl_bulan") not in bulan_ada:
        st.session_state.kl_bulan = bulan_ada[-1]
    return f"{st.session_state.kl_tahun}-{st.session_state.kl_bulan:02d}"


def _render_pilihan(sumber: SumberDataService, label: dict, daftar: list[str]) -> None:
    st.markdown('<div class="kl-h2">Wilayah dan periode</div>', unsafe_allow_html=True)
    st.selectbox("Wilayah", list(label), key="kl_grid", format_func=label.get,
                 help="Klik grid pada peta, atau ketik nama kabupaten untuk mencari. "
                      "Hanya 221 grid yang memiliki data yang dapat dipilih.")
    with st.popover("atau masukkan koordinat", icon=":material/my_location:",
                    type="tertiary"):
        st.markdown('<div class="kl-kecil">Grid yang memuat titik ini akan dipilih.</div>',
                    unsafe_allow_html=True)
        st.number_input("Lintang", -5.0, 5.0, 0.0, 0.01, format="%.3f", key="kl_lat")
        st.number_input("Bujur", 108.0, 120.0, 114.0, 0.01, format="%.3f", key="kl_lon")
        st.button("Pilih grid", icon=":material/check:", width="stretch",
                  on_click=_pakai_koordinat, args=(sumber,))

    tahun = st.session_state.kl_tahun
    a, b = st.columns([1, 1.6], gap="small")
    a.selectbox("Tahun", sorted({int(p[:4]) for p in daftar}), key="kl_tahun")
    b.selectbox("Bulan", [int(p[5:]) for p in daftar if p.startswith(str(tahun))],
                key="kl_bulan",
                format_func=lambda m: BULAN[m - 1] + AKHIRAN_BULAN[
                    sumber.status_periode(f"{tahun}-{m:02d}")])


# ---- 4. Klasifikasi (tombol) ----------------------------------------------------

def _prediksi_peta(sumber: SumberDataService, periode: str, status: str):
    """Prediksi kedua model untuk semua grid, hanya untuk bulan di luar basis data,
    supaya peta langsung berwarna saat bulannya dipilih. Tidak disimpan ke
    HASIL_PREDIKSI. Pertama kali sebuah bulan dibuka perlu waktu (data cuaca 221
    grid dari Open-Meteo); sesudahnya diambil dari cache. None kalau Open-Meteo gagal."""
    if status == "historis":
        return None
    kabar = st.empty()
    try:
        with st.spinner(f"Menyusun cuaca dan menghitung prediksi kedua model untuk 221 grid "
                        f"({nama_periode(periode)}). Pertama kali dibuka bisa beberapa "
                        "menit, mohon tunggu..."):
            prediksi = ModulKlasifikasi(sumber).klasifikasi_bulan(
                periode, kabar=lambda teks: kabar.caption(teks))
    except GagalAmbilCuaca as e:
        kabar.warning(f"Peta belum bisa diwarnai: data cuaca gagal diambil ({e}).",
                      icon=":material/cloud_off:")
        return None
    kabar.empty()
    return prediksi


def _minta_jalankan() -> None:
    """Callback tombol; modelnya dijalankan di render()."""
    st.session_state.kl_jalankan = True


def _jalankan(sumber: SumberDataService, grid_id: str, periode: str, status: str) -> None:
    """Jalankan kedua model untuk grid dan periode terpilih; hanya dipanggil saat
    tombol ditekan. Periode di basis data disimpan ke HASIL_PREDIKSI.
    Hasilnya bertahan di kl_hasil sampai tombol ditekan lagi."""
    hasil = {"grid_id": grid_id, "periode": periode, "status": status,
             "grid": None, "galat": None}
    teks = ("Menjalankan Random Forest dan XGBoost..." if status == "historis"
            else "Menyusun cuaca dari Open-Meteo dan menjalankan kedua model...")
    try:
        with st.spinner(teks):
            hasil["grid"] = ModulKlasifikasi(sumber).klasifikasi(grid_id, periode)
    except GagalAmbilCuaca as e:
        hasil["galat"] = str(e)
    st.session_state.kl_hasil = hasil


# ---- 5. Hasil klasifikasi dan confidence ------------------------------------------

def _html_hasil(h: HasilPrediksi) -> str:
    sebaran = "".join(f'<div style="flex:{h.probabilitas[k]:.4f};background:{WARNA[k]}"></div>'
                      for k in KELAS if h.probabilitas[k] > 0)
    ket = "".join(f'<span><i style="background:{WARNA[k]}"></i>{k} {h.probabilitas[k]:.0%}</span>'
                  for k in KELAS)
    return (
        f'<div class="kl-hasil" style="background:{WARNA_LATAR[h.kelas]};'
        f'border-color:{WARNA[h.kelas]}">'
        f'<div class="kl-hasil-atas"><div><div class="kl-model">{h.model}</div>'
        f'<div class="kl-kelas" style="color:{WARNA_TEKS[h.kelas]}">{h.kelas}</div></div>'
        f'<div class="kl-conf" style="color:{WARNA_TEKS[h.kelas]}"><small>Confidence</small>'
        f'<b>{angka(h.confidence * 100, 1)}%</b></div></div>'
        f'<div class="kl-sebaran">{sebaran}</div>'
        f'<div class="kl-sebaran-ket">{ket}</div></div>'
    )


def _html_ringkas(grid: Grid) -> str:
    k = grid.kondisi[0]
    rf, xgb = k.hasil
    baris = [("Kesepakatan model", "Sepakat" if rf.kelas == xgb.kelas else "Berbeda")]
    if k.kerawanan is not None:
        tepat = [h.model for h in k.hasil if h.kelas == k.kerawanan]
        baris.append(("Kategori tercatat",
                      f'<span class="kl-titik" style="background:{WARNA[k.kerawanan]}"></span>'
                      f'{k.kerawanan}, {k.jumlah_hotspot} titik panas'))
        baris.append(("Model yang sesuai", " dan ".join(tepat) if tepat else "Tidak ada"))
    else:
        baris.append(("Kategori tercatat", "Belum ada"))
        baris.append(("Disimpan ke riwayat", "Tidak"))
    isi = "".join(f"<div><span>{a}</span><b>{b}</b></div>" for a, b in baris)
    return f'<div class="kl-ringkas">{isi}</div>'


def _render_hasil(label: dict, grid_id: str, periode: str) -> dict | None:
    """Tampilkan hasil tombol terakhir. Hasil tetap bertahan walau pilihan sudah
    berubah, dengan catatan bahwa itu hasil pilihan sebelumnya."""
    hasil = st.session_state.get("kl_hasil")
    if hasil is None:
        st.markdown('<div class="kl-garis"></div><div class="kl-kosong">'
                    '<div class="kl-kosong-judul">Belum ada hasil</div>Pilih wilayah dan '
                    'periode, lalu tekan <b>Jalankan klasifikasi</b>.</div>',
                    unsafe_allow_html=True)
        return None
    chip, teks, latar = STATUS[hasil["status"]]
    st.markdown(
        '<div class="kl-garis"></div><div class="kl-kepala">'
        f'<div class="kl-h2">Hasil · {nama_periode(hasil["periode"])}</div>'
        f'<span class="kl-chip" style="color:{teks};background:{latar}"><i></i>{chip}</span>'
        '</div>', unsafe_allow_html=True)
    if (hasil["grid_id"], hasil["periode"]) != (grid_id, periode):
        st.markdown(f'<div class="kl-kecil">Hasil untuk {label.get(hasil["grid_id"])}. '
                    'Pilihan sudah berubah; tekan <b>Jalankan klasifikasi</b> untuk '
                    'memperbarui.</div>', unsafe_allow_html=True)
    if hasil["galat"]:
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Data cuaca gagal '
                    f'diambil</div>{hasil["galat"]}<br>Tekan <b>Jalankan klasifikasi</b> '
                    'untuk mencoba lagi.</div>', unsafe_allow_html=True)
        return None
    if hasil["grid"] is None:
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Tidak ada data'
                    '</div>Grid ini tidak punya data pada periode tersebut.</div>',
                    unsafe_allow_html=True)
        return None
    kartu = "".join(_html_hasil(h) for h in hasil["grid"].kondisi[0].hasil)
    st.markdown(f'<div class="kl-kartu-grup">{kartu}</div>{_html_ringkas(hasil["grid"])}',
                unsafe_allow_html=True)
    return hasil


# ---- halaman --------------------------------------------------------------------

def render(sumber: SumberDataService) -> None:
    # Pertahankan pilihan widget. Klik peta memicu rerun sebelum dropdown sempat
    # dibuat; tanpa ini Streamlit membuang nilainya dan periode kembali ke bawaan.
    for kunci in ("kl_grid", "kl_tahun", "kl_bulan"):
        if kunci in st.session_state:
            st.session_state[kunci] = st.session_state[kunci]

    grid_tersedia = sumber.daftar_grid_tersedia()
    label = {r.grid_id: _label_grid(r) for r in grid_tersedia.itertuples()}
    daftar = sumber.daftar_periode_pilihan()

    st.session_state.setdefault("kl_grid", grid_tersedia.grid_id.iloc[0])
    periode = _periode_aktif(sumber, daftar)
    status = sumber.status_periode(periode)

    st.markdown(
        '<div class="kl-label">Klasifikasi</div>'
        '<div class="kl-judul">Klasifikasi kerawanan per grid</div>'
        '<div class="kl-sub">Pilih grid lewat peta, daftar wilayah, atau koordinat, pilih '
        'periodenya, lalu tekan Jalankan klasifikasi. Hasil Random Forest dan XGBoost tampil '
        'berdampingan.</div>',
        unsafe_allow_html=True,
    )
    if "kl_pesan" in st.session_state:
        teks, ikon = st.session_state.pop("kl_pesan")
        st.toast(teks, icon=ikon)

    # 4. Klasifikasi - hanya pada rerun yang dipicu tombol
    if st.session_state.pop("kl_jalankan", False):
        _jalankan(sumber, st.session_state.kl_grid, periode, status)

    kiri, kanan = st.columns([3, 2], gap="medium")

    # 2. Peta interaktif kerawanan. Digambar sebelum dropdown wilayah supaya klik
    # pada peta sudah mengubah kl_grid sebelum dropdown dibuat.
    with kiri, st.container(key="bento_kl_peta", height="stretch"):
        klik = peta.render(sumber, periode, st.session_state.kl_grid,
                           _prediksi_peta(sumber, periode, status))
    if klik:
        _pilih_koordinat(sumber, *klik, "Titik")
        st.rerun()  # gambar ulang bingkai grid terpilih

    with kanan, st.container(key="bento_kl_panel", height="stretch"):
        # 3. Pemilihan wilayah dan periode
        _render_pilihan(sumber, label, daftar)
        st.button("Jalankan klasifikasi", type="primary", icon=":material/play_arrow:",
                  width="stretch", on_click=_minta_jalankan)
        # 5. Hasil kedua model berdampingan (dari tombol terakhir)
        hasil = _render_hasil(label, st.session_state.kl_grid, periode)
    if hasil is None:
        return
    grid = hasil["grid"]

    # 6. Rincian variabel prediktor
    with st.container(key="bento_kl_variabel"):
        rincian_variabel.render(sumber, grid)

    # 7. Informasi periode mendatang - hanya bila cuaca tidak dari basis data
    komposisi = grid.kondisi[0].komposisi
    if komposisi is not None:
        with st.container(key="bento_kl_mendatang"):
            periode_mendatang.render(komposisi, hasil["periode"], hasil["status"])
