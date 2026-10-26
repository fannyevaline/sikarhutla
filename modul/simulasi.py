"""Modul 10 - Simulasi: pengguna mengisi sendiri sebelas variabel prediktor, lalu
melihat hasil klasifikasi kedua model.

Tidak terikat grid maupun periode, jadi hasilnya tidak disimpan ke HASIL_PREDIKSI
(sama dengan perlakuan bulan di luar basis data). Batas dan nilai awal isian
diambil dari data nyata lewat SumberDataService.rentang_variabel().

Nilai isian disimpan di session_state.sim_isian (satuan tampilan) supaya tetap ada
saat pindah menu. Model hanya dijalankan saat tombol Jalankan simulasi ditekan.
"""
import math

import pandas as pd
import streamlit as st

from domain.grid import HasilPrediksi
from domain.konstanta import FEATURE_COLS, KELAS
from domain.model_klasifikasi import kategori_dikenal
from domain.modul_klasifikasi import ModulKlasifikasi
from domain.sumber_data_service import SumberDataService
from modul.tampilan import LABEL_GAMBUT, WARNA, WARNA_LATAR, WARNA_TEKS, angka

# kolom -> (nama, satuan tampilan, desimal tampilan, pembagi ke satuan tampilan)
NUMERIK = {
    "ketinggian_meter": ("Ketinggian", "m dpl", 0, 1),
    "kemiringan_lereng": ("Kemiringan lereng", "°", 1, 1),
    "curah_hujan_mm": ("Curah hujan", "mm", 0, 1),
    "suhu_maks_c": ("Suhu maks.", "°C", 1, 1),
    "kelembapan_persen": ("Kelembapan", "%", 1, 1),
    "angin_maks_kmh": ("Angin", "km/jam", 1, 1),
    "hari_kering_maks": ("Hari kering", "hari", 0, 1),
    "jarak_air_meter": ("Jarak ke badan air", "km", 1, 1000),
    "jarak_jalan_meter": ("Jarak ke jalan", "km", 1, 1000),
}
# Dua panel, sama dengan Rincian Variabel di halaman Klasifikasi; nomor tetap 1-11.
KELOMPOK = [
    ("Cuaca bulanan", "Curah hujan dijumlahkan sebulan, variabel lain dirata-ratakan. "
                      "Hari kering adalah rentang hari tanpa hujan terpanjang dalam sebulan.",
     ["curah_hujan_mm", "suhu_maks_c", "kelembapan_persen", "angin_maks_kmh",
      "hari_kering_maks"]),
    ("Karakteristik grid", "Tidak berubah dari bulan ke bulan.",
     ["ketinggian_meter", "kemiringan_lereng", "jarak_air_meter", "jarak_jalan_meter",
      "tutupan_lahan", "gambut"]),
]
NAMA_KATEGORI = {"tutupan_lahan": "Tutupan lahan", "gambut": "Status gambut"}


def _nomor(kolom: str) -> int:
    return FEATURE_COLS.index(kolom) + 1


def _batas(rentang: pd.DataFrame) -> dict:
    """Min, max, median tiap angka dalam satuan tampilan. Min dibulatkan ke bawah dan
    max ke atas sesuai desimal tampilan, supaya seluruh rentang data tetap terjangkau."""
    hasil = {}
    for kolom, (_, _, desimal, pembagi) in NUMERIK.items():
        r = rentang.loc[kolom] / pembagi
        f = 10 ** desimal
        lo, hi = math.floor(r["min"] * f) / f, math.ceil(r["max"] * f) / f
        md = round(r["median"], desimal)
        hasil[kolom] = ((int(lo), int(hi), int(md)) if kolom == "hari_kering_maks"
                        else (lo, hi, md))
    return hasil


def _salin(kunci: str, kolom: str) -> None:
    """Callback isian: simpan nilainya sebagai nilai isian. Pilihan yang dikosongkan
    (None) diabaikan, jadi kembali ke nilai sebelumnya."""
    if st.session_state[kunci] is not None:
        st.session_state.sim_isian[kolom] = st.session_state[kunci]


