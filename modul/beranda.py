"""Modul 1 - Beranda."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from domain.sumber_data_service import KELAS, SumberDataService

# Warna tanda (peta, batang) dan warna teks yang lebih gelap supaya tetap terbaca.
WARNA = {"Rendah": "#1f9d55", "Sedang": "#e0a000", "Tinggi": "#e03131"}
WARNA_TEKS = {"Rendah": "#137a3f", "Sedang": "#9a6700", "Tinggi": "#b42323"}
WARNA_LATAR = {"Rendah": "#dcf3e5", "Sedang": "#fff0c4", "Tinggi": "#ffe1e1"}

BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

LANGKAH = [
    ("Pilih grid wilayah", "Lewat peta atau daftar grid"),
    ("Pilih periode", "Bulan lampau atau sampai 16 hari ke depan"),
    ("Jalankan klasifikasi", "Kedua model dijalankan sekaligus"),
    ("Baca hasilnya", "Kategori, confidence, dan nilai variabel"),
]

SUMBER_DATA = [
    ("Titik panas", "NASA FIRMS", "#f76707"),
    ("Cuaca", "Open-Meteo", "#1c7ed6"),
    ("Tutupan lahan", "ESA WorldCover", "#2b8a3e"),
    ("Lahan gambut", "BIG", "#9c5b2a"),
    ("Jalan dan air", "OpenStreetMap", "#0c8599"),
    ("Batas wilayah", "GADM v4.1", "#7048e8"),
]

FONT = "Plus Jakarta Sans, sans-serif"

CSS = """
<style>
.st-key-bento_hero {
    background: radial-gradient(circle at 92% 10%, rgba(255,146,43,0.55), transparent 42%),
                linear-gradient(120deg, #2a1712 0%, #5c1a1a 50%, #b4321f 100%);
    border: none !important; padding: 1.7rem 2rem !important;
}
.st-key-bento_hero:hover { transform: none !important; }
.bd-label { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #ffb38a; margin-bottom: 0.35rem; }
.bd-judul { font-size: 2.2rem; font-weight: 800; color: #fff; margin: 0;
    line-height: 1.15; letter-spacing: -0.02em; }
.bd-sub { color: #f5d9cc; font-size: 1rem; margin: 0.35rem 0 0.9rem; }
.bd-pil-grup { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.bd-pil { display: inline-flex; align-items: center; gap: 0.45rem;
    background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.22);
    border-radius: 999px; padding: 0.3rem 0.8rem; font-size: 0.82rem; color: #fff;
    font-weight: 500; backdrop-filter: blur(4px); }
.bd-pil i { width: 7px; height: 7px; border-radius: 50%; background: #ffa94d; }

.bd-h2 { font-size: 1.08rem; font-weight: 700; color: #1f1b18; margin: 0; }
.bd-kecil { color: #756d66; font-size: 0.86rem; }
.bd-kepala { display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 0.6rem; }
.bd-legenda { display: flex; flex-wrap: wrap; gap: 0.8rem; font-size: 0.8rem; color: #4f4842; }
.bd-legenda span { display: inline-flex; align-items: center; gap: 0.35rem; }
.bd-legenda i { width: 11px; height: 11px; border-radius: 3px; }

.bd-stat { border-radius: 14px; padding: 0.9rem 1.1rem; margin-top: 0.7rem;
    display: flex; justify-content: space-between; align-items: center;
    border-left: 5px solid; }
.bd-stat-label { display: flex; align-items: center; gap: 0.5rem;
    font-size: 0.92rem; font-weight: 700; }
.bd-stat-nilai { font-size: 2.1rem; font-weight: 800; line-height: 1; letter-spacing: -0.02em;
    text-align: right; }
.bd-stat-nilai small { display: block; font-size: 0.78rem; font-weight: 600;
    color: #6f6760; letter-spacing: 0; margin-top: 0.25rem; }
.bd-batang { display: flex; gap: 2px; height: 10px; border-radius: 999px; overflow: hidden;
    margin-top: 1rem; }
.bd-stat-abu { display: flex; justify-content: space-between; align-items: center;
    margin-top: 0.7rem; padding: 0.55rem 1.1rem; border-radius: 12px;
    border: 1px dashed #d4ccc3; color: #756d66; font-size: 0.85rem; }
.bd-stat-abu b { color: #4f4842; }
.st-key-bento_statistik [data-testid="stElementContainer"]:has(button) { margin-top: auto; }

.bd-kategori { display: flex; align-items: center; gap: 0.85rem; margin-top: 0.75rem; }
.bd-lencana { min-width: 3.3rem; height: 2.6rem; border-radius: 10px; padding: 0 0.4rem;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.95rem; color: #fff; }
.bd-kategori-nama { font-size: 0.98rem; font-weight: 700; color: #1f1b18; line-height: 1.3; }

.bd-langkah { display: flex; gap: 0.8rem; margin-top: 0.75rem; align-items: flex-start; }
.bd-nomor { width: 1.7rem; height: 1.7rem; border-radius: 8px; color: #fff; flex-shrink: 0;
    background: linear-gradient(135deg, #ff922b, #e03131);
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 0.8rem; }
.bd-langkah-judul { font-weight: 700; font-size: 0.95rem; color: #1f1b18; line-height: 1.3; }

.bd-baris { display: flex; justify-content: space-between; align-items: center; gap: 1rem;
    padding: 0.55rem 0; border-bottom: 1px solid #f1ece6; }
.bd-baris:last-child { border-bottom: none; padding-bottom: 0; }
.bd-baris-kiri { display: flex; align-items: center; gap: 0.6rem; }
.bd-baris-kiri i { width: 1.6rem; height: 1.6rem; border-radius: 7px; opacity: 0.9; }
.bd-baris b { color: #1f1b18; font-weight: 600; font-size: 0.88rem; text-align: right; }
</style>
"""


def _nama_periode(tahun_bulan: str) -> str:
    tahun, bulan = tahun_bulan.split("-")
    return f"{BULAN[int(bulan) - 1]} {tahun}"


def _html_hero(n_grid: int, awal: str, akhir: str) -> str:
    pil = "".join(
        f'<span class="bd-pil"><i></i>{teks}</span>'
        for teks in [
            f"{n_grid} grid 0,5°",
            f"{_nama_periode(awal)} – {_nama_periode(akhir)}",
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
    nama = [_nama_periode(p) for p in tren.index]
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
        barmode="stack", bargap=0.22, barcornerradius=3, height=320,
        margin={"l": 0, "r": 0, "t": 24, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT, "color": "#756d66", "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.04, "x": 1, "xanchor": "right",
                "font": {"color": "#4f4842"}, "traceorder": "normal"},
        hoverlabel={"bgcolor": "#ffffff", "bordercolor": "#e6dfd7",
                    "font": {"family": FONT, "color": "#1f1b18", "size": 13}},
        xaxis={"showgrid": False, "tickformat": "%Y", "dtick": "M12", "tick0": "2021-01-01",
               "range": [x.min() - pd.Timedelta(days=20), x.max() + pd.Timedelta(days=20)]},
        yaxis={"title": {"text": "Jumlah grid"}, "gridcolor": "#efe9e2", "zeroline": False,
               "rangemode": "tozero"},
        dragmode=False,
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
        f'<div class="bd-h2" style="font-size:1.35rem">{_nama_periode(periode)}</div>'
        f'<div class="bd-kecil">Kategori {total} grid menurut jumlah titik panas yang tercatat, '
        'bukan hasil prediksi</div>'
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
        barmode="stack", bargap=0.35, barcornerradius=4, height=400,
        margin={"l": 0, "r": 0, "t": 30, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT, "color": "#756d66", "size": 12},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "x": 1, "xanchor": "right",
                "font": {"color": "#4f4842"}, "traceorder": "normal"},
        hoverlabel={"bgcolor": "#ffffff", "bordercolor": "#e6dfd7",
                    "font": {"family": FONT, "color": "#1f1b18", "size": 13}},
        xaxis={"title": {"text": "Jumlah grid"}, "gridcolor": "#efe9e2", "zeroline": False},
        yaxis={"tickfont": {"color": "#1f1b18", "size": 13}},
        dragmode=False,
    )
    return fig


def _html_kategori(p33: int, p67: int) -> str:
    batas = {
        "Rendah": (f"≤ {p33}", f"sampai {p33} titik panas"),
        "Sedang": (f"{p33 + 1}–{p67}", f"{p33 + 1} sampai {p67} titik panas"),
        "Tinggi": (f"≥ {p67 + 1}", f"lebih dari {p67} titik panas"),
    }
    isi = "".join(
        f'<div class="bd-kategori">'
        f'<div class="bd-lencana" style="background:{WARNA[k]}">{angka}</div>'
        f'<div><div class="bd-kategori-nama">{k}</div><div class="bd-kecil">{t}</div></div></div>'
        for k, (angka, t) in batas.items()
    )
    return (
        '<div class="bd-h2">Tiga kategori kerawanan</div>'
        '<div class="bd-kecil">Dari jumlah titik panas per grid tiap bulan</div>'
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
        for nama, sumber, warna in SUMBER_DATA
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

    st.markdown(CSS, unsafe_allow_html=True)
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
            f'<div class="bd-h2">Sebaran per provinsi · {_nama_periode(periode)}</div>'
            '<div class="bd-kecil">Jumlah grid tiap kategori di setiap provinsi, '
            'diurutkan dari yang paling banyak grid tinggi</div>',
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
            f'{_nama_periode(daftar[0])} sampai {_nama_periode(periode)}. '
            'Angka = puncak grid tinggi tiap tahun.</div>',
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
