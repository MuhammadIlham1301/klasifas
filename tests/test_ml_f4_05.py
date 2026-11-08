"""
Pengujian komprehensif TSK-F4-05:
- Pipeline Preprocessing NLP (FR-03): Case folding, cleaning, slang normalization, stopword, Sastrawi stemming.
- Integritas Data: Pembersihan angka hanya pada teks kosakata NLP, deskripsi asli di database tetap utuh.
- Keamanan Model Loader Joblib: Path traversal protection, pemuatan hanya dari direktori tepercaya.
- Graceful Fallback Manual (FR-10): Penanganan ketiadaan model .joblib tanpa exception atau kebocoran PII pada log.
- Evaluasi Ambang Batas Keyakinan (ML_CONFIDENCE_THRESHOLD = 0.60 TBD).
- Integrasi Alur Pelaporan (/lapor).
"""
from decimal import Decimal
import logging
import os
import re
from unittest.mock import MagicMock

import pytest
from flask import g
from sqlalchemy import delete, select, update

from app.extensions import db
from app.ml.classifier import (
    ModelNotAvailableError,
    ModelSecurityError,
    _validate_safe_path,
    load_model_artifacts,
    predict_category,
    reset_model_cache,
)
from app.ml.dictionary import SLANG_DICTIONARY
from app.ml.preprocessor import (
    PreprocessResult,
    normalize_slang,
    preprocess_text,
)
from app.models.category import Category
from app.models.ticket import Ticket
from app.services.classification_service import (
    ClassificationResult,
    classify_ticket_description,
)
from app.services.ticket_report import BUILDING_NAME

CSRF_TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture()
def app():
    from app import create_app

    test_app = create_app("testing")
    test_app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

    with test_app.app_context():
        baseline_ticket_ids = set(db.session.scalars(select(Ticket.id)).all())
        baseline_categories = {
            category.code: category.is_active
            for category in db.session.scalars(select(Category)).all()
        }

        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.remove()
        db.session.configure(
            bind=connection, join_transaction_mode="create_savepoint"
        )

        try:
            yield test_app
        finally:
            db.session.remove()
            if transaction.is_active:
                transaction.rollback()
            connection.close()
            db.session.configure(bind=None)

            with db.engine.begin() as cleanup_connection:
                if baseline_ticket_ids:
                    cleanup_connection.execute(
                        delete(Ticket).where(
                            Ticket.id.notin_(baseline_ticket_ids)
                        )
                    )
                else:
                    cleanup_connection.execute(delete(Ticket))

                for code, is_active in baseline_categories.items():
                    cleanup_connection.execute(
                        update(Category)
                        .where(Category.code == code)
                        .values(is_active=is_active)
                    )

            db.engine.dispose()


@pytest.fixture(autouse=True)
def clear_cache():
    reset_model_cache()
    yield
    reset_model_cache()


@pytest.fixture()
def client(app):
    return app.test_client()


