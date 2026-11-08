"""
Kamus normalisasi singkatan dan kata slang terpusat (FR-03).
Digunakan dalam tahap pra-pemrosesan teks sebelum stopword removal dan stemming.
"""
from types import MappingProxyType

# Pemetaan kata slang / singkatan ke bentuk baku bahasa Indonesia.
# Menggunakan kata kunci huruf kecil; penggantian dilakukan berbasis batas kata (\b).
_SLANG_MAPPING = {
    # Fasilitas & Perangkat Kampus
    "ac": "pendingin ruangan",
    "wifi": "internet",
    "wi-fi": "internet",
    "hotspot": "internet",
    "pc": "komputer",
    "lcd": "proyektor",
    "infocus": "proyektor",
    "lab": "laboratorium",
    "colokan": "stop kontak",
    "stopkontak": "stop kontak",
    "saklar": "saklar",
    "kran": "keran",
    "wc": "toilet",
    "wastafel": "wastafel",
    "lift": "lift",

    # Negasi & Kata Hubung Informal
    "gak": "tidak",
    "ga": "tidak",
    "nggak": "tidak",
    "ngga": "tidak",
    "ndak": "tidak",
    "tak": "tidak",
    "tdk": "tidak",
    "bkn": "bukan",
    "yg": "yang",
    "dgn": "dengan",
    "dg": "dengan",
    "kalo": "kalau",
    "kl": "kalau",
    "krn": "karena",
    "utk": "untuk",
    "bgt": "sangat",
    "bgtu": "begitu",
    "bgmn": "bagaimana",
    "gmn": "bagaimana",
    "sdh": "sudah",
    "udh": "sudah",
    "udah": "sudah",
    "blm": "belum",
    "belom": "belum",
    "tp": "tetapi",
    "tpi": "tetapi",
    "bisa": "bisa",
    "bs": "bisa",
    "aja": "saja",
    "ajah": "saja",
    "doang": "saja",

    # Kondisi / Kerusakan
    "ancur": "rusak",
    "remuk": "rusak",
    "mati": "padam",
    "padam": "padam",
    "bocor": "bocor",
    "mampet": "tersumbat",
    "sumbat": "tersumbat",
    "jelek": "buruk",
    "lemot": "lambat",
    "lelet": "lambat",
    "lag": "lambat",
    "error": "rusak",
    "rusak": "rusak",
}

# Kamus terpusat yang bersifat immutable (read-only)
SLANG_DICTIONARY: MappingProxyType[str, str] = MappingProxyType(_SLANG_MAPPING)

