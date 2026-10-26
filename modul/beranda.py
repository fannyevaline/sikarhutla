"""Modul 1 - Beranda."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from domain.konstanta import KELAS
from domain.sumber_data_service import SumberDataService
from modul.tampilan import (BULAN, SUMBER_DATA, WARNA, WARNA_LATAR, WARNA_TEKS,
                            gaya_grafik, nama_periode)

LANGKAH = [
    ("Pilih grid", "Lewat peta, daftar wilayah, atau koordinat"),
    ("Pilih periode", "Bulan lampau, bulan berjalan, atau bulan yang terjangkau ramalan"),
    ("Jalankan klasifikasi", "Kedua model dijalankan sekaligus"),
    ("Baca hasilnya", "Kategori, confidence, dan nilai variabel"),
]


def _html_hero(n_grid: int, awal: str, akhir: str) -> str:
    pil = "".join(
        f'<span class="bd-pil"><i></i>{teks}</span>'
        for teks in [
            f"{n_grid} grid 0,5°",
            f"{nama_periode(awal)} – {nama_periode(akhir)}",
            "Random Forest &amp; XGBoost",
        ]
    )
    return (
        '<div class="bd-label">Dashboard klasifikasi</div>'
        '<div class="bd-judul">Kerawanan karhutla Kalimantan</div>'
        '<div class="bd-sub">Klasifikasi tingkat kerawanan per grid dengan '
        'Random Forest dan XGBoost</div>'
        f'<div class="bd-pil-grup">{pil}</div>'
    )


def _tren(tren: pd.DataFrame, periode: str) -> go.Figure:
    """Batang bertumpuk jumlah grid per kelas tiap bulan. Rendah digambar pucat supaya
    naik-turun Tinggi dan Sedang tetap menonjol. Puncak Tinggi tiap tahun diberi label;
    periode terpilih disorot."""
    x = pd.to_datetime(tren.index + "-01")
    nama = [nama_periode(p) for p in tren.index]
    redup = [1.0 if p == periode else 0.55 for p in tren.index]
    rincian = list(zip(nama, tren["Tinggi"], tren["Sedang"], tren["Rendah"]))
    tooltip = ("<b>%{customdata[0]}</b><br>"
               "<span style='color:" + WARNA["Tinggi"] + "'>■</span> Tinggi: %{customdata[1]} grid<br>"
               "<span style='color:" + WARNA["Sedang"] + "'>■</span> Sedang: %{customdata[2]} grid<br>"
               "<span style='color:" + WARNA["Rendah"] + "'>■</span> Rendah: %{customdata[3]} grid"
               "<extra></extra>")

    redup_rendah = [0.45 if p == periode else 0.2 for p in tren.index]
    fig = go.Figure()
    for k in KELAS[::-1]:  # Tinggi di dasar, Rendah di atas
        fig.add_bar(x=x, y=tren[k], name=k, customdata=rincian, hovertemplate=tooltip,
                    marker={"color": WARNA[k], "line": {"width": 0},
                            "opacity": redup_rendah if k == "Rendah" else redup})

    # Latar berselang-seling per tahun supaya batas tahun mudah dibaca
    for tahun in sorted({t.year for t in x}):
        if tahun % 2 == 0:
            fig.add_vrect(x0=f"{tahun - 1}-12-16", x1=f"{tahun}-12-16", layer="below",
                          fillcolor="rgba(120,100,80,0.05)", line_width=0)

    # Label puncak grid Tinggi tiap tahun
    seri = pd.Series(tren["Tinggi"].values, index=x)
    for tahun, kelompok in seri.groupby(seri.index.year):
        puncak = kelompok.idxmax()
        if kelompok.max() == 0:
            continue
        total = int(tren.loc[puncak.strftime("%Y-%m"), ["Tinggi", "Sedang"]].sum())
        fig.add_annotation(
            x=puncak, y=total, yshift=4, showarrow=False, yanchor="bottom",
            text=f"<b>{int(kelompok.max())}</b> {BULAN[puncak.month - 1][:3]}",
            font={"size": 11, "color": "#4f4842"},
        )

    fig.update_layout(
        **gaya_grafik(tinggi=320, margin_atas=24, legenda_y=1.04),
        barmode="stack", bargap=0.22, barcornerradius=3,
        xaxis={"showgrid": False, "tickformat": "%Y", "dtick": "M12", "tick0": "2021-01-01",
               "range": [x.min() - pd.Timedelta(days=20), x.max() + pd.Timedelta(days=20)]},
        yaxis={"title": {"text": "Jumlah grid"}, "gridcolor": "#efe9e2", "zeroline": False,
               "rangemode": "tozero"},
    )
    return fig


def _html_statistik(periode: str, ringkasan, total: int, n_grid: int) -> str:
    urutan = ["Tinggi", "Sedang", "Rendah"]
    stat = "".join(
        f'<div class="bd-stat" style="background:{WARNA_LATAR[k]};border-color:{WARNA[k]}">'
        f'<div class="bd-stat-label" style="color:{WARNA_TEKS[k]}">'
        f'Grid berkategori {k.lower()}</div>'
        f'<div class="bd-stat-nilai" style="color:{WARNA_TEKS[k]}">{int(ringkasan[k])}'
        f'<small>{ringkasan[k] / total:.0%}</small></div></div>'
        for k in urutan
    )
    batang = "".join(
        f'<div style="width:{ringkasan[k] / total:.2%};background:{WARNA[k]}"></div>'
        for k in urutan
    )
    return (
        '<div class="bd-label" style="color:#e8590c">Kondisi tercatat terakhir</div>'
        f'<div class="bd-h2" style="font-size:1.35rem">{nama_periode(periode)}</div>'
        f'<div class="bd-kecil">Kategori {total} grid menurut jumlah titik panas yang tercatat, '
        'bukan hasil prediksi.</div>'
        f'{stat}<div class="bd-batang">{batang}</div>'
        f'<div class="bd-stat-abu"><span>Grid tanpa data</span><b>{n_grid - total} grid</b></div>'
    )


def _sebaran_provinsi(sebaran: pd.DataFrame) -> go.Figure:
    """Batang horizontal bertumpuk: jumlah grid per kelas di tiap provinsi.
    Provinsi diurutkan dari yang grid Tingginya paling banyak (paling atas)."""
    data = sebaran.assign(_urut=sebaran["Tinggi"] + sebaran["Sedang"] / 1000)
    data = data.sort_values("_urut")
    total = data[KELAS].sum(axis=1)
    fig = go.Figure()
    for k in ["Tinggi", "Sedang", "Rendah"]:
        fig.add_bar(
            y=data.index, x=data[k], name=k, orientation="h",
            marker={"color": WARNA[k], "line": {"width": 0}},
            text=[str(v) if v else "" for v in data[k]], textposition="inside",
            insidetextanchor="middle", textfont={"color": "#ffffff", "size": 12},
            customdata=list(zip(total, data[k] / total)),
            hovertemplate=(f"<b>%{{y}}</b><br>{k}: %{{x}} dari %{{customdata[0]}} grid "
                           "(%{customdata[1]:.0%})<extra></extra>"),
        )
    fig.update_layout(
        **gaya_grafik(tinggi=400, margin_atas=30, legenda_y=1.0),
        barmode="stack", bargap=0.35, barcornerradius=4,
        xaxis={"title": {"text": "Jumlah grid"}, "gridcolor": "#efe9e2", "zeroline": False},
        yaxis={"tickfont": {"color": "#1f1b18", "size": 13}, "automargin": True,
               "ticksuffix": "  "},
    )
    return fig


def _html_kategori(p33: int, p67: int) -> str:
    batas = {
        "Rendah": (f"≤ {p33}", f"sampai {p33} titik panas"),
        "Sedang": (f"{p33 + 1}–{p67}", f"{p33 + 1} sampai {p67} titik panas"),
        "Tinggi": (f"> {p67}", f"lebih dari {p67} titik panas"),
    }
    isi = "".join(
        f'<div class="bd-kategori">'
        f'<div class="bd-lencana" style="background:{WARNA[k]}">{angka}</div>'
        f'<div><div class="bd-kategori-nama">{k}</div><div class="bd-kecil">{t}</div></div></div>'
        for k, (angka, t) in batas.items()
    )
    return (
        '<div class="bd-h2">Tiga kategori kerawanan</div>'
        '<div class="bd-kecil">Berdasarkan jumlah titik panas per grid dalam sebulan.</div>'
        f'{isi}'
    )


def _html_langkah() -> str:
    isi = "".join(
        f'<div class="bd-langkah"><div class="bd-nomor">{i}</div>'
        f'<div><div class="bd-langkah-judul">{judul}</div>'
        f'<div class="bd-kecil">{ket}</div></div></div>'
        for i, (judul, ket) in enumerate(LANGKAH, 1)
    )
    return f'<div class="bd-h2">Cara menggunakan</div>{isi}'


def _html_sumber() -> str:
    baris = "".join(
        f'<div class="bd-baris"><span class="bd-baris-kiri">'
        f'<i style="background:linear-gradient(135deg,{warna}33,{warna}88)"></i>'
        f'<span class="bd-kecil">{nama}</span></span><b>{sumber}</b></div>'
        for nama, sumber, _, warna in SUMBER_DATA
    )
    return f'<div class="bd-h2" style="margin-bottom:0.3rem">Sumber data</div>{baris}'


def render(sumber: SumberDataService) -> None:
    """Ringkasan yang hanya dilihat: selalu periode tercatat terakhir. Pemilihan
    wilayah dan periode ada di halaman Klasifikasi."""
    daftar = sumber.daftar_periode()
    periode = daftar[-1]
    cut = sumber.muat_cutoff()
    n_grid = int(cut["n_grid"])
    ringkasan = sumber.ringkasan_kategori(periode)
    total = int(ringkasan.sum())

    with st.container(key="bento_hero"):
        st.markdown(_html_hero(n_grid, daftar[0], periode), unsafe_allow_html=True)

    kiri, kanan = st.columns([1, 2], gap="medium")
    with kiri, st.container(key="bento_statistik", height="stretch"):
        st.markdown(_html_statistik(periode, ringkasan, total, n_grid),
                    unsafe_allow_html=True)
        if st.button("Buka klasifikasi", icon=":material/arrow_forward:",
                     type="primary", width="stretch"):
            st.session_state.menu = "Klasifikasi"
            st.rerun()
    with kanan, st.container(key="bento_provinsi", height="stretch"):
        st.markdown(
            f'<div class="bd-h2">Sebaran per provinsi · {nama_periode(periode)}</div>'
            '<div class="bd-kecil">Jumlah grid tiap kategori di setiap provinsi, '
            'diurutkan dari provinsi dengan grid Tinggi terbanyak.</div>',
            unsafe_allow_html=True,
        )
        sebaran = sumber.sebaran_provinsi(periode)
        if sebaran.empty:
            st.caption("Nama provinsi belum tersedia (data/grid_wilayah.csv tidak ditemukan).")
        else:
            st.plotly_chart(_sebaran_provinsi(sebaran), width="stretch",
                            config={"displayModeBar": False})

    with st.container(key="bento_tren"):
        st.markdown(
            '<div class="bd-h2">Tren kerawanan bulanan</div>'
            '<div class="bd-kecil">Jumlah grid per kategori tiap bulan, '
            f'{nama_periode(daftar[0])} sampai {nama_periode(periode)}. '
            'Angka di atas batang menunjukkan jumlah grid Tinggi terbanyak tiap tahun.</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_tren(sumber.tren_kategori()[KELAS], periode), width="stretch",
                        config={"displayModeBar": False})

    kolom = st.columns(3, gap="medium")
    isi = [("bento_kategori", _html_kategori(int(cut["p33"]), int(cut["p67"]))),
           ("bento_langkah", _html_langkah()),
           ("bento_sumber", _html_sumber())]
    for k, (key, html) in zip(kolom, isi):
        with k, st.container(key=key, height="stretch"):
            st.markdown(html, unsafe_allow_html=True)
