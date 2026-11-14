"""
Pipeline pra-pemrosesan teks NLP untuk deskripsi keluhan (FR-03).
Menerapkan 6 tahap pra-pemrosesan:
1. Case folding
2. Regex cleaning (penghapusan URL, simbol, tanda baca, dan angka khusus teks deskripsi)
3. Normalisasi kata slang / singkatan berbasis kamus terpusat
4. Tokenisasi
5. Stopword removal (PySastrawi)
6. Stemming Nazief-Adriani (PySastrawi)
"""
from dataclasses import dataclass
import re
import threading
from typing import Pattern

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

from app.ml.dictionary import SLANG_DICTIONARY

# Singleton instances untuk Sastrawi (lazy initialization dengan thread-safety)
_stemmer = None
_stopwords = None
_sastrawi_lock = threading.Lock()

NEGATION_WORDS = frozenset({"tidak", "bukan", "belum", "tanpa", "tak", "jangan"})

URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
CLEAN_CHARS_PATTERN = re.compile(r"[^a-z\s]")
WHITESPACE_PATTERN = re.compile(r"\s+")

# Kompilasi pola regex untuk setiap entri slang dengan word boundary (\b)
_COMPILED_SLANG_PATTERNS: list[tuple[Pattern[str], str]] = [
    (re.compile(rf"\b{re.escape(k)}\b", re.IGNORECASE), v)
    for k, v in SLANG_DICTIONARY.items()
]


@dataclass(frozen=True)
class PreprocessResult:
    """Kontrak hasil pra-pemrosesan teks deskripsi keluhan."""
    cleaned_text: str          # Teks setelah pra-pemrosesan lengkap
    tokens: list[str]          # Daftar token kata dasar
    token_count: int           # Jumlah token kata dasar


def _get_stemmer():
    global _stemmer
    if _stemmer is None:
        with _sastrawi_lock:
            if _stemmer is None:
                factory = StemmerFactory()
                _stemmer = factory.create_stemmer()
    return _stemmer


def _get_stopwords():
    global _stopwords
    if _stopwords is None:
        with _sastrawi_lock:
            if _stopwords is None:
                factory = StopWordRemoverFactory()
                _stopwords = frozenset(factory.get_stop_words()) - NEGATION_WORDS
    return _stopwords


def normalize_slang(text: str) -> str:
    """
    Normalisasi singkatan dan kata slang ke bentuk baku bahasa Indonesia.
    Menggunakan word boundary (\b) untuk mencegah perusakan kata (contoh: 'kaca' tidak menjadi 'kpendingin ruangan').
    """
    result = text
    for pattern, replacement in _COMPILED_SLANG_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def preprocess_text(text: str | None) -> PreprocessResult:
    """
    Eksekusi 6 tahapan pra-pemrosesan teks pada deskripsi keluhan.

    PENTING (Integritas Data Lokasi):
    Pembersihan angka pada fungsi ini HANYA diterapkan pada teks deskripsi
    sebagai input sementara fitur vektorisasi TF-IDF. Teks asli dan angka
    pada entitas lokasi gedung/lantai/ruang tidak terpengaruh fungsi ini.
    """
    if not text or not str(text).strip():
        return PreprocessResult(cleaned_text="", tokens=[], token_count=0)

    # 1. Case Folding: seragamkan huruf kecil
    normalized = str(text).lower()

    # 2. Hapus URL
    normalized = URL_PATTERN.sub(" ", normalized)

    # 3. Normalisasi singkatan & slang dengan batas kata
    normalized = normalize_slang(normalized)

    # 4. Regex Cleaning: hapus karakter non-huruf, tanda baca, simbol, dan angka
    #    (Menghilangkan angka secara khusus untuk vektorisasi kosakata NLP)
    normalized = CLEAN_CHARS_PATTERN.sub(" ", normalized)
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()

    if not normalized:
        return PreprocessResult(cleaned_text="", tokens=[], token_count=0)

    # 5. Stopword Removal menggunakan daftar PySastrawi, kecuali kata negasi
    stopwords = _get_stopwords()
    without_stopwords = " ".join(
        word for word in normalized.split() if word not in stopwords
    )

    # 6. Stemming Nazief-Adriani menggunakan PySastrawi
    stemmer = _get_stemmer()
    stemmed = stemmer.stem(without_stopwords).strip()

    # Normalisasi spasi akhir dan pembentukan token
    cleaned_text = WHITESPACE_PATTERN.sub(" ", stemmed).strip()
    tokens = cleaned_text.split() if cleaned_text else []

    return PreprocessResult(
        cleaned_text=cleaned_text,
        tokens=tokens,
        token_count=len(tokens),
    )

