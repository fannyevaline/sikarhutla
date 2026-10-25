"""Modul 8 - Perbandingan performa model.

Semua angka dibaca dari data/model/metrik_lengkap_*.csv lewat SumberDataService;
tidak ada metrik yang dihitung ulang di sini. Yang dilakukan halaman ini hanya memilih
baris, memformat angka, dan menandai nilai tertinggi tiap kolom.

Model final = skenario SKENARIO_FINAL dengan model F1-macro tertinggi
(SumberDataService.model_terbaik(), sama dengan yang dipakai untuk mewarnai peta).
"""
import pandas as pd
import streamlit as st

from domain.konstanta import SKENARIO_FINAL
from domain.sumber_data_service import SumberDataService
from modul.tampilan import WARNA, angka

# kolom CSV -> (judul kolom, keterangan kecil di bawah judul)
KOLOM_RINGKASAN = {
    "Akurasi": ("Akurasi", ""),
    "Precision_Macro": ("Precision", "macro"),
    "Recall_Macro": ("Recall", "macro"),
    "F1_Macro": ("F1", "macro"),
    "AUC_Macro": ("AUC", "macro"),
    "Cohen_Kappa": ("Cohen's Kappa", ""),
    "MCC": ("MCC", ""),
}
KOLOM_PER_KELAS = {"Precision": "Precision", "Recall": "Recall", "F1": "F1", "AUC": "AUC"}


def _persen(x: float) -> str:
    return f"{angka(x * 100, 2)}%"


def _nama_skenario(skenario: str) -> str:
    """"DENGAN SMOTENC" -> "Dengan SMOTENC"."""
    awal, *sisa = skenario.split()
    return " ".join([awal.capitalize(), *sisa])


def _html_nama(baris, final: bool) -> str:
    """Nama model + skenario, dengan chip "Model final" bila baris ini model final."""
    chip = '<span class="pf-chip">Model final</span>' if final else ""
    return (f'<div class="pf-nama">{baris.Model}{chip}</div>'
            f'<div class="pf-skenario">{_nama_skenario(baris.Skenario)}</div>')


def _is_final(baris, model_final: str) -> bool:
    return baris.Skenario == SKENARIO_FINAL and baris.Model == model_final


# ---- 1. perbandingan empat skenario -----------------------------------------------

def _html_ringkasan(ringkasan: pd.DataFrame, model_final: str) -> str:
    kepala = "".join(f"<th>{judul}<small>{ket}</small></th>"
                     for judul, ket in KOLOM_RINGKASAN.values())
    tertinggi = ringkasan[list(KOLOM_RINGKASAN)].max()
    baris = ""
    for b in ringkasan.itertuples():
        final = _is_final(b, model_final)
        sel = "".join(
            f"<td>{'<b>' if getattr(b, k) == tertinggi[k] else ''}{angka(getattr(b, k), 3)}</td>"
            for k in KOLOM_RINGKASAN)
        baris += (f'<tr class="{"pf-final" if final else ""}">'
                  f'<td>{_html_nama(b, final)}</td>{sel}</tr>')
    return (
        '<div class="kl-h2">Perbandingan empat skenario</div>'
        '<div class="kl-kecil">Dua algoritma, masing-masing dilatih tanpa dan dengan '
        'SMOTENC. Angka tebal = tertinggi di kolomnya.</div>'
        f'<div class="pf-gulir"><table class="pf-tabel"><thead><tr>'
        f'<th>Model · skenario</th>{kepala}</tr></thead><tbody>{baris}</tbody></table></div>'
    )


# ---- 2. per kelas, model final ----------------------------------------------------

def _html_per_kelas(per_kelas: pd.DataFrame, model_final: str) -> str:
    kepala = "".join(f"<th>{j}</th>" for j in KOLOM_PER_KELAS.values())
    baris = "".join(
        f'<tr><td><span class="pf-kelas"><i style="background:{WARNA[k]}"></i>{k}</span></td>'
        + "".join(f"<td>{angka(r[c], 3)}</td>" for c in KOLOM_PER_KELAS)
        + f'<td>{_persen(r["Tingkat_Kesalahan"])}</td><td>{angka(r["Jumlah_data"])}</td></tr>'
        for k, r in per_kelas.iterrows())
    return (
        f'<div class="kl-h2">Per kelas · {model_final}</div>'
        f'<div class="kl-kecil">Model final, skenario {_nama_skenario(SKENARIO_FINAL)}. '
        'Tingkat kesalahan = bagian data kelas itu yang diklasifikasikan ke kelas lain.</div>'
        f'<div class="pf-gulir"><table class="pf-tabel"><thead><tr><th>Kelas</th>{kepala}'
        f'<th>Tingkat<small>kesalahan</small></th><th>Jumlah<small>data</small></th>'
        f'</tr></thead>'
        f'<tbody>{baris}</tbody></table></div>'
    )


# ---- 3. kesalahan paling berbahaya: Tinggi -> Rendah --------------------------------

