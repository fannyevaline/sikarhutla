"""Halaman Klasifikasi: modul 2-5 (peta menyusul, pemilihan wilayah & periode,
klasifikasi, hasil & confidence)."""
import streamlit as st

from domain.grid import Grid, HasilPrediksi
from domain.modul_klasifikasi import ModulKlasifikasi
from domain.sumber_data_service import KELAS, SumberDataService
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
.kl-peta-kosong { border: 2px dashed #e0d7cd; border-radius: 14px; height: 100%;
    min-height: 300px; display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center; color: #8a827a; gap: 0.3rem;
    background: repeating-linear-gradient(45deg, #faf8f5, #faf8f5 12px, #f5f1ec 12px, #f5f1ec 24px); }
.kl-peta-kosong b { color: #4f4842; font-size: 1rem; }
.kl-terpilih { margin-top: 0.8rem; padding: 0.75rem 1rem; border-radius: 12px;
    background: #fff4ea; border: 1px solid #ffd8bd; }
.kl-terpilih b { color: #1f1b18; }

.kl-hasil { border-radius: 16px; padding: 1.3rem 1.4rem; border: 1px solid; height: 100%; }
.kl-model { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #4f4842; }
.kl-kelas { font-size: 2.3rem; font-weight: 800; line-height: 1.1; margin: 0.35rem 0 0.1rem;
    letter-spacing: -0.02em; }
.kl-conf { font-size: 0.95rem; color: #4f4842; }
.kl-conf b { font-size: 1.15rem; }
.kl-proba { margin-top: 1rem; display: grid; grid-template-columns: 4.2rem 1fr 3rem;
    gap: 0.45rem 0.6rem; align-items: center; font-size: 0.84rem; color: #4f4842; }
.kl-proba-batang { height: 8px; border-radius: 999px; background: rgba(0,0,0,0.07);
    overflow: hidden; }
.kl-proba-batang div { height: 100%; border-radius: 999px; }
.kl-proba span:nth-child(3n) { text-align: right; font-variant-numeric: tabular-nums; }
.kl-ringkas { margin-top: 1rem; padding: 0.8rem 1rem; border-radius: 12px; background: #fff;
    border: 1px solid #ece5dc; display: flex; flex-wrap: wrap; gap: 0.4rem 1.6rem;
    font-size: 0.9rem; color: #4f4842; }
.kl-ringkas b { color: #1f1b18; }
.kl-titik { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
    margin-right: 0.35rem; }
</style>
"""


def _label_grid(baris) -> str:
    if isinstance(baris.kabupaten, str):
        return f"{baris.kabupaten}, {baris.provinsi}  ·  {baris.grid_lat:.2f}, {baris.grid_lon:.2f}"
    return f"Grid {baris.grid_lat:.2f}, {baris.grid_lon:.2f}"


def _pakai_koordinat(sumber: SumberDataService) -> None:
    """Callback tombol koordinat: ubah pilihan grid yang sama dengan dropdown."""
    lat, lon = st.session_state.kl_lat, st.session_state.kl_lon
    grid_id, ada = sumber.cari_grid(lat, lon)
    if grid_id is None:
        st.session_state.kl_pesan = ("error", f"Koordinat {lat:.3f}, {lon:.3f} berada di "
                                     "luar 232 grid wilayah kajian Kalimantan.")
    elif not ada:
        st.session_state.kl_pesan = ("warning", f"Koordinat {lat:.3f}, {lon:.3f} masuk grid "
                                     f"{grid_id}, tetapi grid itu tidak ada di dataset.")
    else:
        st.session_state.kl_grid = grid_id
        st.session_state.kl_pesan = ("success", f"Koordinat {lat:.3f}, {lon:.3f} masuk grid "
                                     f"{grid_id}. Pilihan wilayah diperbarui.")


def _html_hasil(h: HasilPrediksi) -> str:
    proba = "".join(
        f'<span>{k}</span><div class="kl-proba-batang">'
        f'<div style="width:{h.probabilitas[k]:.1%};background:{WARNA[k]}"></div></div>'
        f'<span>{h.probabilitas[k]:.1%}</span>'
        for k in KELAS
    )
    return (
        f'<div class="kl-hasil" style="background:{WARNA_LATAR[h.kelas]};'
        f'border-color:{WARNA[h.kelas]}">'
        f'<div class="kl-model">{h.model}</div>'
        f'<div class="kl-kelas" style="color:{WARNA_TEKS[h.kelas]}">{h.kelas}</div>'
        f'<div class="kl-conf">Confidence <b>{h.confidence:.1%}</b></div>'
        f'<div class="kl-proba">{proba}</div></div>'
    )


def _html_ringkas(grid: Grid) -> str:
    k = grid.kondisi[0]
    rf, xgb = k.hasil
    sepakat = ("Kedua model <b>sepakat</b>" if rf.kelas == xgb.kelas
               else "Kedua model <b>berbeda</b> pendapat")
    return (
        '<div class="kl-ringkas">'
        f'<span>{sepakat}</span>'
        f'<span>Kategori tercatat: <span class="kl-titik" style="background:{WARNA[k.kerawanan]}">'
        f'</span><b>{k.kerawanan}</b> ({k.jumlah_hotspot} titik panas)</span>'
        f'<span>Hasil disimpan ke HASIL_PREDIKSI (kondisi_id {k.kondisi_id})</span></div>'
    )


def render(sumber: SumberDataService) -> None:
    grid_tersedia = sumber.daftar_grid_tersedia()
    daftar_periode = sumber.daftar_periode()
    label = {r.grid_id: _label_grid(r) for r in grid_tersedia.itertuples()}

    st.session_state.setdefault("kl_grid", grid_tersedia.grid_id.iloc[0])
    st.session_state.setdefault("kl_tahun", int(daftar_periode[-1][:4]))

    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="kl-label">Klasifikasi</div>'
        '<div class="kl-judul">Klasifikasi kerawanan per grid</div>'
        '<div class="kl-sub">Pilih wilayah dan periode, lalu jalankan Random Forest dan '
        'XGBoost sekaligus.</div>',
        unsafe_allow_html=True,
    )

    kiri, kanan = st.columns([3, 2], gap="medium")

    # 2. Peta interaktif - tempatnya disiapkan, isinya menyusul
    with kiri, st.container(key="bento_kl_peta", height="stretch"):
        st.markdown(
            '<div class="kl-h2">Peta interaktif kerawanan</div>'
            '<div class="kl-kecil" style="margin-bottom:0.8rem">Klik grid untuk memilih wilayah</div>'
            '<div class="kl-peta-kosong"><b>Peta menyusul</b>'
            '<span>Untuk sementara pilih wilayah lewat daftar atau koordinat</span></div>',
            unsafe_allow_html=True,
        )

    # 3. Pemilihan wilayah dan periode
    with kanan, st.container(key="bento_kl_pilih", height="stretch"):
        st.markdown('<div class="kl-h2">Wilayah</div>', unsafe_allow_html=True)
        cara = st.segmented_control("Cara memilih", ["Daftar wilayah", "Koordinat manual"],
                                    default="Daftar wilayah", key="kl_cara",
                                    label_visibility="collapsed")
        if cara == "Koordinat manual":
            a, b = st.columns(2)
            a.number_input("Lintang", -5.0, 5.0, 0.0, 0.01, format="%.3f", key="kl_lat")
            b.number_input("Bujur", 108.0, 120.0, 114.0, 0.01, format="%.3f", key="kl_lon")
            st.button("Cari grid", icon=":material/my_location:", width="stretch",
                      on_click=_pakai_koordinat, args=(sumber,))
            if "kl_pesan" in st.session_state:
                jenis, teks = st.session_state.pop("kl_pesan")
                getattr(st, jenis)(teks)
        st.selectbox("Wilayah (grid)", list(label), key="kl_grid",
                     format_func=label.get, disabled=cara == "Koordinat manual",
                     help="Hanya grid yang ada di dataset (221 grid)")

        st.markdown('<div class="kl-h2" style="margin-top:0.6rem">Periode</div>',
                    unsafe_allow_html=True)
        tahun_ada = sorted({int(p[:4]) for p in daftar_periode})
        a, b = st.columns(2)
        tahun = a.selectbox("Tahun", tahun_ada, key="kl_tahun")
        bulan_ada = [int(p[5:]) for p in daftar_periode if p.startswith(str(tahun))]
        if st.session_state.get("kl_bulan") not in bulan_ada:
            st.session_state.kl_bulan = bulan_ada[-1]
        bulan = b.selectbox("Bulan", bulan_ada, key="kl_bulan",
                            format_func=lambda m: BULAN[m - 1])
        periode = f"{tahun}-{bulan:02d}"

        jalan = st.button("Jalankan klasifikasi", icon=":material/play_arrow:",
                          type="primary", width="stretch")

    # 4. Klasifikasi
    grid_id = st.session_state.kl_grid
    if jalan:
        with st.spinner("Menjalankan Random Forest dan XGBoost..."):
            hasil = ModulKlasifikasi(sumber).klasifikasi(grid_id, periode)
        if hasil is None:
            st.error(f"Tidak ada data untuk grid {grid_id} pada {_nama_periode(periode)}.")
        st.session_state.kl_hasil = hasil

    # 5. Hasil dan confidence - kedua model berdampingan
    hasil: Grid | None = st.session_state.get("kl_hasil")
    with st.container(key="bento_kl_hasil"):
        if hasil is None:
            st.markdown('<div class="kl-h2">Hasil klasifikasi</div>'
                        '<div class="kl-kecil">Belum ada hasil. Pilih wilayah dan periode, '
                        'lalu tekan <b>Jalankan klasifikasi</b>.</div>', unsafe_allow_html=True)
            return
        k = hasil.kondisi[0]
        st.markdown(
            f'<div class="kl-h2">Hasil klasifikasi · {hasil.nama}</div>'
            f'<div class="kl-kecil">{_nama_periode(k.tahun_bulan)} · grid '
            f'{hasil.grid_lat:.2f}, {hasil.grid_lon:.2f}</div>',
            unsafe_allow_html=True,
        )
        if (hasil.grid_id, k.tahun_bulan) != (grid_id, periode):
            st.caption("Pilihan wilayah atau periode sudah diubah. Tekan Jalankan "
                       "klasifikasi untuk memperbarui hasil.")
        kol = st.columns(2, gap="medium")
        for c, h in zip(kol, k.hasil):
            c.markdown(_html_hasil(h), unsafe_allow_html=True)
        st.markdown(_html_ringkas(hasil), unsafe_allow_html=True)
