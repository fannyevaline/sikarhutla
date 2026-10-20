"""Halaman Klasifikasi: modul 2-7 dalam satu alur dari atas ke bawah.

2. Peta interaktif kerawanan        (modul/peta.py)
3. Pemilihan wilayah dan periode
4. Klasifikasi kerawanan            (otomatis setiap pilihan berubah)
5. Hasil klasifikasi dan confidence
6. Rincian variabel prediktor       (modul/rincian_variabel.py)
7. Informasi periode mendatang      (modul/periode_mendatang.py)
"""
import streamlit as st

from domain.grid import Grid, HasilPrediksi
from domain.modul_klasifikasi import ModulKlasifikasi
from domain.sumber_data_service import KELAS, GagalAmbilCuaca, SumberDataService
from modul import peta, periode_mendatang, rincian_variabel
from modul.beranda import BULAN, WARNA, WARNA_LATAR, WARNA_TEKS, _nama_periode

CSS = """
<style>
.kl-label { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #e8590c; margin-bottom: 0.25rem; }
.kl-judul { font-size: 2rem; font-weight: 800; color: #1f1b18; line-height: 1.15;
    letter-spacing: -0.02em; }
.kl-sub { color: #756d66; font-size: 0.98rem; margin: 0.3rem 0 1.2rem; }
.kl-h2 { font-size: 1.08rem; font-weight: 700; color: #1f1b18; margin: 0; }
.kl-kecil { color: #756d66; font-size: 0.86rem; }
.st-key-bento_kl_peta:hover, .st-key-bento_kl_panel:hover { transform: none !important; }
.st-key-bento_kl_panel [data-testid="stPopover"] button { padding: 0; min-height: 0;
    font-size: 0.84rem; color: #b8460b; }

.kl-garis { border-top: 1px solid #f1ece6; margin: 0.4rem 0 0.2rem; }
.kl-kepala { display: flex; justify-content: space-between; align-items: center;
    gap: 0.6rem; flex-wrap: wrap; }
.kl-chip { display: inline-flex; align-items: center; gap: 0.35rem; white-space: nowrap;
    border-radius: 999px; padding: 0.22rem 0.7rem; font-size: 0.76rem; font-weight: 700; }
.kl-chip i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

.kl-kosong { border: 2px dashed #e6ddd3; border-radius: 14px; padding: 1.6rem 1.2rem;
    text-align: center; color: #8a827a; font-size: 0.88rem; margin-top: 0.7rem; }
.kl-kosong-judul { color: #4f4842; font-size: 1rem; font-weight: 700; margin-bottom: 0.25rem; }

.kl-kartu-grup { display: grid; gap: 0.6rem; margin-top: 0.7rem;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
.kl-hasil { border-radius: 14px; padding: 0.85rem 1rem; border: 1px solid; min-width: 0; }
.kl-hasil-atas { display: flex; justify-content: space-between; align-items: flex-end;
    gap: 0.8rem; }
.kl-model { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #4f4842; }
.kl-kelas { font-size: 1.75rem; font-weight: 800; line-height: 1.1; margin-top: 0.15rem;
    letter-spacing: -0.02em; white-space: nowrap; }
.kl-conf { text-align: right; white-space: nowrap; }
.kl-conf small { display: block; font-size: 0.72rem; color: #6f6760; font-weight: 600; }
.kl-conf b { font-size: 1.45rem; font-weight: 800; letter-spacing: -0.01em; }
.kl-sebaran { display: flex; height: 8px; border-radius: 999px; overflow: hidden; gap: 2px;
    margin-top: 0.7rem; background: rgba(0,0,0,0.06); }
.kl-sebaran-ket { display: flex; justify-content: space-between; gap: 0.5rem;
    margin-top: 0.4rem; font-size: 0.76rem; color: #4f4842;
    font-variant-numeric: tabular-nums; }
.kl-sebaran-ket span { display: inline-flex; align-items: center; gap: 0.3rem;
    white-space: nowrap; }
.kl-sebaran-ket i { width: 8px; height: 8px; border-radius: 2px; }

.kl-ringkas { margin-top: 0.7rem; display: flex; flex-direction: column; gap: 0.35rem;
    font-size: 0.85rem; color: #4f4842; }
.kl-ringkas > div { display: flex; justify-content: space-between; gap: 1rem;
    padding: 0.45rem 0.8rem; border-radius: 10px; background: #faf7f3; }
.kl-ringkas span:first-child { white-space: nowrap; }
.kl-ringkas b { color: #1f1b18; text-align: right; }
.kl-titik { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
    margin-right: 0.35rem; }
</style>
"""

