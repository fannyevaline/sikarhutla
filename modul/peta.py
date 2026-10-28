"""Modul 2 - Peta interaktif kerawanan: 232 grid 0,5 derajat, klik untuk memilih.

Bulan di basis data diwarnai menurut kategori tercatat. Bulan di luar basis data
belum punya kategori tercatat, jadi diwarnai menurut prediksi model dengan F1-macro
tertinggi; prediksi kedua model tetap terlihat di tooltip dan panel hasil.
"""
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from domain.grid import nama_wilayah
from domain.konstanta import KELAS, UKURAN_GRID
from domain.sumber_data_service import SumberDataService
from modul.tampilan import WARNA, nama_periode

ABU = "#d8d0c6"           # bulan di luar basis data yang cuacanya gagal diambil
ARSIR = "#A8A29E"         # garis miring grid tanpa data
KOLOM = {"Random Forest": ("kelas_rf", "conf_rf"), "XGBoost": ("kelas_xgb", "conf_xgb")}
# Kepekatan isian grid menurut confidence prediksi: (batas bawah, opacity)
KEPEKATAN = [(0.70, 0.85), (0.50, 0.60), (0.0, 0.35)]
KEPEKATAN_TERCATAT = 0.85
TENGAH = [0.1, 114.2]
BATAS = [[-4.6, 108.4], [4.6, 119.6]]
# Peta dasar tanpa API key: Esri World Physical Map (daratan hijau-cokelat berelief,
# laut biru) + label tempat, berwarna natural tetapi tenang. Tile-nya hanya sampai
# zoom 8; di atas itu Leaflet memperbesar tile zoom 8. CartoDB Positron kini memberi
# tile bertanda air "API KEY REQUIRED" tanpa kunci.
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/{}/MapServer/tile/{{z}}/{{y}}/{{x}}"
TILE = ESRI.format("World_Physical_Map")
TILE_ZOOM_MAKS = 8
TILE_LABEL = ESRI.format("Reference/World_Boundaries_and_Places_Alternate")
ATRIBUSI = "Esri, US NPS, Garmin, HERE, © OpenStreetMap"
# Ruang kosong di atas peta untuk strip legenda, supaya grid tidak tertutup (piksel)
RUANG_LEGENDA = 64
# Tinggi minimum peta (piksel); bila panel di sebelahnya lebih tinggi, peta ikut
# memanjang. Angka yang sama ada di klasifikasi.css.
TINGGI_MIN = 600


def _kepekatan(confidence: float) -> float:
    return next(o for batas, o in KEPEKATAN if confidence >= batas)


def _fitur(grid, periode_tercatat: bool, prediksi: pd.DataFrame | None, model: str) -> dict:
    """GeoJSON satu grid: persegi 0,5 derajat di sekitar titik pusatnya."""
    h = UKURAN_GRID / 2
    lat, lon = grid.grid_lat, grid.grid_lon
    warna, kepekatan = ABU, 0.6
    if not grid.ada_di_dataset:
        warna, kepekatan, ket = ARSIR, 0.0, "Tidak ada data"
    elif periode_tercatat:
        warna, kepekatan = WARNA[grid.kerawanan], KEPEKATAN_TERCATAT
        ket = f"{grid.kerawanan} · {int(grid.jumlah_hotspot)} titik panas"
    elif prediksi is not None and grid.grid_id in prediksi.index:
        r = prediksi.loc[grid.grid_id]
        kolom_kelas, kolom_conf = KOLOM[model]
        warna, kepekatan = WARNA[r[kolom_kelas]], _kepekatan(r[kolom_conf])
        ket = (f"Random Forest: {r.kelas_rf} ({r.conf_rf:.0%}) · "
               f"XGBoost: {r.kelas_xgb} ({r.conf_xgb:.0%})")
    else:
        ket = "Kategori belum tercatat"
    nama = nama_wilayah(grid.kabupaten, grid.provinsi, lat, lon)
    return {
        "type": "Feature",
        "properties": {"nama": nama, "ket": ket, "warna": warna, "kepekatan": kepekatan,
                       "garis": ARSIR if not grid.ada_di_dataset else "#ffffff"},
        "geometry": {"type": "Polygon", "coordinates": [[
            [lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h],
            [lon - h, lat + h], [lon - h, lat - h]]]},
    }


