"""Modul 8 - Perbandingan performa model.

Dua tab dengan komponen tampilan yang sama:
- Pengujian internal: data/model/metrik_lengkap_*.csv dan confusion_matrix.csv
  (baris dibedakan per Skenario).
- Pengujian eksternal: data/model/metrik_eksternal_*.csv dan
  confusion_matrix_eksternal.csv (baris dibedakan per Periode).

Semua angka dibaca dari CSV lewat SumberDataService; tidak ada metrik yang dihitung
ulang di sini. Yang dilakukan halaman ini hanya memilih baris, memformat angka, dan
menandai nilai tertinggi tiap kolom.

Model final = skenario SKENARIO_FINAL dengan model F1-macro tertinggi pada pengujian
internal (SumberDataService.model_terbaik(), sama dengan yang dipakai untuk mewarnai
peta). Pengujian eksternal tidak memilih ulang model final.
"""
from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from domain.konstanta import SKENARIO_FINAL
from domain.sumber_data_service import SumberDataService
from modul.tampilan import WARNA, WARNA_LATAR, angka, nama_periode

PERIODE_EKSTERNAL = "Juli–September 2026"  # untuk keterangan saat berkasnya belum ada
KESELURUHAN = "Keseluruhan"  # nilai kolom Periode untuk gabungan seluruh bulan
LABEL_FINAL_INTERNAL = "Model final"
LABEL_FINAL_EKSTERNAL = "Model final (ditetapkan dari evaluasi internal)"


def _persen(x: float) -> str:
    return f"{angka(x * 100, 2)}%"


@dataclass(frozen=True)
class Kolom:
    """Satu kolom tabel ringkasan: judul, keterangan kecil, arah nilai terbaik
    ("max" atau "min"), dan cara menampilkan nilainya dari satu baris."""
    judul: str
    ket: str = ""
    terbaik: str = "max"
    tampil: Callable = lambda b, kolom: angka(getattr(b, kolom), 3)


def _tampil_tinggi_rendah(b, kolom: str) -> str:
    return (f"{_persen(b.Persen_Tinggi_jadi_Rendah)}"
            f"<small>{angka(b.Tinggi_jadi_Rendah)} dari {angka(b.N_Tinggi)}</small>")


# kolom CSV -> Kolom
KOLOM_RINGKASAN = {
    "Akurasi": Kolom("Akurasi"),
    "Precision_Macro": Kolom("Precision", "macro"),
    "Recall_Macro": Kolom("Recall", "macro"),
    "F1_Macro": Kolom("F1", "macro"),
    "AUC_Macro": Kolom("AUC", "macro"),
    "Cohen_Kappa": Kolom("Cohen's Kappa"),
    "MCC": Kolom("MCC"),
}
KOLOM_PER_BULAN = {
    "Akurasi": Kolom("Akurasi"),
    "F1_Macro": Kolom("F1", "macro"),
    "Persen_Tinggi_jadi_Rendah": Kolom("Tinggi → Rendah", "grid Tinggi", "min",
                                       _tampil_tinggi_rendah),
}
KOLOM_PER_KELAS = {"Precision": "Precision", "Recall": "Recall", "F1": "F1", "AUC": "AUC"}

# Kolom yang harus ada di CSV eksternal supaya komponen tampilan bisa dipakai.
WAJIB_EKSTERNAL = ["Periode", "Model", *KOLOM_RINGKASAN, "Tinggi_jadi_Rendah",
                   "Persen_Tinggi_jadi_Rendah", "Jumlah_data"]


def _nama_skenario(skenario: str) -> str:
    """"DENGAN SMOTENC" -> "Dengan SMOTENC"."""
    awal, *sisa = skenario.split()
    return " ".join([awal.capitalize(), *sisa])


def _html_nama(b) -> str:
    """Nama model + keterangan (skenario atau periode), dengan chip "Model final"."""
    chip = f'<span class="pf-chip">{b.Label_final}</span>' if b.Final else ""
    return (f'<div class="pf-nama">{b.Model}{chip}</div>'
            f'<div class="pf-skenario">{b.Keterangan}</div>')


# ---- penyiapan baris: internal dan eksternal dibuat seragam --------------------------
# Setiap baris ringkasan diberi tiga kolom tampilan:
#   Keterangan  teks di bawah nama model (skenario / periode)
#   Final       True bila baris ini model final
#   Label_final teks chip untuk baris model final
#   N_Tinggi    jumlah data kelas Tinggi, dibaca dari CSV per kelas

