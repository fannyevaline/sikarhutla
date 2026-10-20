"""Entitas data sesuai class diagram (Gambar 3.8): Grid -> KondisiBulanan -> HasilPrediksi.

Relasi ketiganya komposisi: HasilPrediksi hanya ada di dalam KondisiBulanan,
dan KondisiBulanan hanya ada di dalam Grid.
"""
from dataclasses import dataclass, field


@dataclass
class HasilPrediksi:
    """Hasil klasifikasi satu model untuk satu grid-bulan."""
    model: str
    kelas: str
    confidence: float
    probabilitas: dict[str, float]  # kelas -> peluang, urut KELAS


@dataclass
class KomposisiCuaca:
    """Asal deret cuaca harian untuk bulan yang tidak ada di basis data.
    Ketiga bagian berurutan: observasi, lalu ramalan, lalu klimatologi."""
    hari_observasi: int
    hari_ramalan: int
    hari_klimatologi: int

    @property
    def n_hari(self) -> int:
        return self.hari_observasi + self.hari_ramalan + self.hari_klimatologi


@dataclass
class KondisiBulanan:
    """Data dinamis satu grid pada satu bulan. Untuk bulan di luar basis data,
    kondisi_id, jumlah_hotspot, dan kerawanan bernilai None, dan komposisi terisi."""
    kondisi_id: int | None
    tahun_bulan: str
    curah_hujan_mm: float
    suhu_maks_c: float
    kelembapan_persen: float
    angin_maks_kmh: float
    hari_kering_maks: int
    jumlah_hotspot: int | None
    kerawanan: str | None
    komposisi: KomposisiCuaca | None = None
    hasil: list[HasilPrediksi] = field(default_factory=list)


@dataclass
class Grid:
    """Data statis satu grid 0,5 derajat."""
    grid_id: str
    grid_lat: float
    grid_lon: float
    ketinggian_meter: float
    kemiringan_lereng: float
    jarak_air_meter: float
    jarak_jalan_meter: float
    tutupan_lahan: str
    gambut: str
    provinsi: str | None = None
    kabupaten: str | None = None
    kondisi: list[KondisiBulanan] = field(default_factory=list)

    @property
    def nama(self) -> str:
        if self.kabupaten:
            return f"{self.kabupaten}, {self.provinsi}"
        return f"Grid {self.grid_lat:.2f}, {self.grid_lon:.2f}"

    def baris_fitur(self, kondisi: KondisiBulanan) -> dict:
        """Satu baris input model untuk kondisi bulan tertentu (belum di-encode)."""
        return {
            "ketinggian_meter": self.ketinggian_meter,
            "kemiringan_lereng": self.kemiringan_lereng,
            "curah_hujan_mm": kondisi.curah_hujan_mm,
            "suhu_maks_c": kondisi.suhu_maks_c,
            "kelembapan_persen": kondisi.kelembapan_persen,
            "angin_maks_kmh": kondisi.angin_maks_kmh,
            "hari_kering_maks": kondisi.hari_kering_maks,
            "jarak_air_meter": self.jarak_air_meter,
            "jarak_jalan_meter": self.jarak_jalan_meter,
            "tutupan_lahan": self.tutupan_lahan,
            "gambut": self.gambut,
        }