def _arsir(lat: float, lon: float) -> list:
    """Garis miring (/) di dalam satu grid: ruas-ruas u - v = c, dengan u, v selisih
    lintang dan bujur terhadap titik pusat, dipotong pada tepi persegi."""
    h = UKURAN_GRID / 2
    ruas = []
    for c in (-0.4, -0.2, 0.0, 0.2, 0.4):
        v0, v1 = max(-h, -h - c), min(h, h - c)
        ruas.append([[lat + v0 + c, lon + v0], [lat + v1 + c, lon + v1]])
    return ruas


def _lapisan(sumber: SumberDataService, periode: str, grid_terpilih: str, tercatat: bool,
             prediksi: pd.DataFrame | None, model: str) -> folium.FeatureGroup:
    """Lapisan grid berwarna + arsir grid tanpa data + bingkai grid terpilih. Dikirim
    sebagai feature_group_to_add supaya peta dasar (posisi & zoom) tidak dimuat ulang."""
    data = sumber.kategori_per_grid(periode)
    lapisan = folium.FeatureGroup(name="grid")
    folium.GeoJson(
        {"type": "FeatureCollection",
         "features": [_fitur(g, tercatat, prediksi, model) for g in data.itertuples()]},
        style_function=lambda f: {"fillColor": f["properties"]["warna"],
                                  "fillOpacity": f["properties"]["kepekatan"],
                                  "color": f["properties"]["garis"], "weight": 1},
        highlight_function=lambda f: {"weight": 2, "color": "#1f1b18"},
        tooltip=folium.GeoJsonTooltip(fields=["nama", "ket"], labels=False,
                                      style="font-family: 'Plus Jakarta Sans', sans-serif;"
                                            "font-size: 13px;"),
    ).add_to(lapisan)
    kosong = data[data.ada_di_dataset == 0]
    folium.PolyLine([r for g in kosong.itertuples() for r in _arsir(g.grid_lat, g.grid_lon)],
                    color=ARSIR, weight=1, opacity=1, interactive=False).add_to(lapisan)
    pilih = data[data.grid_id == grid_terpilih]
    if len(pilih):
        g = next(pilih.itertuples())
        h = UKURAN_GRID / 2
        folium.Rectangle(
            [[g.grid_lat - h, g.grid_lon - h], [g.grid_lat + h, g.grid_lon + h]],
            color="#1f1b18", weight=3.5, fill=False, interactive=False,
        ).add_to(lapisan)
    return lapisan