def _baris_internal(sumber: SumberDataService, model_final: str) -> pd.DataFrame:
    r = sumber.metrik_ringkasan()
    return r.assign(
        Keterangan=r["Skenario"].map(_nama_skenario),
        Final=(r["Skenario"] == SKENARIO_FINAL) & (r["Model"] == model_final),
        Label_final=LABEL_FINAL_INTERNAL,
        N_Tinggi=[sumber.metrik_per_kelas(s, m).loc["Tinggi", "Jumlah_data"]
                  for s, m in zip(r["Skenario"], r["Model"])],
    )


def _rentang_eksternal(r: pd.DataFrame) -> str:
    """Nama rentang bulan pengujian eksternal dari kolom Periode, mis. "Juli 2026 –
    September 2026"."""
    bulan = sorted(p for p in r["Periode"].unique() if p != KESELURUHAN)
    if not bulan:
        return PERIODE_EKSTERNAL
    return f"{nama_periode(bulan[0])} – {nama_periode(bulan[-1])}"


def _baris_eksternal(sumber: SumberDataService, r: pd.DataFrame, model_final: str) -> pd.DataFrame:
    rentang = _rentang_eksternal(r)
    return r.assign(
        Keterangan=[rentang if p == KESELURUHAN else nama_periode(p) for p in r["Periode"]],
        Final=r["Model"] == model_final,
        Label_final=LABEL_FINAL_EKSTERNAL,
        N_Tinggi=[sumber.metrik_eksternal_per_kelas(p, m).loc["Tinggi", "Jumlah_data"]
                  for p, m in zip(r["Periode"], r["Model"])],
    )


# ---- 1. tabel ringkasan ------------------------------------------------------------

def _terbaik(baris: pd.DataFrame, kolom: dict[str, Kolom]) -> dict:
    """Nilai terbaik tiap kolom (terbesar atau terkecil, sesuai Kolom.terbaik)."""
    return {c: baris[c].max() if k.terbaik == "max" else baris[c].min()
            for c, k in kolom.items()}


def _unggul_semua(baris: pd.DataFrame, kolom: dict[str, Kolom] = KOLOM_RINGKASAN) -> str | None:
    """Nama model yang sendirian memegang nilai terbaik di setiap kolom, atau None.
    Hanya membandingkan nilai yang sudah ada di CSV."""
    terbaik = _terbaik(baris, kolom)
    pemenang = set()
    for c in kolom:
        model = baris.loc[baris[c] == terbaik[c], "Model"]
        if len(model) != 1:
            return None
        pemenang.add(model.iloc[0])
    return pemenang.pop() if len(pemenang) == 1 else None


def _html_ringkasan(baris: pd.DataFrame, judul: str, ket: str,
                    kolom: dict[str, Kolom] = KOLOM_RINGKASAN, catatan: str = "") -> str:
    kepala = "".join(f"<th>{k.judul}<small>{k.ket}</small></th>" for k in kolom.values())
    terbaik = _terbaik(baris, kolom)
    isi = ""
    for b in baris.itertuples():
        sel = "".join(
            f"<td>{'<b>' if getattr(b, c) == terbaik[c] else ''}{k.tampil(b, c)}</td>"
            for c, k in kolom.items())
        isi += f'<tr class="{"pf-final" if b.Final else ""}"><td>{_html_nama(b)}</td>{sel}</tr>'
    return (
        f'<div class="kl-h2">{judul}</div>'
        f'<div class="kl-kecil">{ket} Angka tebal = terbaik di kolomnya.</div>'
        f'<div class="pf-gulir"><table class="pf-tabel"><thead><tr>'
        f'<th>Model</th>{kepala}</tr></thead><tbody>{isi}</tbody></table></div>'
        + (f'<div class="pf-catatan">{catatan}</div>' if catatan else "")
    )


# ---- 2. per kelas, model final ----------------------------------------------------

def _html_per_kelas(per_kelas: pd.DataFrame, model_final: str, ket: str) -> str:
    kepala = "".join(f"<th>{j}</th>" for j in KOLOM_PER_KELAS.values())
    isi = "".join(
        f'<tr><td><span class="pf-kelas"><i style="background:{WARNA[k]}"></i>{k}</span></td>'
        + "".join(f"<td>{angka(r[c], 3)}</td>" for c in KOLOM_PER_KELAS)
        + f'<td>{_persen(r["Tingkat_Kesalahan"])}</td><td>{angka(r["Jumlah_data"])}</td></tr>'
        for k, r in per_kelas.iterrows())
    return (
        f'<div class="kl-h2">Per kelas · {model_final}</div>'
        f'<div class="kl-kecil">Model final, {ket}. Tingkat kesalahan = bagian data kelas '
        'itu yang diklasifikasikan ke kelas lain.</div>'
        f'<div class="pf-gulir"><table class="pf-tabel"><thead><tr><th>Kelas</th>{kepala}'
        f'<th>Tingkat<small>kesalahan</small></th><th>Jumlah<small>data</small></th>'
        f'</tr></thead><tbody>{isi}</tbody></table></div>'
    )