STATUS = {  # label chip, warna teks, warna latar
    "historis": ("Tercatat", "#137a3f", "#dcf3e5"),
    "selesai": ("Di luar basis data", "#6f6760", "#efe9e2"),
    "berjalan": ("Bulan berjalan", "#b8460b", "#ffe8d6"),
    "mendatang": ("Bulan mendatang", "#7048e8", "#ece6ff"),
}
AKHIRAN_BULAN = {"historis": "", "selesai": " · di luar basis data",
                 "berjalan": " · berjalan", "mendatang": " · mendatang"}
MAKS_TERSIMPAN = 60  # hasil per (grid, periode) yang diingat selama sesi


def _label_grid(baris) -> str:
    if isinstance(baris.kabupaten, str):
        return f"{baris.kabupaten}, {baris.provinsi}  ·  {baris.grid_lat:.2f}, {baris.grid_lon:.2f}"
    return f"Grid {baris.grid_lat:.2f}, {baris.grid_lon:.2f}"


# ---- 3. Pemilihan wilayah dan periode ---------------------------------------------

def _pilih_koordinat(sumber: SumberDataService, lat: float, lon: float, asal: str) -> None:
    """Ubah pilihan grid dari koordinat (klik peta atau masukan manual). Pesannya
    ditampilkan sebagai toast pada render berikutnya."""
    grid_id, ada = sumber.cari_grid(lat, lon)
    lokasi = f"{lat:.3f}, {lon:.3f}"
    if grid_id is None:
        st.session_state.kl_pesan = (f"{asal} {lokasi} berada di luar 232 grid wilayah "
                                     "kajian.", ":material/wrong_location:")
    elif not ada:
        st.session_state.kl_pesan = (f"Grid {grid_id} tidak ada di dataset (tidak ada data), "
                                     "jadi tidak bisa diklasifikasi.", ":material/block:")
    elif asal == "Koordinat":  # klik peta sudah terlihat dari bingkai, tidak perlu toast
        st.session_state.kl_grid = grid_id
        st.session_state.kl_pesan = (f"Koordinat {lokasi} masuk grid {grid_id}.",
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
                      "Hanya 221 grid yang ada di dataset yang dapat dipilih.")
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


# ---- 4. Klasifikasi (otomatis) --------------------------------------------------

def _klasifikasi(sumber: SumberDataService, grid_id: str, periode: str) -> Grid | None:
    """Jalankan kedua model sekali untuk tiap (grid, periode) dalam satu sesi.
    Kembali ke pilihan yang sama memakai hasil yang sudah ada, jadi tidak dijalankan
    dan disimpan ulang. Melempar GagalAmbilCuaca kalau Open-Meteo gagal."""
    tersimpan: dict = st.session_state.setdefault("kl_tersimpan", {})
    kunci = (grid_id, periode)
    if kunci not in tersimpan:
        teks = ("Menjalankan Random Forest dan XGBoost..."
                if sumber.status_periode(periode) == "historis"
                else "Menyusun cuaca dari Open-Meteo dan menjalankan kedua model...")
        with st.spinner(teks):
            tersimpan[kunci] = ModulKlasifikasi(sumber).klasifikasi(grid_id, periode)
        if len(tersimpan) > MAKS_TERSIMPAN:
            tersimpan.pop(next(iter(tersimpan)))
    return tersimpan[kunci]