def _setel_awal(awal: dict) -> None:
    st.session_state.sim_isian = dict(awal)


# ---- isian ------------------------------------------------------------------------

def _ubin_angka(kolom: str, batas: tuple) -> None:
    """Ubin: nama + satuan, kotak ketik, lalu rentang data."""
    nama, satuan, desimal, _ = NUMERIK[kolom]
    lo, hi, md = batas
    bulat = kolom == "hari_kering_maks"
    with st.container(key=f"sim_ubin_{kolom}"):
        st.number_input(f"{_nomor(kolom):02d} · {nama} ({satuan})", lo, hi,
                        step=1 if bulat else 10.0 ** -desimal,
                        format=None if bulat else f"%.{desimal}f",
                        key=f"sim_n_{kolom}", on_change=_salin,
                        args=(f"sim_n_{kolom}", kolom))
        st.markdown(f'<div class="sm-rentang">{angka(lo, desimal)}–{angka(hi, desimal)}'
                    f' · median {angka(md, desimal)}</div>', unsafe_allow_html=True)


def _ubin_kategori(kolom: str, daftar: list[str]) -> None:
    label = f"{_nomor(kolom):02d} · {NAMA_KATEGORI[kolom]}"
    with st.container(key=f"sim_ubin_{kolom}"):
        if kolom == "tutupan_lahan":
            st.pills(label, daftar, key=f"sim_p_{kolom}", on_change=_salin,
                     args=(f"sim_p_{kolom}", kolom))
        else:
            st.segmented_control(label, daftar, key=f"sim_p_{kolom}",
                                 format_func=LABEL_GAMBUT.get, on_change=_salin,
                                 args=(f"sim_p_{kolom}", kolom))


def _render_isian(batas: dict, pilihan: dict) -> None:
    isian = st.session_state.sim_isian
    # Isi widget dari nilai isian sebelum widgetnya dibuat.
    for kolom in NUMERIK:
        st.session_state[f"sim_n_{kolom}"] = isian[kolom]
    for kolom in pilihan:
        st.session_state[f"sim_p_{kolom}"] = isian[kolom]

    for i, (judul, ket, daftar) in enumerate(KELOMPOK):
        with st.container(key=f"bento_sim_grup{i}"):
            st.markdown(f'<div class="sm-kepala-grup"><div class="kl-h2">{judul}</div>'
                        f'<small>{ket}</small></div>', unsafe_allow_html=True)
            angka_ = [k for k in daftar if k in NUMERIK]
            for kol, kolom in zip(st.columns(len(angka_), gap="small"), angka_):
                with kol:
                    _ubin_angka(kolom, batas[kolom])
            kategori = [k for k in daftar if k in pilihan]
            if kategori:
                for kol, kolom in zip(st.columns([2.2, 1], gap="small"), kategori):
                    with kol:
                        _ubin_kategori(kolom, pilihan[kolom])


def _nilai_model(isian: dict) -> dict:
    """Isian (satuan tampilan) -> masukan model, urut FEATURE_COLS."""
    return {k: isian[k] * NUMERIK[k][3] if k in NUMERIK else isian[k] for k in FEATURE_COLS}


# ---- hasil ------------------------------------------------------------------------

def _html_kartu(h: HasilPrediksi) -> str:
    peluang = "".join(
        f'<div class="sm-p"><span>{k}</span><b>{angka(h.probabilitas[k] * 100)}%</b></div>'
        f'<div class="sm-p-bar"><i style="width:{h.probabilitas[k] * 100:.1f}%;'
        f'background:{WARNA[k]}"></i></div>' for k in KELAS)
    return (f'<div class="kl-hasil sm-kartu" style="background:{WARNA_LATAR[h.kelas]};'
            f'border-color:{WARNA[h.kelas]}"><div class="kl-model">{h.model}</div>'
            f'<div class="kl-kelas" style="color:{WARNA_TEKS[h.kelas]}">{h.kelas}</div>'
            f'<div class="sm-conf">Confidence <b style="color:{WARNA_TEKS[h.kelas]}">'
            f'{angka(h.confidence * 100, 1)}%</b></div>{peluang}</div>')