def _get_csrf_token(client):
    g.pop("csrf_token", None)
    response = client.get("/lapor")
    assert response.status_code == 200
    match = CSRF_TOKEN_PATTERN.search(response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


# ==============================================================================
# 1. Pengujian Pipeline Preprocessing NLP (FR-03)
# ==============================================================================
def test_preprocessor_case_folding():
    result = preprocess_text("LAMPU DI RUANG KELAS PADAM TOTAL")
    assert result.cleaned_text == result.cleaned_text.lower()
    assert "lampu" in result.tokens


def test_preprocessor_regex_cleaning_removes_urls_symbols():
    raw = "Proyektor rusak! Lihat bukti di https://example.com/foto.jpg @admin #sarpras !!!"
    result = preprocess_text(raw)
    assert "https" not in result.cleaned_text
    assert "example" not in result.cleaned_text
    assert "!" not in result.cleaned_text
    assert "@" not in result.cleaned_text
    assert "#" not in result.cleaned_text


def test_preprocessor_regex_cleaning_removes_digits_for_ml_vocabulary():
    """Memastikan angka dihapus pada teks kosakata NLP untuk vektorisasi."""
    raw = "AC 2 PK di meja nomor 14 rusak sejak jam 08.00 pagi"
    result = preprocess_text(raw)
    assert not any(char.isdigit() for char in result.cleaned_text)
    assert "2" not in result.tokens
    assert "14" not in result.tokens


def test_slang_normalization_preserves_embedded_words():
    """
    CRITICAL: Memastikan normalisasi slang 'ac' tidak merusak kata seperti 'kaca', 'baca', atau 'acak'.
    """
    raw = "kaca jendela retak dan mahasiswa sedang baca buku di ruang ac"
    normalized = normalize_slang(raw)
    # 'kaca' dan 'baca' tidak boleh terpengaruh
    assert "kaca" in normalized
    assert "baca" in normalized
    assert "kpendingin ruangan" not in normalized
    assert "bpendingin ruangan" not in normalized
    # Kata 'ac' mandiri wajib dinormalisasi
    assert "pendingin ruangan" in normalized


def test_preprocessor_slang_and_abbreviations():
    raw = "wifi di lab komputer gak bisa konek dan lemot bgt"
    result = preprocess_text(raw)
    # 'wifi' -> 'internet', 'lab' -> 'laboratorium', 'gak' -> 'tidak', 'lemot' -> 'lambat', 'bgt' -> 'sangat'
    assert "internet" in result.tokens
    assert "laboratorium" in result.tokens
    assert "lambat" in result.tokens or "lambat" in result.cleaned_text


def test_preprocessor_sastrawi_stemming_and_stopwords():
    raw = "kursi kuliah mengalami kerusakan yang sangat parah"
    result = preprocess_text(raw)
    # Stopwords seperti 'yang', 'sangat' dihapus oleh Sastrawi
    # 'mengalami' di-stem menjadi 'alami', 'kursi' menjadi 'kursi'
    assert "alami" in result.tokens
    assert "kursi" in result.tokens


def test_preprocessor_empty_or_whitespace():
    assert preprocess_text("") == PreprocessResult(cleaned_text="", tokens=[], token_count=0)
    assert preprocess_text("   \n\t  ") == PreprocessResult(cleaned_text="", tokens=[], token_count=0)
    assert preprocess_text("12345 !@#$%") == PreprocessResult(cleaned_text="", tokens=[], token_count=0)


# ==============================================================================
# 2. Pengujian Keamanan Pemuatan Model Joblib
# ==============================================================================
def test_safe_path_validation_rejects_path_traversal(tmp_path):
    trusted_dir = tmp_path / "trusted"
    trusted_dir.mkdir(parents=True, exist_ok=True)
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir(parents=True, exist_ok=True)
    evil_file = outside_dir / "evil.joblib"
    evil_file.touch()

    # Percobaan path traversal keluar dari direktori tepercaya
    with pytest.raises(ModelSecurityError):
        _validate_safe_path(str(evil_file), str(trusted_dir))

    with pytest.raises(ModelSecurityError):
        _validate_safe_path(str(trusted_dir / "../outside/evil.joblib"), str(trusted_dir))


def test_load_model_artifacts_raises_when_files_missing(tmp_path):
    trusted_dir = tmp_path / "models"
    trusted_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ModelNotAvailableError):
        load_model_artifacts(
            model_path=str(trusted_dir / "model.joblib"),
            vectorizer_path=str(trusted_dir / "vectorizer.joblib"),
            base_dir=str(trusted_dir),
        )


# ==============================================================================
# 3. Pengujian Graceful Fallback Manual (FR-10) Tanpa Kebocoran PII
# ==============================================================================
def test_fallback_activated_when_model_missing_without_exception(app, caplog):
    """
    Ketika model .joblib belum ada di disk:
    1. Mengembalikan ClassificationResult dengan is_fallback=True dan needs_manual_verification=True.
    2. Tidak memunculkan unhandled exception.
    3. Log TIDAK membocorkan teks mentah deskripsi pelapor (PII Protection).
    """
    with caplog.at_level(logging.INFO):
        secret_description = "AC bocor menetes ke laptop milik Budi Santoso 08123456789"
        result = classify_ticket_description(secret_description)

    assert isinstance(result, ClassificationResult)
    assert result.is_fallback is True
    assert result.predicted_category_id is None
    assert result.confidence_score is None
    assert result.needs_manual_verification is True
    assert result.fallback_reason == "MODEL_NOT_AVAILABLE"

    # Verifikasi ketat proteksi privasi: data sensitif tidak boleh tercatat di log
    log_output = caplog.text
    assert "Budi Santoso" not in log_output
    assert "08123456789" not in log_output
    assert secret_description not in log_output
    assert "text_len=" in log_output  # Hanya panjang teks yang dicatat