def _kalimat_perubahan(ringkasan: pd.DataFrame) -> str:
    """Perubahan Persen_Tinggi_jadi_Rendah dari tanpa ke dengan SMOTENC, per model."""
    bagian = []
    for model, data in ringkasan.groupby("Model", sort=False):
        sebelum = data.loc[data.Skenario != SKENARIO_FINAL, "Persen_Tinggi_jadi_Rendah"].iloc[0]
        sesudah = data.loc[data.Skenario == SKENARIO_FINAL, "Persen_Tinggi_jadi_Rendah"].iloc[0]
        arah = "turun" if sesudah < sebelum else "naik"
        bagian.append(f"{model} {arah} dari <b>{_persen(sebelum)}</b> "
                      f"menjadi <b>{_persen(sesudah)}</b>")
    return "Dengan SMOTENC, " + "; ".join(bagian) + "."


def _html_bahaya(sumber: SumberDataService, ringkasan: pd.DataFrame, model_final: str) -> str:
    batang = ""
    for b in ringkasan.itertuples():
        final = _is_final(b, model_final)
        n_tinggi = sumber.metrik_per_kelas(b.Skenario, b.Model).loc["Tinggi", "Jumlah_data"]
        batang += (
            f'<div class="pf-bahaya{" pf-final" if final else ""}">'
            f'<div class="pf-bahaya-atas"><div>{_html_nama(b, final)}</div>'
            f'<div class="pf-bahaya-nilai">{_persen(b.Persen_Tinggi_jadi_Rendah)}'
            f'<small>{angka(b.Tinggi_jadi_Rendah)} dari {angka(n_tinggi)} grid Tinggi</small>'
            f'</div></div>'
            f'<div class="pf-batang"><i style="width:{b.Persen_Tinggi_jadi_Rendah * 100:.2f}%;'
            f'background:{WARNA["Tinggi"]}"></i></div></div>'
        )
    return (
        '<div class="kl-h2">Kesalahan paling berbahaya: Tinggi → Rendah</div>'
        '<div class="kl-kecil">Grid yang sebenarnya rawan tinggi tetapi diklasifikasikan '
        'rendah, sehingga bisa luput dari kewaspadaan.</div>'
        f'{batang}<div class="pf-catatan">{_kalimat_perubahan(ringkasan)}</div>'
    )


# ---- 5. cara membaca ----------------------------------------------------------------

def _html_cara_membaca(per_kelas: pd.DataFrame) -> str:
    n = per_kelas["Jumlah_data"]
    return (
        '<div class="kl-h2">Cara membaca</div>'
        '<div class="pf-baca">'
        '<div><b>Kenapa macro, bukan weighted.</b> Data uji timpang: '
        f'{angka(n["Rendah"])} dari {angka(n.sum())} grid-bulan berkelas Rendah. Rata-rata '
        '<i>weighted</i> diberi bobot sesuai jumlah data, jadi didominasi kelas Rendah yang '
        'mudah ditebak. Rata-rata <i>macro</i> memberi bobot sama pada ketiga kelas, sehingga '
        'kelemahan pada kelas Sedang dan Tinggi tetap terlihat. Itu juga sebabnya akurasi '
        'tertinggi tidak otomatis berarti model terbaik.</div>'
        "<div><b>Cohen's Kappa.</b> Mengukur kesesuaian prediksi dengan label sebenarnya "
        'setelah dikurangi kesesuaian yang bisa terjadi secara kebetulan. Nilai 0 berarti '
        'tidak lebih baik daripada menebak sesuai proporsi kelas; 1 berarti sempurna.</div>'
        '<div><b>MCC.</b> Korelasi antara prediksi dan label sebenarnya, dari −1 sampai 1; '
        'tetap adil pada data yang timpang karena memperhitungkan semua sel confusion '
        'matrix.</div>'
        '<div><b>Model final</b> dipilih dari F1 macro tertinggi pada skenario '
        f'{_nama_skenario(SKENARIO_FINAL)}.</div>'
        '</div>'
    )


# ---- halaman ------------------------------------------------------------------------

def render(sumber: SumberDataService) -> None:
    ringkasan = sumber.metrik_ringkasan()
    model_final = sumber.model_terbaik()
    per_kelas = sumber.metrik_per_kelas(SKENARIO_FINAL, model_final)
    n_uji = int(ringkasan["Jumlah_benar"].iloc[0] + ringkasan["Jumlah_salah"].iloc[0])

    st.markdown(
        '<div class="kl-label">Performa model</div>'
        '<div class="kl-judul">Perbandingan performa model</div>'
        f'<div class="kl-sub">Hasil pengujian pada {angka(n_uji)} grid-bulan dari grid yang '
        'dipisahkan dari data latih.</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="pf_tab"):
        internal, eksternal = st.tabs(["Pengujian internal", "Pengujian eksternal"])

    with internal:
        with st.container(key="bento_pf_skenario"):
            st.markdown(_html_ringkasan(ringkasan, model_final), unsafe_allow_html=True)
        kiri, kanan = st.columns([1.25, 1], gap="medium")
        with kiri, st.container(key="bento_pf_kelas", height="stretch"):
            st.markdown(_html_per_kelas(per_kelas, model_final), unsafe_allow_html=True)
        with kanan, st.container(key="bento_pf_bahaya", height="stretch"):
            st.markdown(_html_bahaya(sumber, ringkasan, model_final), unsafe_allow_html=True)
        with st.container(key="bento_pf_baca"):
            st.markdown(_html_cara_membaca(per_kelas), unsafe_allow_html=True)

    with eksternal, st.container(key="bento_pf_eksternal"):
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Belum tersedia'
                    '</div>Angka akan terisi setelah tahap pengujian eksternal selesai.'
                    '</div>', unsafe_allow_html=True)