# ---- 3. confusion matrix, model final -----------------------------------------------

def _kelas_sel(sebenarnya: str, prediksi: str) -> str:
    """Kelas CSS sel: diagonal = benar; Tinggi diprediksi Rendah = kesalahan berbahaya."""
    if sebenarnya == prediksi:
        return "pf-cm-sel pf-cm-benar"
    if (sebenarnya, prediksi) == ("Tinggi", "Rendah"):
        return "pf-cm-sel pf-cm-bahaya"
    return "pf-cm-sel"


def _html_confusion(cm: pd.DataFrame, model_final: str, ket: str) -> str:
    kepala = ('<div></div>'
              + "".join(f'<div class="pf-cm-sumbu">{k}</div>' for k in cm.index)
              + '<div class="pf-cm-sumbu">Jumlah data</div>')
    isi = ""
    for sebenarnya, r in cm.iterrows():
        isi += f'<div class="pf-cm-label">{sebenarnya}</div>'
        for prediksi in cm.index:
            latar = f' style="background:{WARNA_LATAR[prediksi]}"' if sebenarnya == prediksi else ""
            isi += (f'<div class="{_kelas_sel(sebenarnya, prediksi)}"{latar}>'
                    f'{angka(r[f"Prediksi_{prediksi}"])}</div>')
        isi += f'<div class="pf-cm-jumlah">{angka(r["Jumlah_data"])}</div>'
    return (
        f'<div class="kl-h2">Confusion matrix · {model_final}</div>'
        f'<div class="kl-kecil">{ket[0].upper() + ket[1:]}. Baris = kelas sebenarnya, '
        'kolom = prediksi. Sel berwarna = prediksi benar; bingkai merah = Tinggi yang '
        'diprediksi Rendah.</div>'
        '<div class="pf-gulir"><div class="pf-cm-judul">Prediksi →</div>'
        f'<div class="pf-cm">{kepala}{isi}</div></div>'
    )


# ---- 4. kesalahan paling berbahaya: Tinggi -> Rendah --------------------------------

def _catatan_smotenc(baris: pd.DataFrame) -> str:
    """Internal: perubahan Persen_Tinggi_jadi_Rendah dari tanpa ke dengan SMOTENC."""
    bagian = []
    for model, data in baris.groupby("Model", sort=False):
        sebelum = data.loc[data.Skenario != SKENARIO_FINAL, "Persen_Tinggi_jadi_Rendah"]
        sesudah = data.loc[data.Skenario == SKENARIO_FINAL, "Persen_Tinggi_jadi_Rendah"]
        if sebelum.empty or sesudah.empty:
            continue
        arah = "turun" if sesudah.iloc[0] < sebelum.iloc[0] else "naik"
        bagian.append(f"{model} {arah} dari <b>{_persen(sebelum.iloc[0])}</b> "
                      f"menjadi <b>{_persen(sesudah.iloc[0])}</b>")
    return "Dengan SMOTENC, " + "; ".join(bagian) + "." if bagian else ""


def _catatan_eksternal(internal: pd.DataFrame, eksternal: pd.DataFrame) -> str:
    """Eksternal: bandingkan persen Tinggi -> Rendah model final dengan pengujian internal."""
    a = internal.loc[internal.Final]
    b = eksternal.loc[eksternal.Final & (eksternal.Periode == KESELURUHAN)]
    if a.empty or b.empty:
        return ""
    a, b = a.iloc[0], b.iloc[0]
    return (f"Model final salah mengklasifikasikan <b>{_persen(b.Persen_Tinggi_jadi_Rendah)}"
            f"</b> grid Tinggi menjadi Rendah pada pengujian eksternal, dibanding "
            f"<b>{_persen(a.Persen_Tinggi_jadi_Rendah)}</b> pada pengujian internal. "
            f"Komposisi kelasnya berbeda: {angka(b.N_Tinggi)} dari {angka(b.Jumlah_data)} "
            "grid-bulan eksternal berkelas Tinggi.")


