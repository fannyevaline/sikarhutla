"""Modul 8 - Perbandingan performa model.

Dua tab dengan susunan yang sama:
- Pengujian internal: data/model/metrik_lengkap_*.csv dan confusion_matrix.csv
  (baris dibedakan per Skenario).
- Pengujian eksternal: data/model/metrik_eksternal_*.csv dan
  confusion_matrix_eksternal.csv (baris dibedakan per Periode).

Halaman utama sengaja ringkas: angka sorotan, tiga temuan singkat, dan satu tabel
perbandingan. Grafik dan rincian lain baru muncul di jendela dialog saat pengguna
menekan tombol "Lihat ..." pada kartu detail.

Semua metrik dibaca dari CSV lewat SumberDataService; tidak ada metrik yang dihitung
ulang di sini. Yang dilakukan halaman ini hanya memilih baris, memformat angka,
menandai nilai terbaik, dan menghitung selisih/proporsi untuk keterangan (misalnya
persen tiap baris confusion matrix = isi sel / Jumlah_data).

Model final = skenario SKENARIO_FINAL dengan model F1-macro tertinggi pada pengujian
internal (SumberDataService.model_terbaik(), sama dengan yang dipakai untuk mewarnai
peta). Pengujian eksternal tidak memilih ulang model final.
"""
from dataclasses import dataclass
from typing import Callable

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from domain.konstanta import KELAS, SKENARIO_FINAL
from domain.sumber_data_service import SumberDataService
from modul.tampilan import (BULAN, WARNA, WARNA_MODEL, WARNA_TEKS, angka, gaya_grafik,
                            nama_periode)

PERIODE_EKSTERNAL = "Juli – September 2026"  # untuk keterangan saat berkasnya belum ada
KESELURUHAN = "Keseluruhan"  # nilai kolom Periode untuk gabungan seluruh bulan
MODEL = list(WARNA_MODEL)

# Ikon kartu temuan (path SVG Material Icons, viewBox 0 0 24 24)
IKON = {
    "seimbang": "M10 20h4V4h-4v16zm-6 0h4v-8H4v8zM16 9v11h4V9h-4z",
    "naik": "M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z",
    "awas": "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    "bintang": "M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 "
               "4.73L5.82 21z",
    "kalender": "M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 "
                "2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z",
}


def _persen(x: float, desimal: int = 2) -> str:
    return f"{angka(x * 100, desimal)}%"


def _selisih(d: float) -> str:
    """+0,008 / −0,012 (tanda minus tipografis)."""
    return f"{'+' if d >= 0 else '−'}{angka(abs(d), 3)}"


