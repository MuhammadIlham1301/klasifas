"""
Layanan inferensi Machine Learning dan Graceful Fallback Manual (FR-03, FR-10).
"""
from dataclasses import dataclass
from decimal import Decimal
import logging
import os
from typing import Any

from flask import current_app, has_app_context
from sqlalchemy import select

from app.extensions import db
from app.models.category import Category
from app.ml.classifier import (
    ModelNotAvailableError,
    ModelSecurityError,
    load_model_artifacts,
    predict_category,
)
from app.ml.preprocessor import preprocess_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassificationResult:
    """Kontrak keluaran inferensi klasifikasi keluhan."""
    predicted_category_id: int | None
    predicted_category_code: str | None
    confidence_score: Decimal | None
    needs_manual_verification: bool
    is_fallback: bool
    fallback_reason: str | None


def _fallback_result(reason: str) -> ClassificationResult:
    """Helper pembentuk hasil fallback standar FR-10."""
    return ClassificationResult(
        predicted_category_id=None,
        predicted_category_code=None,
        confidence_score=None,
        needs_manual_verification=True,
        is_fallback=True,
        fallback_reason=reason,
    )


def classify_ticket_description(
    description: str | None,
    model_override: Any = None,
    vectorizer_override: Any = None,
) -> ClassificationResult:
    """
    Eksekusi alur pra-pemrosesan teks dan inferensi Naive Bayes dengan Graceful Fallback (FR-10).

    Aturan Keamanan dan Privasi:
    1. Pencatatan log kegagalan TIDAK BOLEH memuat teks mentah deskripsi demi mencegah
       kebocoran data pribadi (PII pelapor).
    2. Jika artefak model belum tersedia atau terjadi galat komputasi, fungsi secara
       otomatis mengembalikan penanda fallback manual (needs_manual_verification = True)
       tanpa menghentikan proses penyimpanan tiket pelapor.
    """
    text_len = len(description) if description else 0

    # 1. Validasi masukan dasar
    if not description or not str(description).strip():
        logger.info(
            "Klasifikasi fallback: deskripsi kosong (text_len=%d)", text_len
        )
        return _fallback_result("EMPTY_DESCRIPTION")

    # 2. Tahap Pra-pemrosesan NLP (Case folding, regex, slang, stopword, Sastrawi stemming)
    try:
        preprocessed = preprocess_text(description)
    except Exception as exc:
        logger.warning(
            "Klasifikasi fallback: pra-pemrosesan gagal (exc=%s, text_len=%d)",
            exc.__class__.__name__,
            text_len,
        )
        return _fallback_result(f"PREPROCESSING_ERROR:{exc.__class__.__name__}")

    if not preprocessed.cleaned_text:
        logger.info(
            "Klasifikasi fallback: tidak ada token tersisa setelah pra-pemrosesan (text_len=%d)",
            text_len,
        )
        return _fallback_result("NO_VALID_TOKENS")

    # 3. Pemuatan Artefak Model & Vectorizer (.joblib)
    model = model_override
    vectorizer = vectorizer_override

    if model is None or vectorizer is None:
        try:
            if has_app_context():
                base_dir = current_app.config.get(
                    "BASE_DIR",
                    os.path.abspath(
                        os.path.dirname(
                            os.path.dirname(os.path.dirname(__file__))
                        )
                    ),
                )
                models_dir = os.path.join(base_dir, "app", "ml", "models")
                model_path = current_app.config.get(
                    "ML_MODEL_PATH", os.path.join(models_dir, "model.joblib")
                )
                vectorizer_path = current_app.config.get(
                    "ML_VECTORIZER_PATH",
                    os.path.join(models_dir, "vectorizer.joblib"),
                )
            else:
                base_dir = os.path.abspath(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(__file__))
                    )
                )
                models_dir = os.path.join(base_dir, "app", "ml", "models")
                model_path = os.path.join(models_dir, "model.joblib")
                vectorizer_path = os.path.join(models_dir, "vectorizer.joblib")

            loaded_model, loaded_vectorizer = load_model_artifacts(
                model_path=model_path,
                vectorizer_path=vectorizer_path,
                base_dir=models_dir,
            )
            model = model or loaded_model
            vectorizer = vectorizer or loaded_vectorizer
        except ModelNotAvailableError:
            logger.info(
                "Klasifikasi fallback FR-10: artefak model .joblib belum tersedia (text_len=%d)",
                text_len,
            )
            return _fallback_result("MODEL_NOT_AVAILABLE")
        except ModelSecurityError as exc:
            logger.error(
                "Klasifikasi fallback FR-10: pelanggaran keamanan jalur model (exc=%s, text_len=%d)",
                exc.__class__.__name__,
                text_len,
            )
            return _fallback_result("MODEL_SECURITY_VIOLATION")
        except Exception as exc:
            logger.error(
                "Klasifikasi fallback FR-10: gagal memuat model (exc=%s, text_len=%d)",
                exc.__class__.__name__,
                text_len,
            )
            return _fallback_result(f"MODEL_LOAD_ERROR:{exc.__class__.__name__}")

    # 4. Komputasi Inferensi Naive Bayes
    try:
        predicted_code, raw_score = predict_category(
            preprocessed.cleaned_text, model, vectorizer
        )
    except Exception as exc:
        logger.warning(
            "Klasifikasi fallback FR-10: inferensi gagal (exc=%s, text_len=%d)",
            exc.__class__.__name__,
            text_len,
        )
        return _fallback_result(f"INFERENCE_ERROR:{exc.__class__.__name__}")

    # 5. Resolusi ID Kategori dari Basis Data
    category_id = db.session.scalar(
        select(Category.id).where(Category.code == predicted_code)
    )
    if category_id is None:
        logger.warning(
            "Klasifikasi fallback: kode kategori '%s' tidak ditemukan di basis data",
            predicted_code,
        )
        return _fallback_result("CATEGORY_NOT_FOUND_IN_DB")

    # 6. Evaluasi Ambang Batas Keyakinan (Placeholder TBD: 0.60)
    if has_app_context():
        threshold = float(current_app.config.get("ML_CONFIDENCE_THRESHOLD", 0.60))
    else:
        threshold = 0.60
    confidence_decimal = Decimal(f"{raw_score:.4f}")
    needs_manual = raw_score < threshold

    return ClassificationResult(
        predicted_category_id=category_id,
        predicted_category_code=predicted_code,
        confidence_score=confidence_decimal,
        needs_manual_verification=needs_manual,
        is_fallback=False,
        fallback_reason=None,
    )