def _html_catatan(f1: pd.DataFrame) -> str:
    def per_model(k: str) -> str:
        return " / ".join(angka(f1.loc[m, k], 2) for m in f1.index)
    return ('<div class="sm-catatan"><b>Catatan:</b> prediksi kelas <b>Sedang</b> kurang '
            'andal dibanding kelas Rendah dan Tinggi. F1 hasil evaluasi model final '
            f'({" / ".join(f1.index)}): Sedang {per_model("Sedang")}, Rendah '
            f'{per_model("Rendah")}, Tinggi {per_model("Tinggi")}.</div>')


def _render_hasil(sumber: SumberDataService) -> None:
    st.markdown('<div class="kl-h2">Hasil simulasi</div>', unsafe_allow_html=True)
    simpanan = st.session_state.get("sim_hasil")
    if simpanan is None:
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Belum ada hasil'
                    '</div>Isi variabel di atas, atau langsung tekan <b>Jalankan '
                    'Simulasi</b> untuk mencoba nilai median.</div>', unsafe_allow_html=True)
        return
    if simpanan["isian"] != st.session_state.sim_isian:
        st.markdown('<div class="sm-basi">Isian sudah berubah. Tekan Jalankan simulasi '
                    'untuk memperbarui hasil.</div>', unsafe_allow_html=True)
    rf, xgb = simpanan["hasil"]
    a, b, c = st.columns([1, 1, 1.25], gap="small")
    a.markdown(_html_kartu(rf), unsafe_allow_html=True)
    b.markdown(_html_kartu(xgb), unsafe_allow_html=True)
    sepakat = "Sepakat" if rf.kelas == xgb.kelas else "Berbeda"
    c.markdown(f'<div class="sm-sepakat"><span>Kesepakatan kedua model</span>'
               f'<b>{sepakat}</b></div>' + _html_catatan(sumber.f1_per_kelas()) +
               '<div class="sm-kaki">Hasil simulasi tidak disimpan ke riwayat.</div>',
               unsafe_allow_html=True)


# ---- halaman ----------------------------------------------------------------------

def render(sumber: SumberDataService) -> None:
    rentang, kategori = sumber.rentang_variabel()
    batas = _batas(rentang)
    dikenal = kategori_dikenal("tutupan_lahan")
    pilihan = {"tutupan_lahan": [t for t in kategori["tutupan_lahan"] if t in dikenal],
               "gambut": kategori["gambut"]}
    # Nilai awal: median tiap angka, kategori yang paling sering di data.
    awal = {**{k: b[2] for k, b in batas.items()},
            **{k: daftar[0] for k, daftar in pilihan.items()}}
    st.session_state.setdefault("sim_isian", dict(awal))

    st.markdown(
        '<div class="kl-label">Simulasi</div>'
        '<div class="kl-judul">Klasifikasi dari isian sendiri</div>'
        '<div class="kl-sub">Isi sendiri kesebelas variabel prediktor, lalu tekan Jalankan '
        'simulasi untuk melihat hasil Random Forest dan XGBoost. Nilai awal tiap isian '
        'adalah median data, dan rentang datanya tertulis di bawah kotak.</div>',
        unsafe_allow_html=True,
    )
    _render_isian(batas, pilihan)

    with st.container(key="bento_sim_tombol"):
        ulang, jalan = st.columns([1, 3], gap="small")
        ulang.button("Atur ulang ke median", icon=":material/restart_alt:", width="stretch",
                     on_click=_setel_awal, args=(awal,),
                     disabled=st.session_state.sim_isian == awal)
        if jalan.button("Jalankan simulasi", type="primary", icon=":material/play_arrow:",
                        width="stretch"):
            isian = st.session_state.sim_isian
            with st.spinner("Menjalankan Random Forest dan XGBoost..."):
                st.session_state.sim_hasil = {
                    "isian": dict(isian),
                    "hasil": ModulKlasifikasi(sumber).simulasi(_nilai_model(isian))}

    with st.container(key="bento_sim_hasil"):
        _render_hasil(sumber)