def _rgba(hex_warna: str, alfa: float) -> str:
    r, g, b = (int(hex_warna[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alfa:.2f})"


def _titik(model: str) -> str:
    return f'<i class="pf-titik" style="background:{WARNA_MODEL[model]}"></i>'


def _md(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


@dataclass(frozen=True)
class Kolom:
    """Satu kolom tabel ringkasan: judul, keterangan kecil, arah nilai terbaik
    ("max" atau "min"), cara menampilkan nilainya, dan penjelasan singkat yang
    muncul saat kursor diarahkan ke judul kolom."""
    judul: str
    ket: str = ""
    terbaik: str = "max"
    tampil: Callable = lambda b, kolom: angka(getattr(b, kolom), 3)
    info: str = ""


def _tampil_tinggi_rendah(b, kolom: str) -> str:
    return (f"{_persen(b.Persen_Tinggi_jadi_Rendah)}"
            f"<small>{angka(b.Tinggi_jadi_Rendah)} dari {angka(b.N_Tinggi)}</small>")


INFO = {
    "Akurasi": "Porsi seluruh grid-bulan yang kelasnya ditebak benar. Mudah tertipu bila "
               "data tidak seimbang.",
    "Precision": "Dari grid yang diprediksi masuk suatu kelas, berapa bagian yang benar. "
                 "Rata-rata macro: tiap kelas berbobot sama.",
    "Recall": "Dari grid yang sebenarnya masuk suatu kelas, berapa bagian yang dikenali. "
              "Rata-rata macro: tiap kelas berbobot sama.",
    "F1": "Rata-rata harmonis precision dan recall. Metrik utama pemilihan model.",
    "AUC": "Kemampuan memisahkan kelas dari probabilitas. 0,5 = acak, 1 = sempurna.",
    "Kappa": "Kecocokan dengan label setelah dikurangi faktor kebetulan. 0 = setara "
             "menebak, 1 = sempurna.",
    "MCC": "Korelasi prediksi dan label (−1 sampai 1); adil untuk data tidak seimbang.",
    "TR": "Grid Tinggi yang diprediksi Rendah. Kesalahan paling berbahaya; makin kecil "
          "makin baik.",
}

# kolom CSV -> Kolom
KOLOM_RINGKASAN = {
    "Akurasi": Kolom("Akurasi", info=INFO["Akurasi"]),
    "Precision_Macro": Kolom("Precision", "macro", info=INFO["Precision"]),
    "Recall_Macro": Kolom("Recall", "macro", info=INFO["Recall"]),
    "F1_Macro": Kolom("F1", "macro", info=INFO["F1"]),
    "AUC_Macro": Kolom("AUC", "macro", info=INFO["AUC"]),
    "Cohen_Kappa": Kolom("Cohen's Kappa", info=INFO["Kappa"]),
    "MCC": Kolom("MCC", info=INFO["MCC"]),
}
KOLOM_PER_BULAN = {
    "Akurasi": Kolom("Akurasi", info=INFO["Akurasi"]),
    "F1_Macro": Kolom("F1", "macro", info=INFO["F1"]),
    "AUC_Macro": Kolom("AUC", "macro", info=INFO["AUC"]),
    "Persen_Tinggi_jadi_Rendah": Kolom("Tinggi → Rendah", "grid Tinggi", "min",
                                       _tampil_tinggi_rendah, INFO["TR"]),
}
KOLOM_PER_KELAS = {"Precision": "Precision", "Recall": "Recall", "F1": "F1", "AUC": "AUC"}
# Baris tabel internal vs eksternal: kolom CSV -> (judul, arah nilai terbaik)
KOLOM_BANDING = {
    "Akurasi": ("Akurasi", "max"),
    "F1_Macro": ("F1 macro", "max"),
    "AUC_Macro": ("AUC macro", "max"),
    "Cohen_Kappa": ("Cohen's Kappa", "max"),
    "MCC": ("MCC", "max"),
    "Persen_Tinggi_jadi_Rendah": ("Tinggi → Rendah", "min"),
}

# Kolom yang harus ada di CSV eksternal supaya komponen tampilan bisa dipakai.
WAJIB_EKSTERNAL = ["Periode", "Model", *KOLOM_RINGKASAN, "Tinggi_jadi_Rendah",
                   "Persen_Tinggi_jadi_Rendah", "Jumlah_data"]


def _nama_skenario(skenario: str) -> str:
    """"DENGAN SMOTENC" -> "Dengan SMOTENC"."""
    awal, *sisa = skenario.split()
    return " ".join([awal.capitalize(), *sisa])


def _html_nama(b) -> str:
    """Nama model + keterangan (skenario atau periode), dengan chip "Model final"."""
    chip = '<span class="pf-chip">Model final</span>' if b.Final else ""
    return (f'<div class="pf-nama">{_titik(b.Model)}{b.Model}{chip}</div>'
            f'<div class="pf-skenario">{b.Keterangan}</div>')


# ---- penyiapan baris: internal dan eksternal dibuat seragam --------------------------
# Setiap baris ringkasan diberi kolom tampilan:
#   Keterangan  teks di bawah nama model (skenario / periode)
#   Final       True bila baris ini model final
#   N_Tinggi    jumlah data kelas Tinggi, dibaca dari CSV per kelas
#   Jumlah_data (internal) jumlah data uji, dibaca dari CSV per kelas

def _baris_internal(sumber: SumberDataService, model_final: str) -> pd.DataFrame:
    r = sumber.metrik_ringkasan()
    per_kelas = [sumber.metrik_per_kelas(s, m) for s, m in zip(r["Skenario"], r["Model"])]
    return r.assign(
        Keterangan=r["Skenario"].map(_nama_skenario),
        Final=(r["Skenario"] == SKENARIO_FINAL) & (r["Model"] == model_final),
        N_Tinggi=[k.loc["Tinggi", "Jumlah_data"] for k in per_kelas],
        Jumlah_data=[k["Jumlah_data"].sum() for k in per_kelas],
    )


def _rentang_eksternal(r: pd.DataFrame) -> str:
    """Nama rentang bulan pengujian eksternal dari kolom Periode, mis. "Juli –
    September 2026" (tahun ditulis sekali bila sama)."""
    bulan = sorted(p for p in r["Periode"].unique() if p != KESELURUHAN)
    if not bulan:
        return PERIODE_EKSTERNAL
    awal, akhir = bulan[0], bulan[-1]
    if awal[:4] == akhir[:4]:
        return f"{BULAN[int(awal[5:]) - 1]} – {nama_periode(akhir)}"
    return f"{nama_periode(awal)} – {nama_periode(akhir)}"


def _baris_eksternal(sumber: SumberDataService, r: pd.DataFrame, model_final: str) -> pd.DataFrame:
    rentang = _rentang_eksternal(r)
    return r.assign(
        Keterangan=[rentang if p == KESELURUHAN else nama_periode(p) for p in r["Periode"]],
        Final=r["Model"] == model_final,
        N_Tinggi=[sumber.metrik_eksternal_per_kelas(p, m).loc["Tinggi", "Jumlah_data"]
                  for p, m in zip(r["Periode"], r["Model"])],
    )


# ---- 1. sorotan: empat angka utama model final --------------------------------------

def _html_sorotan(baris: pd.DataFrame, ket_final: str) -> str:
    """Model final, F1 dan AUC macro-nya, serta persen Tinggi -> Rendah. baris = model
    final dan pembandingnya pada skenario/periode yang sama."""
    final = baris[baris.Final].iloc[0]
    lain = baris[~baris.Final]
    lain = lain.iloc[0] if not lain.empty else None

    def banding(kolom: str, persen: bool = False) -> str:
        if lain is None:
            return ""
        tampil = _persen(lain[kolom]) if persen else angka(lain[kolom], 3)
        return f"{_titik(lain.Model)}{lain.Model}: {tampil}"

    def selisih(kolom: str) -> str:
        if lain is None:
            return ""
        d = final[kolom] - lain[kolom]
        return f'<span class="pf-delta {"pf-naik" if d >= 0 else "pf-turun"}">{_selisih(d)}</span>'

    def kotak(label: str, nilai: str, sub: str, kelas: str = "", delta: str = "") -> str:
        return (f'<div class="pf-tile {kelas}"><div class="pf-tile-label">{label}</div>'
                f'<div class="pf-tile-nilai">{nilai}{delta}</div><small>{sub}</small></div>')

    return '<div class="pf-sorotan">' + "".join([
        kotak("Model final", final.Model, ket_final, "pf-tile-final"),
        kotak("F1 macro", angka(final.F1_Macro, 3), banding("F1_Macro"),
              delta=selisih("F1_Macro")),
        kotak("AUC macro", angka(final.AUC_Macro, 3), banding("AUC_Macro"),
              delta=selisih("AUC_Macro")),
        kotak("Tinggi → Rendah", _persen(final.Persen_Tinggi_jadi_Rendah),
              banding("Persen_Tinggi_jadi_Rendah", persen=True), "pf-tile-bahaya"),
    ]) + "</div>"


# ---- 2. temuan: tiga kartu singkat ---------------------------------------------------
# Satu temuan = (ikon, warna, angka besar, satu kalimat pendek)

def _html_temuan(butir: list[tuple[str, str, str, str]]) -> str:
    kartu = "".join(
        f'<div class="pf-temuan" style="--warna:{warna}">'
        f'<div class="pf-temuan-ikon"><svg viewBox="0 0 24 24"><path d="{IKON[ikon]}"/>'
        f'</svg></div><div><div class="pf-temuan-angka">{nilai}</div>'
        f'<div class="pf-temuan-teks">{teks}</div></div></div>'
        for ikon, warna, nilai, teks in butir)
    return f'<div class="pf-bagian">Temuan utama</div><div class="pf-temuan-baris">{kartu}</div>'


def _temuan_kelas_tersulit(per_kelas: pd.DataFrame, cm: pd.DataFrame) -> tuple:
    """Kelas dengan F1 terendah dan ke kelas mana sebagian besar salahnya."""
    k = per_kelas["F1"].idxmin()
    salah = cm.loc[k, [f"Prediksi_{p}" for p in KELAS if p != k]]
    tujuan = salah.idxmax().removeprefix("Prediksi_")
    return ("awas", WARNA_TEKS["Tinggi"],
            f"{angka(salah.max())} dari {angka(cm.loc[k, 'Jumlah_data'])}",
            f"grid {k} tertebak {tujuan}. {k} adalah kelas tersulit "
            f"(F1 {angka(per_kelas.loc[k, 'F1'], 3)}).")


def _temuan_internal(sumber: SumberDataService, internal: pd.DataFrame,
                     model_final: str) -> list[tuple]:
    final = internal[internal.Final].iloc[0]
    lain = internal[(internal.Skenario == SKENARIO_FINAL) & ~internal.Final].iloc[0]
    d = final.F1_Macro - lain.F1_Macro
    butir = [("seimbang", "#c2410c", _selisih(d),
              f"selisih F1 macro {model_final} atas {lain.Model}"
              + (". Tipis, keduanya hampir setara." if abs(d) < 0.02 else "."))]

    # Pengaruh SMOTENC: kelas yang F1-nya paling naik pada model final
    lain_skenario = [s for s in internal.Skenario.unique() if s != SKENARIO_FINAL]
    if lain_skenario:
        sebelum = sumber.metrik_per_kelas(lain_skenario[0], model_final)["F1"]
        sesudah = sumber.metrik_per_kelas(SKENARIO_FINAL, model_final)["F1"]
        k = (sesudah - sebelum).idxmax()
        butir.append(("naik", WARNA_TEKS["Rendah"],
                      f"{angka(sebelum[k], 3)} → {angka(sesudah[k], 3)}",
                      f"F1 kelas {k} pada {model_final} setelah SMOTENC diterapkan."))

    butir.append(_temuan_kelas_tersulit(sumber.metrik_per_kelas(SKENARIO_FINAL, model_final),
                                        sumber.confusion_matrix(SKENARIO_FINAL, model_final)))
    return butir


def _temuan_eksternal(sumber: SumberDataService, internal: pd.DataFrame,
                      keseluruhan: pd.DataFrame, model_final: str, rentang: str) -> list[tuple]:
    unggul = _unggul_semua(keseluruhan)
    if unggul:
        pertama = ("bintang", WARNA_MODEL[unggul], unggul,
                   f"unggul di semua metrik pada {rentang}.")
    else:
        b = keseluruhan.loc[keseluruhan.F1_Macro.idxmax()]
        pertama = ("bintang", WARNA_MODEL[b.Model], b.Model,
                   f"meraih F1 macro tertinggi pada {rentang}.")

    a = internal[internal.Final].iloc[0]
    b = keseluruhan[keseluruhan.Final].iloc[0]
    kedua = ("kalender", "#c2410c", _persen(b.N_Tinggi / b.Jumlah_data, 1),
             f"data uji berkelas Tinggi (internal {_persen(a.N_Tinggi / a.Jumlah_data, 1)}), "
             "jadi angkanya tampak lebih tinggi.")

    ketiga = _temuan_kelas_tersulit(sumber.metrik_eksternal_per_kelas(KESELURUHAN, model_final),
                                    sumber.confusion_matrix_eksternal(model_final))
    return [pertama, kedua, ketiga]


# ---- 3. tabel ringkasan ------------------------------------------------------------

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


def _html_tabel(baris: pd.DataFrame, kolom: dict[str, Kolom] = KOLOM_RINGKASAN) -> str:
    kepala = "".join(
        f'<th title="{k.info}"><span class="{"pf-info" if k.info else ""}">{k.judul}</span>'
        f"<small>{k.ket or '&nbsp;'}</small></th>"
        for k in kolom.values())
    terbaik = _terbaik(baris, kolom)
    isi = ""
    for b in baris.itertuples():
        sel = "".join(
            f"<td>{'<b>' if getattr(b, c) == terbaik[c] else ''}{k.tampil(b, c)}</td>"
            for c, k in kolom.items())
        isi += f'<tr class="{"pf-final" if b.Final else ""}"><td>{_html_nama(b)}</td>{sel}</tr>'
    return (f'<div class="pf-gulir"><table class="pf-tabel"><thead><tr>'
            f'<th>Model</th>{kepala}</tr></thead><tbody>{isi}</tbody></table></div>')


def _html_ringkasan(baris: pd.DataFrame, judul: str, ket: str) -> str:
    return (f'<div class="kl-h2">{judul}</div>'
            f'<div class="kl-kecil">{ket} Angka tebal = terbaik di kolomnya. Arahkan kursor '
            'ke judul kolom untuk arti metriknya.</div>' + _html_tabel(baris))


# ---- 4. isi dialog -----------------------------------------------------------------

def _grafik_f1_kelas(panel: dict[str, dict[str, pd.Series]]) -> go.Figure:
    """Batang F1 tiap kelas, dikelompokkan per kelas, satu warna per model.
    panel = {judul panel: {model: Series F1 berindeks KELAS}}; satu panel per skenario."""
    fig = make_subplots(rows=1, cols=len(panel), shared_yaxes=True,
                        subplot_titles=list(panel) if len(panel) > 1 else None,
                        horizontal_spacing=0.06)
    for i, (judul, per_model) in enumerate(panel.items(), 1):
        for model, f1 in per_model.items():
            fig.add_bar(
                x=KELAS, y=f1[KELAS], name=model, legendgroup=model, showlegend=i == 1,
                marker={"color": WARNA_MODEL[model], "line": {"width": 0}},
                text=[angka(v, 2) for v in f1[KELAS]], textposition="outside",
                textfont={"size": 11, "color": "#4f4842"}, cliponaxis=False,
                customdata=[[model, judul, angka(v, 3)] for v in f1[KELAS]],
                hovertemplate="<b>%{customdata[0]}</b> · %{x}<br>%{customdata[1]}<br>"
                              "F1 %{customdata[2]}<extra></extra>",
                row=1, col=i)
    fig.update_layout(**gaya_grafik(tinggi=380, margin_atas=72, legenda_y=1.16),
                      barmode="group", bargap=0.3, bargroupgap=0.08, barcornerradius=4,
                      separators=",.")
    fig.update_layout(legend={"x": 0, "xanchor": "left"})  # di kiri, jauh dari judul panel
    fig.update_annotations(font={"size": 12, "color": "#4f4842"}, yshift=6)
    fig.update_xaxes(showgrid=False, tickfont={"color": "#4f4842", "size": 12})
    fig.update_yaxes(range=[0, 1.08], dtick=0.25, gridcolor="#efe9e2", zeroline=False,
                     tickformat=".2f")
    fig.update_yaxes(title={"text": "F1", "font": {"size": 12}}, row=1, col=1)
    return fig


def _grafik_per_bulan(per_bulan: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for model in MODEL:
        d = per_bulan[per_bulan.Model == model]
        if d.empty:
            continue
        fig.add_bar(
            x=d.Keterangan, y=d.F1_Macro, name=model,
            marker={"color": WARNA_MODEL[model], "line": {"width": 0}},
            text=[angka(v, 3) for v in d.F1_Macro], textposition="outside",
            textfont={"size": 11, "color": "#4f4842"}, cliponaxis=False,
            customdata=[[model, angka(f, 3), angka(a, 3), _persen(t)]
                        for f, a, t in zip(d.F1_Macro, d.Akurasi, d.Persen_Tinggi_jadi_Rendah)],
            hovertemplate="<b>%{customdata[0]}</b> · %{x}<br>F1 macro %{customdata[1]}<br>"
                          "Akurasi %{customdata[2]}<br>Tinggi → Rendah %{customdata[3]}"
                          "<extra></extra>")
    fig.update_layout(**gaya_grafik(tinggi=300, margin_atas=40, legenda_y=1.08),
                      barmode="group", bargap=0.35, bargroupgap=0.08, barcornerradius=4,
                      separators=",.")
    fig.update_layout(legend={"x": 0, "xanchor": "left"})
    fig.update_xaxes(showgrid=False, tickfont={"color": "#4f4842", "size": 12})
    fig.update_yaxes(range=[0, 1], dtick=0.25, gridcolor="#efe9e2", zeroline=False,
                     tickformat=".2f", title={"text": "F1 macro", "font": {"size": 12}})
    return fig


def _grafik(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _html_per_kelas(per_model: dict[str, pd.DataFrame]) -> str:
    """Precision/Recall/F1/AUC tiap kelas untuk kedua model; nilai yang lebih baik
    di tiap pasangan ditebalkan."""
    kepala1 = "".join(f'<th colspan="{len(per_model)}" class="pf-grup">{j}</th>'
                      for j in KOLOM_PER_KELAS.values())
    kepala2 = "".join(f'<th>{_titik(m)}{"RF" if m == "Random Forest" else "XGB"}</th>'
                      for _ in KOLOM_PER_KELAS for m in per_model)
    isi = ""
    for k in KELAS:
        sel = ""
        for c in KOLOM_PER_KELAS:
            nilai = [df.loc[k, c] for df in per_model.values()]
            sel += "".join(f'<td class="{"pf-awal" if j == 0 else ""}">'
                           f'{"<b>" if v == max(nilai) else ""}{angka(v, 3)}</td>'
                           for j, v in enumerate(nilai))
        n = next(iter(per_model.values())).loc[k, "Jumlah_data"]
        isi += (f'<tr><td><span class="pf-kelas"><i style="background:{WARNA[k]}"></i>{k}</span>'
                f'</td>{sel}<td class="pf-awal">{angka(n)}</td></tr>')
    return (f'<div class="pf-gulir"><table class="pf-tabel pf-tabel-kelas"><thead>'
            f'<tr><th rowspan="2">Kelas</th>{kepala1}'
            f'<th rowspan="2">Jumlah<small>data</small></th></tr>'
            f'<tr>{kepala2}</tr></thead><tbody>{isi}</tbody></table></div>')


def _html_confusion(cm: pd.DataFrame, model: str, final: bool) -> str:
    """Satu confusion matrix: tiap sel berisi jumlah dan persen terhadap baris
    (kelas sebenarnya). Pekat warna mengikuti persen itu."""
    kepala = ('<div></div>'
              + "".join(f'<div class="pf-cm-sumbu">{k}</div>' for k in cm.index))
    isi = ""
    for sebenarnya, r in cm.iterrows():
        isi += f'<div class="pf-cm-label">{sebenarnya}</div>'
        for prediksi in cm.index:
            n = r[f"Prediksi_{prediksi}"]
            p = n / r["Jumlah_data"]
            if sebenarnya == prediksi:
                gaya, kelas = f"background:{_rgba(WARNA[prediksi], 0.12 + 0.6 * p)}", " pf-cm-benar"
            else:
                gaya, kelas = f"background:{_rgba('#78644f', 0.04 + 0.45 * p)}", ""
            if (sebenarnya, prediksi) == ("Tinggi", "Rendah"):
                kelas += " pf-cm-bahaya"
            isi += (f'<div class="pf-cm-sel{kelas}" style="{gaya}" '
                    f'title="{sebenarnya} diprediksi {prediksi}: {angka(n)} dari '
                    f'{angka(r["Jumlah_data"])}">'
                    f'{angka(n)}<small>{_persen(p, 1)}</small></div>')
    chip = '<span class="pf-chip">Model final</span>' if final else ""
    return (f'<div class="pf-cm-blok"><div class="pf-nama">{_titik(model)}{model}{chip}</div>'
            '<div class="pf-cm-judul">Prediksi →</div>'
            f'<div class="pf-cm">{kepala}{isi}</div></div>')


def _html_bahaya(baris: pd.DataFrame) -> str:
    return "".join(
        f'<div class="pf-bahaya{" pf-final" if b.Final else ""}">'
        f'<div class="pf-bahaya-atas"><div>{_html_nama(b)}</div>'
        f'<div class="pf-bahaya-nilai">{_persen(b.Persen_Tinggi_jadi_Rendah)}'
        f'<small>{angka(b.Tinggi_jadi_Rendah)} dari {angka(b.N_Tinggi)} grid Tinggi</small>'
        f'</div></div>'
        f'<div class="pf-batang"><i style="width:{b.Persen_Tinggi_jadi_Rendah * 100:.2f}%;'
        f'background:{WARNA["Tinggi"]}"></i></div></div>'
        for b in baris.itertuples())


def _html_banding(a: pd.Series, b: pd.Series) -> str:
    """Model final: metrik internal (a) vs eksternal (b), plus komposisi kelas Tinggi."""
    isi = ""
    for c, (judul, arah) in KOLOM_BANDING.items():
        persen = c.startswith("Persen")
        tampil = _persen if persen else (lambda x: angka(x, 3))
        d = b[c] - a[c]
        baik = d >= 0 if arah == "max" else d <= 0
        tampil_d = (f"{'+' if d >= 0 else '−'}{angka(abs(d) * 100, 2)} poin" if persen
                    else _selisih(d))
        isi += (f'<tr><td>{judul}</td><td>{tampil(a[c])}</td><td>{tampil(b[c])}</td>'
                f'<td><span class="pf-delta {"pf-naik" if baik else "pf-turun"}">{tampil_d}'
                '</span></td></tr>')
    isi += (f'<tr class="pf-baris-ket"><td>Porsi kelas Tinggi<small>di data uji</small></td>'
            f'<td>{_persen(a.N_Tinggi / a.Jumlah_data, 1)}</td>'
            f'<td>{_persen(b.N_Tinggi / b.Jumlah_data, 1)}</td><td></td></tr>')
    return ('<div class="pf-gulir"><table class="pf-tabel pf-tabel-rapat"><thead><tr>'
            '<th>Metrik</th><th>Internal</th><th>Eksternal</th><th>Selisih</th>'
            f'</tr></thead><tbody>{isi}</tbody></table></div>')


def _html_cara_membaca(per_kelas: pd.DataFrame) -> str:
    n = per_kelas["Jumlah_data"]
    terbanyak = n.idxmax()
    butir = [
        ("Precision", "Dari grid yang <i>diprediksi</i> masuk suatu kelas, berapa yang benar. "
                      "Rendah = banyak peringatan palsu."),
        ("Recall", "Dari grid yang <i>sebenarnya</i> masuk suatu kelas, berapa yang dikenali. "
                   "Paling penting untuk kelas Tinggi."),
        ("F1", "Gabungan precision dan recall; tinggi hanya bila keduanya baik. Metrik utama "
               "pemilihan model."),
        ("AUC", "Kemampuan memisahkan kelas dari probabilitas. 0,5 = acak, 1 = sempurna."),
        ("Macro, bukan weighted", f"{angka(n[terbanyak])} dari {angka(n.sum())} data uji "
                                  f"berkelas {terbanyak}. Macro memberi bobot sama pada tiap "
                                  "kelas, jadi kelemahan kelas kecil tetap terlihat."),
        ("Cohen's Kappa", "Kecocokan setelah dikurangi faktor kebetulan. 0 = setara menebak, "
                          "1 = sempurna."),
        ("MCC", "Korelasi prediksi dan label, −1 sampai 1. Adil untuk data tidak seimbang."),
        ("SMOTENC", "Menambah contoh sintetis kelas minoritas pada data latih saja. Data uji "
                    "tidak diubah."),
        ("Model final", f"F1 macro tertinggi pada pengujian internal skenario "
                        f"{_nama_skenario(SKENARIO_FINAL)}. Berkas .pkl aplikasi berasal dari "
                        "skenario ini."),
    ]
    isi = "".join(f'<div class="pf-baca-butir"><b>{judul}</b><div>{teks}</div></div>'
                  for judul, teks in butir)
    return f'<div class="pf-baca">{isi}</div>'


@st.dialog("F1 per kelas", width="large")
def _dialog_f1(panel: dict[str, dict[str, pd.Series]], ket: str) -> None:
    _md(f'<div class="kl-kecil">{ket} Batang lebih tinggi = lebih baik.</div>')
    _grafik(_grafik_f1_kelas(panel))


@st.dialog("Metrik per kelas dan confusion matrix", width="large")
def _dialog_kelas(pilihan: dict[str, Callable], model_final: str) -> None:
    """pilihan = {label: fungsi -> (metrik per kelas per model, confusion matrix per
    model)}. Lebih dari satu pilihan -> muncul pemilih skenario."""
    label = list(pilihan)
    pilih = label[0]
    if len(label) > 1:
        pilih = st.segmented_control("Skenario", label, default=label[0],
                                     key="pf_skenario_dialog") or label[0]
    per_model, cm = pilihan[pilih]()
    _md('<div class="kl-h3">Metrik per kelas</div>'
        '<div class="kl-kecil">Nilai yang lebih baik di tiap pasangan ditebalkan.</div>'
        + _html_per_kelas(per_model)
        + '<div class="kl-h3 pf-jarak">Confusion matrix</div>'
        '<div class="kl-kecil">Baris = kelas sebenarnya, kolom = prediksi. Persen dihitung '
        'per baris. Bingkai merah = grid Tinggi yang diprediksi Rendah.</div>'
        '<div class="pf-cm-dua">'
        + "".join(_html_confusion(cm[m], m, m == model_final) for m in cm)
        + '</div>')


@st.dialog("Kesalahan paling berbahaya: Tinggi → Rendah", width="large")
def _dialog_bahaya(baris: pd.DataFrame) -> None:
    _md('<div class="kl-kecil">Grid yang sebenarnya Tinggi tetapi diprediksi Rendah, sehingga '
        'bisa luput dari kewaspadaan. Makin kecil makin baik.</div>' + _html_bahaya(baris))


@st.dialog("Performa per bulan", width="large")
def _dialog_bulan(per_bulan: pd.DataFrame) -> None:
    _md('<div class="kl-kecil">F1 macro kedua model tiap bulan. Arahkan kursor ke batang '
        'untuk akurasi dan kesalahan Tinggi → Rendah.</div>')
    _grafik(_grafik_per_bulan(per_bulan))
    _md(_html_tabel(per_bulan, KOLOM_PER_BULAN))


@st.dialog("Internal vs eksternal", width="large")
def _dialog_banding(a: pd.Series, b: pd.Series, rentang: str) -> None:
    _md(f'<div class="kl-kecil">{a.Model} (model final) pada data uji internal dan eksternal '
        f'({rentang}). Hijau = lebih baik pada pengujian eksternal.</div>'
        + _html_banding(a, b)
        + '<div class="pf-catatan">Komposisi kelas kedua data uji sangat berbeda, jadi '
        'kenaikan angka eksternal belum tentu berarti model membaik.</div>')


@st.dialog("Cara membaca metrik", width="large")
def _dialog_baca(per_kelas: pd.DataFrame) -> None:
    _md(_html_cara_membaca(per_kelas))


# ---- 5. kartu "lihat lebih detail" --------------------------------------------------
# Satu kartu = (ikon Material, judul, keterangan, label tombol, fungsi dialog, argumen)

def _render_detail(akhiran: str, kartu: list[tuple]) -> None:
    _md('<div class="pf-bagian">Lihat lebih detail</div>')
    per_baris = 4 if len(kartu) == 4 else 3  # empat kartu muat satu baris
    for awal in range(0, len(kartu), per_baris):
        kolom = st.columns(per_baris, gap="medium")
        for i, (kol, (ikon, judul, ket, tombol, dialog, args)) in enumerate(
                zip(kolom, kartu[awal:awal + per_baris]), awal):
            with kol, st.container(key=f"bento_pf_detail_{akhiran}_{i}", height="stretch"):
                _md(f'<div class="pf-detail-judul">{judul}</div>'
                    f'<div class="pf-detail-ket">{ket}</div>')
                if st.button(tombol, key=f"pf_btn_{akhiran}_{i}", icon=ikon,
                             width="stretch"):
                    dialog(*args)


# ---- susunan tab --------------------------------------------------------------------

def _render_internal(sumber: SumberDataService, model_final: str,
                     internal: pd.DataFrame) -> None:
    skenario = list(dict.fromkeys(internal.Skenario))
    urut = [SKENARIO_FINAL] + [s for s in skenario if s != SKENARIO_FINAL]
    per_kelas_final = sumber.metrik_per_kelas(SKENARIO_FINAL, model_final)

    _md(f'<div class="pf-ket-tab">Data uji: <b>{angka(per_kelas_final["Jumlah_data"].sum())} '
        'grid-bulan</b> dari grid yang tidak dipakai saat pelatihan.</div>')
    _md(_html_sorotan(internal[internal.Skenario == SKENARIO_FINAL],
                      f"Skenario {_nama_skenario(SKENARIO_FINAL)} · F1 macro tertinggi"))
    _md(_html_temuan(_temuan_internal(sumber, internal, model_final)))
    with st.container(key="bento_pf_tabel_internal"):
        _md(_html_ringkasan(internal, "Perbandingan empat skenario",
                            "Kedua model, dilatih tanpa dan dengan SMOTENC."))

    def kelas(s):
        return (lambda: ({m: sumber.metrik_per_kelas(s, m) for m in MODEL},
                         {m: sumber.confusion_matrix(s, m) for m in MODEL}))

    _render_detail("internal", [
        (":material/bar_chart:", "F1 per kelas",
         "Kedua model, tanpa vs dengan SMOTENC.", "Lihat grafik", _dialog_f1,
         ({_nama_skenario(s): {m: sumber.metrik_per_kelas(s, m)["F1"] for m in MODEL}
           for s in urut[::-1]}, "Kedua model, tanpa dan dengan SMOTENC.")),
        (":material/grid_view:", "Confusion matrix",
         "Benar dan salah tiap kelas, kedua model.", "Lihat tabel",
         _dialog_kelas, ({_nama_skenario(s): kelas(s) for s in urut}, model_final)),
        (":material/warning:", "Tinggi → Rendah",
         "Kesalahan paling berbahaya, empat skenario.", "Lihat grafik", _dialog_bahaya,
         (internal,)),
        (":material/menu_book:", "Cara membaca metrik",
         "Arti precision, recall, F1, AUC, dll.", "Lihat penjelasan", _dialog_baca,
         (per_kelas_final,)),
    ])


def _render_eksternal(sumber: SumberDataService, model_final: str,
                      internal: pd.DataFrame) -> None:
    if sumber.berkas_eksternal_kurang():
        _md('<div class="kl-kosong"><div class="kl-kosong-judul">Sedang diproses</div>'
            f'Pengujian eksternal periode {PERIODE_EKSTERNAL} sedang diproses. Hasilnya '
            'tampil di sini begitu tersedia.</div>')
        return
    ringkasan = sumber.metrik_eksternal_ringkasan()
    kurang = [k for k in WAJIB_EKSTERNAL if k not in ringkasan.columns]
    if kurang:
        st.warning(f"Berkas metrik eksternal tidak memuat kolom: {', '.join(kurang)}.",
                   icon=":material/error:")
        return

    eksternal = _baris_eksternal(sumber, ringkasan, model_final)
    keseluruhan = eksternal[eksternal.Periode == KESELURUHAN]
    per_bulan = eksternal[eksternal.Periode != KESELURUHAN].sort_values("Periode")
    rentang = _rentang_eksternal(ringkasan)
    per_kelas_final = sumber.metrik_eksternal_per_kelas(KESELURUHAN, model_final)

    # Ukuran data dibaca dari CSV: total grid-bulan, grid per bulan, banyak bulan.
    bulan_final = per_bulan[per_bulan.Model == model_final]
    ukuran = f"<b>{angka(keseluruhan.Jumlah_data.iloc[0])} grid-bulan</b>"
    if not bulan_final.empty:
        ukuran += (f" ({angka(bulan_final.Jumlah_data.iloc[0])} grid × "
                   f"{len(bulan_final)} bulan)")
    _md(f'<div class="pf-ket-tab">Data uji: {ukuran} periode {rentang}, di luar rentang data '
        'latih. Model tidak dilatih ulang.</div>')
    _md(_html_sorotan(keseluruhan, "Ditetapkan dari pengujian internal"))
    _md(_html_temuan(_temuan_eksternal(sumber, internal, keseluruhan, model_final, rentang)))
    with st.container(key="bento_pf_tabel_eksternal"):
        _md(_html_ringkasan(keseluruhan, f"Keseluruhan · {rentang}",
                            "Kedua model pada seluruh bulan pengujian eksternal."))

    kartu = [
        (":material/bar_chart:", "F1 per kelas",
         "Grafik kedua model untuk tiap kelas.", "Lihat grafik", _dialog_f1,
         ({rentang: {m: sumber.metrik_eksternal_per_kelas(KESELURUHAN, m)["F1"]
                     for m in MODEL}}, f"Kedua model, keseluruhan {rentang}.")),
        (":material/grid_view:", "Confusion matrix",
         "Benar dan salah tiap kelas, kedua model.", "Lihat tabel",
         _dialog_kelas,
         ({rentang: lambda: ({m: sumber.metrik_eksternal_per_kelas(KESELURUHAN, m)
                              for m in MODEL},
                             {m: sumber.confusion_matrix_eksternal(m) for m in MODEL})},
          model_final)),
        (":material/warning:", "Tinggi → Rendah",
         "Kesalahan paling berbahaya pada kedua model.", "Lihat grafik", _dialog_bahaya,
         (keseluruhan,)),
        (":material/compare_arrows:", "Internal vs eksternal",
         "Model final pada dua data uji yang berbeda.", "Lihat tabel", _dialog_banding,
         (internal[internal.Final].iloc[0], keseluruhan[keseluruhan.Final].iloc[0], rentang)),
        (":material/menu_book:", "Cara membaca metrik",
         "Arti precision, recall, F1, AUC, dll.", "Lihat penjelasan", _dialog_baca,
         (per_kelas_final,)),
    ]
    if not per_bulan.empty:
        kartu.insert(3, (":material/calendar_month:", "Per bulan",
                         "F1 macro dan kesalahan tiap bulan.", "Lihat grafik", _dialog_bulan,
                         (per_bulan,)))
    _render_detail("eksternal", kartu)


# ---- halaman ------------------------------------------------------------------------

def render(sumber: SumberDataService) -> None:
    model_final = sumber.model_terbaik()
    internal = _baris_internal(sumber, model_final)

    _md('<div class="kl-label">Performa model</div>'
        '<div class="kl-judul">Perbandingan performa model</div>'
        '<div class="kl-sub">Seberapa tepat Random Forest dan XGBoost mengenali tingkat '
        'kerawanan, pada data uji internal dan pada periode baru di luar data latih.</div>')
    with st.container(key="pf_tab"):
        tab_internal, tab_eksternal = st.tabs(["Pengujian internal", "Pengujian eksternal"])
    with tab_internal:
        _render_internal(sumber, model_final, internal)
    with tab_eksternal:
        _render_eksternal(sumber, model_final, internal)