def _legenda(tercatat: bool, berwarna: bool, model: str) -> str:
    """Keterangan berupa strip tipis di tepi atas peta, di sebelah tombol zoom. Grid
    digeser turun selebar RUANG_LEGENDA supaya tidak tertutup. Di dalam iframe peta,
    jadi gayanya inline."""
    kotak = "display:inline-block;width:12px;height:12px;border-radius:2px;flex-shrink:0"
    item = "display:inline-flex;align-items:center;gap:5px;white-space:nowrap"
    if berwarna:
        isi = "".join(f'<span style="{item}"><i style="{kotak};background:{WARNA[k]};'
                      f'opacity:0.85"></i>{k}</span>' for k in KELAS)
    else:
        isi = (f'<span style="{item}"><i style="{kotak};background:{ABU};opacity:0.6">'
               '</i>Belum tercatat</span>')
    isi += (f'<span style="{item}"><i style="{kotak};border:1px solid {ARSIR};'
            f'background:repeating-linear-gradient(135deg,{ARSIR} 0 1px,transparent 1px 4px)">'
            '</i>Tidak ada data</span>')
    isi += (f'<span style="{item}"><i style="{kotak};border:2.5px solid #1f1b18"></i>'
            'Grid terpilih</span>')
    if tercatat:
        pekat = "Kepekatan rata: kategori dari jumlah titik panas tercatat, bukan prediksi."
    elif berwarna:
        contoh = "".join(f'<i style="{kotak};background:#e03131;opacity:{o}"></i>'
                         for _, o in KEPEKATAN)
        pekat = (f'<span style="{item};gap:2px;margin-right:4px">{contoh}</span>'
                 f"Makin pekat makin yakin: confidence {model} ≥70% · 50–70% · &lt;50%.")
    else:
        pekat = ""
    if pekat:
        pekat = f'<div style="margin-top:4px;color:#78716C">{pekat}</div>'
    return ('<div style="position:absolute;top:10px;left:54px;right:10px;z-index:1000;'
            'background:rgba(255,255,255,0.92);border:1px solid #e7e5e4;border-radius:10px;'
            'padding:6px 10px;font:12px/1.35 Plus Jakarta Sans,system-ui,sans-serif;'
            'color:#44403c;box-shadow:0 2px 8px rgba(0,0,0,0.08)">'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px 14px">{isi}</div>{pekat}</div>')


def render(sumber: SumberDataService, periode: str, grid_terpilih: str,
           prediksi: pd.DataFrame | None = None) -> tuple | None:
    """Gambar peta dan kembalikan koordinat (lat, lon) klik baru, atau None.
    prediksi = hasil ModulKlasifikasi.klasifikasi_bulan() untuk bulan di luar
    basis data; None kalau bulan tercatat atau data cuaca gagal diambil."""
    tercatat = sumber.status_periode(periode) == "historis"
    st.markdown(f'<div class="kl-h2">Peta kerawanan · {nama_periode(periode)}</div>',
                unsafe_allow_html=True)
    model = sumber.model_terbaik()
    if tercatat:
        sub = ("Warna menunjukkan kategori tercatat menurut jumlah titik panas. "
               "Klik grid untuk memilihnya.")
    elif prediksi is not None:
        sub = (f"Kategori bulan ini belum tercatat, jadi warna menunjukkan prediksi {model}, "
               "model dengan F1-macro tertinggi. Arahkan kursor ke grid untuk melihat "
               "prediksi kedua model.")
    else:
        sub = ("Kategori bulan ini belum tercatat dan data cuacanya belum bisa diambil, "
               "jadi peta belum bisa diwarnai.")
    st.markdown(f'<div class="kl-kecil" style="margin-bottom:0.6rem">{sub}</div>',
                unsafe_allow_html=True)
    dasar = folium.TileLayer(TILE, attr=ATRIBUSI, min_zoom=5, max_zoom=10,
                             max_native_zoom=TILE_ZOOM_MAKS)
    peta = folium.Map(location=TENGAH, zoom_start=6, tiles=dasar,
                      max_bounds=True, control_scale=True,
                      zoom_snap=0.25, zoom_delta=0.5,
                      min_lat=BATAS[0][0] - 3, max_lat=BATAS[1][0] + 3,
                      min_lon=BATAS[0][1] - 4, max_lon=BATAS[1][1] + 4)
    folium.TileLayer(TILE_LABEL, attr=ATRIBUSI, overlay=True, control=False).add_to(peta)
    peta.fit_bounds(BATAS, padding_top_left=(0, RUANG_LEGENDA))
    peta.get_root().html.add_child(
        folium.Element(_legenda(tercatat, tercatat or prediksi is not None, model)))
    # Peta mengikuti tinggi iframe; iframe-nya direntangkan setinggi kartu oleh
    # klasifikasi.css, jadi peta ikut memanjang bila panel di sebelahnya lebih tinggi.
    peta.get_root().header.add_child(folium.Element(
        "<style>html, body { height: 100%; margin: 0; overflow: hidden; }"
        "#root, #parent, .float-child { height: 100%; }"
        "#map_div { height: 100% !important; }</style>"))
    hasil = st_folium(
        peta, key="kl_peta", height=TINGGI_MIN, use_container_width=True,
        feature_group_to_add=_lapisan(sumber, periode, grid_terpilih, tercatat, prediksi, model),
        returned_objects=["last_clicked"],
    )

    klik = (hasil or {}).get("last_clicked")
    if not klik or klik == st.session_state.get("kl_klik_terakhir"):
        return None
    st.session_state.kl_klik_terakhir = klik
    return klik["lat"], klik["lng"]