def _html_bahaya(baris: pd.DataFrame, catatan: str) -> str:
    batang = "".join(
        f'<div class="pf-bahaya{" pf-final" if b.Final else ""}">'
        f'<div class="pf-bahaya-atas"><div>{_html_nama(b)}</div>'
        f'<div class="pf-bahaya-nilai">{_persen(b.Persen_Tinggi_jadi_Rendah)}'
        f'<small>{angka(b.Tinggi_jadi_Rendah)} dari {angka(b.N_Tinggi)} grid Tinggi</small>'
        f'</div></div>'
        f'<div class="pf-batang"><i style="width:{b.Persen_Tinggi_jadi_Rendah * 100:.2f}%;'
        f'background:{WARNA["Tinggi"]}"></i></div></div>'
        for b in baris.itertuples())
    catatan = f'<div class="pf-catatan">{catatan}</div>' if catatan else ""
    return (
        '<div class="kl-h2">Kesalahan paling berbahaya: Tinggi → Rendah</div>'
        '<div class="kl-kecil">Grid yang sebenarnya rawan tinggi tetapi diklasifikasikan '
        'rendah, sehingga bisa luput dari kewaspadaan.</div>'
        f'{batang}{catatan}'
    )


# ---- 5. cara membaca ----------------------------------------------------------------

def _html_cara_membaca(per_kelas: pd.DataFrame) -> str:
    n = per_kelas["Jumlah_data"]
    terbanyak = n.idxmax()
    return (
        '<div class="kl-h2">Cara membaca</div>'
        '<div class="pf-baca">'
        '<div><b>Kenapa macro, bukan weighted.</b> Data uji timpang: '
        f'{angka(n[terbanyak])} dari {angka(n.sum())} grid-bulan berkelas {terbanyak}. '
        'Rata-rata <i>weighted</i> diberi bobot sesuai jumlah data, jadi didominasi kelas '
        f'{terbanyak}. Rata-rata <i>macro</i> memberi bobot sama pada ketiga kelas, sehingga '
        'kelemahan pada kelas yang sedikit datanya tetap terlihat. Itu juga sebabnya akurasi '
        'tertinggi tidak otomatis berarti model terbaik.</div>'
        "<div><b>Cohen's Kappa.</b> Mengukur kesesuaian prediksi dengan label sebenarnya "
        'setelah dikurangi kesesuaian yang bisa terjadi secara kebetulan. Nilai 0 berarti '
        'tidak lebih baik daripada menebak sesuai proporsi kelas; 1 berarti sempurna.</div>'
        '<div><b>MCC.</b> Korelasi antara prediksi dan label sebenarnya, dari −1 sampai 1; '
        'tetap adil pada data yang timpang karena memperhitungkan semua sel confusion '
        'matrix.</div>'
        '<div><b>Model final</b> dipilih dari F1 macro tertinggi pada pengujian internal, '
        f'skenario {_nama_skenario(SKENARIO_FINAL)}. Kedua berkas .pkl yang diuji adalah '
        f'skenario {_nama_skenario(SKENARIO_FINAL)}.</div>'
        '</div>'
    )


# ---- susunan satu tab ---------------------------------------------------------------

def _render_isi(akhiran: str, tabel: list[str], per_kelas_html: str, confusion_html: str,
                bahaya_html: str, baca_html: str, tambahan: tuple[str, ...] = ()) -> None:
    """Susunan kartu yang sama untuk kedua tab. akhiran membedakan key container;
    tambahan = kartu pelengkap yang dirender sebelum "Cara membaca"."""
    for i, html in enumerate(tabel):
        with st.container(key=f"bento_pf_tabel{i}_{akhiran}"):
            st.markdown(html, unsafe_allow_html=True)
    kiri, kanan = st.columns([1.25, 1], gap="medium")
    with kiri:
        with st.container(key=f"bento_pf_kelas_{akhiran}"):
            st.markdown(per_kelas_html, unsafe_allow_html=True)
        with st.container(key=f"bento_pf_matriks_{akhiran}"):
            st.markdown(confusion_html, unsafe_allow_html=True)
    with kanan, st.container(key=f"bento_pf_bahaya_{akhiran}", height="stretch"):
        st.markdown(bahaya_html, unsafe_allow_html=True)
    for i, html in enumerate(tambahan):
        with st.container(key=f"bento_pf_tambahan{i}_{akhiran}"):
            st.markdown(html, unsafe_allow_html=True)
    with st.container(key=f"bento_pf_baca_{akhiran}"):
        st.markdown(baca_html, unsafe_allow_html=True)