def _prediksi_peta(sumber: SumberDataService, periode: str, status: str):
    """Prediksi kedua model untuk semua grid, hanya untuk bulan di luar basis data.
    Pertama kali sebuah bulan dibuka perlu waktu (data cuaca 221 grid); sesudahnya
    diambil dari cache. None kalau Open-Meteo gagal."""
    if status == "historis":
        return None
    kabar = st.empty()
    try:
        with st.spinner(f"Menyusun cuaca 221 grid untuk {_nama_periode(periode)}..."):
            prediksi = ModulKlasifikasi(sumber).klasifikasi_bulan(
                periode, kabar=lambda teks: kabar.caption(teks))
    except GagalAmbilCuaca as e:
        kabar.warning(f"Peta belum bisa diwarnai: data cuaca gagal diambil ({e}).",
                      icon=":material/cloud_off:")
        return None
    kabar.empty()
    return prediksi


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
        f'<b>{h.confidence:.1%}</b></div></div>'
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
        baris.append(("Sesuai dengan tercatat", " dan ".join(tepat) if tepat else "Tidak ada"))
    else:
        baris.append(("Kategori tercatat", "Belum ada"))
        baris.append(("Riwayat", "Tidak disimpan"))
    isi = "".join(f"<div><span>{a}</span><b>{b}</b></div>" for a, b in baris)
    return f'<div class="kl-ringkas">{isi}</div>'


def _render_hasil(sumber: SumberDataService, grid_id: str, periode: str,
                  status: str) -> Grid | None:
    chip, teks, latar = STATUS[status]
    st.markdown(
        '<div class="kl-garis"></div><div class="kl-kepala">'
        f'<div class="kl-h2">Hasil · {_nama_periode(periode)}</div>'
        f'<span class="kl-chip" style="color:{teks};background:{latar}"><i></i>{chip}</span>'
        '</div>', unsafe_allow_html=True)
    try:
        hasil = _klasifikasi(sumber, grid_id, periode)
    except GagalAmbilCuaca as e:
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Data cuaca gagal '
                    f'diambil</div>{e}</div>', unsafe_allow_html=True)
        st.button("Coba lagi", icon=":material/refresh:", width="stretch")
        return None
    if hasil is None:
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Tidak ada data'
                    '</div>Grid ini tidak punya data pada periode tersebut.</div>',
                    unsafe_allow_html=True)
        return None
    kartu = "".join(_html_hasil(h) for h in hasil.kondisi[0].hasil)
    st.markdown(f'<div class="kl-kartu-grup">{kartu}</div>{_html_ringkas(hasil)}',
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

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="kl-label">Klasifikasi</div>'
        '<div class="kl-judul">Klasifikasi kerawanan per grid</div>'
        '<div class="kl-sub">Klik grid pada peta atau pilih wilayah dan periode. Random Forest '
        'dan XGBoost langsung dijalankan.</div>',
        unsafe_allow_html=True,
    )
    if "kl_pesan" in st.session_state:
        teks, ikon = st.session_state.pop("kl_pesan")
        st.toast(teks, icon=ikon)

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
        # 4 & 5. Klasifikasi otomatis, lalu hasil kedua model berdampingan
        hasil = _render_hasil(sumber, st.session_state.kl_grid, periode, status)
    if hasil is None:
        return

    # 6. Rincian variabel prediktor
    with st.container(key="bento_kl_variabel"):
        rincian_variabel.render(sumber, hasil)

    # 7. Informasi periode mendatang - hanya bila cuaca tidak dari basis data
    komposisi = hasil.kondisi[0].komposisi
    if komposisi is not None:
        with st.container(key="bento_kl_mendatang"):
            periode_mendatang.render(komposisi, periode, status)