def test_fallback_on_empty_text():
    result = classify_ticket_description("   ")
    assert result.is_fallback is True
    assert result.fallback_reason == "EMPTY_DESCRIPTION"
    assert result.needs_manual_verification is True


# ==============================================================================
# 4. Pengujian Inferensi & Evaluasi Threshold 0.60 (Mocked Classifier)
# ==============================================================================
def test_mocked_classifier_above_threshold(app):
    """Skor probabilitas >= 0.60 menghasilkan needs_manual_verification = False."""
    mock_model = MagicMock()
    mock_model.classes_ = ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
    # Kelas K5 (Listrik, AC, dan penerangan) dengan probabilitas 0.8500
    mock_model.predict_proba.return_value = [[0.02, 0.03, 0.01, 0.02, 0.85, 0.05, 0.02]]

    mock_vectorizer = MagicMock()
    mock_vectorizer.transform.return_value = [[1, 0, 0]]

    result = classify_ticket_description(
        "AC di ruang kelas panas dan tidak dingin sama sekali",
        model_override=mock_model,
        vectorizer_override=mock_vectorizer,
    )

    assert result.is_fallback is False
    assert result.predicted_category_code == "K5"
    assert result.predicted_category_id is not None
    assert result.confidence_score == Decimal("0.8500")
    # Karena 0.85 >= 0.60 (threshold), verifikasi manual = False
    assert result.needs_manual_verification is False


def test_mocked_classifier_below_threshold(app):
    """Skor probabilitas < 0.60 menghasilkan needs_manual_verification = True (TBD-03)."""
    mock_model = MagicMock()
    mock_model.classes_ = ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
    # Probabilitas terbesar hanya 0.4200 pada K1
    mock_model.predict_proba.return_value = [[0.42, 0.20, 0.10, 0.10, 0.08, 0.05, 0.05]]

    mock_vectorizer = MagicMock()
    mock_vectorizer.transform.return_value = [[1, 0, 0]]

    result = classify_ticket_description(
        "Ada bau tidak sedap dekat proyektor atau toilet",
        model_override=mock_model,
        vectorizer_override=mock_vectorizer,
    )

    assert result.is_fallback is False
    assert result.predicted_category_code == "K1"
    assert result.confidence_score == Decimal("0.4200")
    # Karena 0.42 < 0.60, sistem menandai tiket perlu verifikasi manual
    assert result.needs_manual_verification is True


# ==============================================================================
# 5. Pengujian Integrasi Alur Pelaporan (/lapor) & Integritas Deskripsi Asli
# ==============================================================================
def test_report_submission_integrates_fallback_and_preserves_raw_description(client):
    """
    Memastikan bahwa saat pelapor submit di /lapor:
    1. Tiket tersimpan dengan status 'Baru'.
    2. Fallback aktif: needs_manual_verification = True, predicted_category_id = None.
    3. Teks deskripsi di database TETAP ASLI (angka 2 PK dan nomor meja TIDAK terhapus).
    4. Pelapor menerima respons sukses HTTP 200 tanpa error teknis.
    """
    csrf = _get_csrf_token(client)
    raw_description = "AC 2 PK di meja nomor 14 ruang kelas 2.3 bocor menetes deras."

    response = client.post(
        "/lapor",
        data={
            "csrf_token": csrf,
            "description": raw_description,
            "building_name": BUILDING_NAME,
            "floor_number": "2",
            "room_name": "Ruang 2.3",
            "location_detail": "Dekat jendela",
            "reporter_category_id": "",
            "reporter_name": "Pelapor Uji",
            "reporter_contact": "081233445566",
        },
    )
    assert response.status_code == 200
    assert "Laporan berhasil dikirim" in response.get_data(as_text=True)

    # Verifikasi data tiket di database
    ticket = db.session.scalar(
        select(Ticket).where(Ticket.room_name == "Ruang 2.3")
    )
    assert ticket is not None
    assert ticket.status == "Baru"
    assert ticket.needs_manual_verification is True
    assert ticket.predicted_category_id is None
    assert ticket.confidence_score is None

    # CRITICAL: Pastikan teks di basis data adalah deskripsi asli lengkap dengan angka
    assert ticket.description == raw_description
    assert "2 PK" in ticket.description
    assert "meja nomor 14" in ticket.description