def _render_internal(sumber: SumberDataService, model_final: str,
                     internal: pd.DataFrame) -> None:
    per_kelas = sumber.metrik_per_kelas(SKENARIO_FINAL, model_final)
    ket = f"skenario {_nama_skenario(SKENARIO_FINAL)}"
    n_uji = int(per_kelas["Jumlah_data"].sum())
    st.markdown(f'<div class="kl-kecil pf-ket-tab">{angka(n_uji)} grid-bulan dari grid yang '
                'dipisahkan dari data latih.</div>', unsafe_allow_html=True)
    _render_isi(
        "internal",
        [_html_ringkasan(internal, "Perbandingan empat skenario",
                         "Dua algoritma, masing-masing dilatih tanpa dan dengan SMOTENC.")],
        _html_per_kelas(per_kelas, model_final, ket),
        _html_confusion(sumber.confusion_matrix(SKENARIO_FINAL, model_final), model_final, ket),
        _html_bahaya(internal, _catatan_smotenc(internal)),
        _html_cara_membaca(per_kelas),
    )


def _render_eksternal(sumber: SumberDataService, model_final: str,
                      internal: pd.DataFrame) -> None:
    if sumber.berkas_eksternal_kurang():
        st.markdown('<div class="kl-kosong"><div class="kl-kosong-judul">Sedang diproses'
                    f'</div>Pengujian eksternal periode {PERIODE_EKSTERNAL} sedang diproses. '
                    'Hasilnya tampil di sini begitu tersedia.</div>', unsafe_allow_html=True)
        return
    ringkasan = sumber.metrik_eksternal_ringkasan()
    kurang = [k for k in WAJIB_EKSTERNAL if k not in ringkasan.columns]
    if kurang:
        st.warning(f"Berkas metrik eksternal tidak memuat kolom: {', '.join(kurang)}.",
                   icon=":material/error:")
        return

    eksternal = _baris_eksternal(sumber, ringkasan, model_final)
    keseluruhan = eksternal[eksternal.Periode == KESELURUHAN]
    per_bulan = eksternal[eksternal.Periode != KESELURUHAN]
    rentang = _rentang_eksternal(ringkasan)
    per_kelas = sumber.metrik_eksternal_per_kelas(KESELURUHAN, model_final)
    ket = f"periode {rentang}"

    # Ukuran data dibaca dari CSV: total grid-bulan, grid per bulan, banyak bulan.
    bulan_final = per_bulan[per_bulan.Model == model_final]
    ukuran = f"{angka(keseluruhan.Jumlah_data.iloc[0])} grid-bulan"
    if not bulan_final.empty:
        ukuran += (f" ({angka(bulan_final.Jumlah_data.iloc[0])} grid × "
                   f"{len(bulan_final)} bulan)")
    st.markdown(f'<div class="kl-kecil pf-ket-tab">Periode {rentang} · {ukuran}. Model hanya '
                'memprediksi dengan berkas .pkl yang sama, tidak dilatih ulang.</div>',
                unsafe_allow_html=True)

    tambahan = ()
    if not per_bulan.empty:
        tambahan = (_html_ringkasan(per_bulan, "Rincian per bulan",
                                    "Pelengkap tabel keseluruhan di atas.", KOLOM_PER_BULAN),)
    catatan = ""
    unggul = _unggul_semua(keseluruhan)
    if unggul and unggul != model_final:
        catatan = (f"Pada pengujian eksternal (keseluruhan {rentang}), <b>{unggul}</b> "
                   "memperoleh nilai lebih baik pada seluruh metrik, sehingga keunggulan "
                   f"{model_final} pada evaluasi internal tidak berlaku pada periode ini.")
    _render_isi(
        "eksternal",
        [_html_ringkasan(keseluruhan, f"Keseluruhan · {rentang}",
                         "Kedua model pada seluruh periode pengujian eksternal.",
                         catatan=catatan)],
        _html_per_kelas(per_kelas, model_final, ket),
        _html_confusion(sumber.confusion_matrix_eksternal(model_final), model_final, ket),
        _html_bahaya(keseluruhan, _catatan_eksternal(internal, eksternal)),
        _html_cara_membaca(per_kelas),
        tambahan,
    )


# ---- halaman ------------------------------------------------------------------------

def render(sumber: SumberDataService) -> None:
    model_final = sumber.model_terbaik()
    internal = _baris_internal(sumber, model_final)

    st.markdown(
        '<div class="kl-label">Performa model</div>'
        '<div class="kl-judul">Perbandingan performa model</div>'
        '<div class="kl-sub">Hasil pengujian internal dan eksternal kedua model.</div>',
        unsafe_allow_html=True,
    )
    with st.container(key="pf_tab"):
        tab_internal, tab_eksternal = st.tabs(["Pengujian internal", "Pengujian eksternal"])
    with tab_internal:
        _render_internal(sumber, model_final, internal)
    with tab_eksternal:
        _render_eksternal(sumber, model_final, internal)
