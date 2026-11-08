"""
Modul pemuatan model Machine Learning yang aman dan komputasi inferensi (FR-03).
"""
import os
import threading
from typing import Any
import joblib
import numpy as np


class ModelSecurityError(RuntimeError):
    """Kesalahan pemuatan model dari jalur yang tidak diizinkan atau tidak aman."""


class ModelNotAvailableError(FileNotFoundError):
    """Model atau vectorizer belum tersedia di sistem penyimpanan."""


_cached_model: Any = None
_cached_vectorizer: Any = None
_model_lock = threading.Lock()


def _validate_safe_path(target_path: str, base_dir: str) -> str:
    """
    Validasi keamanan jalur file:
    Mencegah path traversal dan memastikan berkas berada di dalam base_dir yang sah.
    """
    resolved_target = os.path.abspath(target_path)
    resolved_base = os.path.abspath(base_dir)

    # Pastikan target berada di bawah resolved_base
    try:
        common = os.path.commonpath([resolved_base, resolved_target])
    except ValueError as exc:
        raise ModelSecurityError(
            f"Path model tidak berada pada drive/direktori yang sama: {exc}"
        )

    if common != resolved_base:
        raise ModelSecurityError(
            "Percobaan pemuatan model dari luar direktori yang diizinkan."
        )

    return resolved_target


def load_model_artifacts(
    model_path: str,
    vectorizer_path: str,
    base_dir: str,
    force_reload: bool = False,
) -> tuple[Any, Any]:
    """
    Muat artefak model.joblib dan vectorizer.joblib dengan validasi keamanan path.
    Menggunakan in-memory caching thread-safe untuk efisiensi komputasi lokal.
    """
    global _cached_model, _cached_vectorizer

    if not force_reload and _cached_model is not None and _cached_vectorizer is not None:
        return _cached_model, _cached_vectorizer

    safe_model_path = _validate_safe_path(model_path, base_dir)
    safe_vectorizer_path = _validate_safe_path(vectorizer_path, base_dir)

    if not os.path.isfile(safe_model_path):
        raise ModelNotAvailableError(
            f"Artefak model tidak ditemukan di lokasi: {safe_model_path}"
        )
    if not os.path.isfile(safe_vectorizer_path):
        raise ModelNotAvailableError(
            f"Artefak vectorizer tidak ditemukan di lokasi: {safe_vectorizer_path}"
        )

    with _model_lock:
        if not force_reload and _cached_model is not None and _cached_vectorizer is not None:
            return _cached_model, _cached_vectorizer

        try:
            loaded_model = joblib.load(safe_model_path)
            loaded_vectorizer = joblib.load(safe_vectorizer_path)
        except Exception as exc:
            raise RuntimeError(f"Gagal mendeserialisasi artefak joblib: {exc}") from exc

        _cached_model = loaded_model
        _cached_vectorizer = loaded_vectorizer
        return _cached_model, _cached_vectorizer


def predict_category(
    cleaned_text: str,
    model: Any,
    vectorizer: Any,
) -> tuple[str, float]:
    """
    Hitung prediksi kategori Naive Bayes dan skor keyakinan (posterior probability).

    Args:
        cleaned_text (str): Teks yang telah melalui tahap pra-pemrosesan.
        model: Objek classifier scikit-learn (MultinomialNB).
        vectorizer: Objek TfidfVectorizer scikit-learn.

    Returns:
        tuple[str, float]: (kode_kategori_prediksi_K1_sampai_K7, confidence_score)
    """
    if not cleaned_text or not cleaned_text.strip():
        raise ValueError("Teks bersih kosong; inferensi tidak dapat dijalankan.")

    # 1. Transformasi fitur TF-IDF unigram & bigram
    features = vectorizer.transform([cleaned_text])

    # 2. Komputasi probabilitas posterior tiap kelas
    probabilities = model.predict_proba(features)[0]

    # 3. Kategori dengan probabilitas terbesar
    best_index = int(np.argmax(probabilities))
    predicted_code = str(model.classes_[best_index])
    confidence_score = float(probabilities[best_index])

    return predicted_code, confidence_score


def reset_model_cache() -> None:
    """Kosongkan cache model (berguna untuk pengujian unit)."""
    global _cached_model, _cached_vectorizer
    with _model_lock:
        _cached_model = None
        _cached_vectorizer = None

