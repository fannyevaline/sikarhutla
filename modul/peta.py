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

ABU = {"Belum tercatat": "#d8d0c6", "Tidak ada data": "#9e968e"}
KOLOM = {"Random Forest": "kelas_rf", "XGBoost": "kelas_xgb"}
TENGAH = [0.1, 114.2]
BATAS = [[-4.6, 108.4], [4.6, 119.6]]
# Peta dasar abu-abu terang tanpa API key, supaya warna grid menonjol.
TILE = ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/"
        "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}")
ATRIBUSI = "Esri, HERE, Garmin, © OpenStreetMap contributors"

def _fitur(grid, periode_tercatat: bool, prediksi: pd.DataFrame | None, model: str) -> dict:
    """GeoJSON satu grid: persegi 0,5 derajat di sekitar titik pusatnya."""
    h = UKURAN_GRID / 2
    lat, lon = grid.grid_lat, grid.grid_lon
    if not grid.ada_di_dataset:
        kelas, ket = "Tidak ada data", "Tidak ada data"
    elif periode_tercatat:
        kelas = grid.kerawanan
        ket = f"{kelas} · {int(grid.jumlah_hotspot)} titik panas"
    elif prediksi is not None and grid.grid_id in prediksi.index:
        r = prediksi.loc[grid.grid_id]
        kelas = r[KOLOM[model]]
        ket = (f"Random Forest: {r.kelas_rf} ({r.conf_rf:.0%}) · "
               f"XGBoost: {r.kelas_xgb} ({r.conf_xgb:.0%})")
    else:
        kelas, ket = "Belum tercatat", "Kategori belum tercatat"
    nama = nama_wilayah(grid.kabupaten, grid.provinsi, lat, lon)
    return {
        "type": "Feature",
        "properties": {"nama": nama, "ket": ket, "warna": WARNA.get(kelas, ABU.get(kelas))},
        "geometry": {"type": "Polygon", "coordinates": [[
            [lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h],
            [lon - h, lat + h], [lon - h, lat - h]]]},
    }


def _lapisan(sumber: SumberDataService, periode: str, grid_terpilih: str, tercatat: bool,
             prediksi: pd.DataFrame | None, model: str) -> folium.FeatureGroup:
    """Lapisan grid berwarna + bingkai grid terpilih. Dikirim sebagai
    feature_group_to_add supaya peta dasar (posisi & zoom) tidak dimuat ulang."""
    data = sumber.kategori_per_grid(periode)
    lapisan = folium.FeatureGroup(name="grid")
    folium.GeoJson(
        {"type": "FeatureCollection",
         "features": [_fitur(g, tercatat, prediksi, model) for g in data.itertuples()]},
        style_function=lambda f: {"fillColor": f["properties"]["warna"], "fillOpacity": 0.62,
                                  "color": "#ffffff", "weight": 1},
        highlight_function=lambda f: {"fillOpacity": 0.85, "weight": 2, "color": "#1f1b18"},
        tooltip=folium.GeoJsonTooltip(fields=["nama", "ket"], labels=False,
                                      style="font-family: 'Plus Jakarta Sans', sans-serif;"
                                            "font-size: 13px;"),
    ).add_to(lapisan)
    pilih = data[data.grid_id == grid_terpilih]
    if len(pilih):
        g = next(pilih.itertuples())
        h = UKURAN_GRID / 2
        folium.Rectangle(
            [[g.grid_lat - h, g.grid_lon - h], [g.grid_lat + h, g.grid_lon + h]],
            color="#1f1b18", weight=3.5, fill=False, interactive=False,
        ).add_to(lapisan)
    return lapisan


def _legenda(berwarna: bool) -> str:
    kelas = KELAS if berwarna else ["Belum tercatat"]
    isi = "".join(f'<span><i style="background:{WARNA.get(k, ABU.get(k))}"></i>{k}</span>'
                  for k in kelas)
    isi += f'<span><i style="background:{ABU["Tidak ada data"]}"></i>Tidak ada data</span>'
    return (f'<div class="pt-legenda">{isi}'
            '<span class="pt-pilih"><i></i>Grid terpilih</span></div>')


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
    peta = folium.Map(location=TENGAH, zoom_start=6, tiles=TILE, attr=ATRIBUSI,
                      min_zoom=5, max_zoom=10, max_bounds=True, control_scale=True,
                      zoom_snap=0.25, zoom_delta=0.5,
                      min_lat=BATAS[0][0] - 3, max_lat=BATAS[1][0] + 3,
                      min_lon=BATAS[0][1] - 4, max_lon=BATAS[1][1] + 4)
    peta.fit_bounds(BATAS)
    hasil = st_folium(
        peta, key="kl_peta", height=560, use_container_width=True,
        feature_group_to_add=_lapisan(sumber, periode, grid_terpilih, tercatat, prediksi, model),
        returned_objects=["last_clicked"],
    )
    st.markdown(_legenda(tercatat or prediksi is not None), unsafe_allow_html=True)

    klik = (hasil or {}).get("last_clicked")
    if not klik or klik == st.session_state.get("kl_klik_terakhir"):
        return None
    st.session_state.kl_klik_terakhir = klik
    return klik["lat"], klik["lng"]
