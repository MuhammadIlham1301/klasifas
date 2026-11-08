"""Validasi dan penyimpanan foto bukti tiket (FR-01)."""
import os
import secrets
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

JPEG_MAGIC = b"\xff\xd8\xff"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_EXTENSIONS = frozenset({"jpg", "jpeg"})
PNG_EXTENSIONS = frozenset({"png"})


class PhotoValidationError(ValueError):
    """File foto tidak lolos validasi keamanan."""


class PhotoStorageError(RuntimeError):
    """File foto gagal disimpan atau dihapus."""


@dataclass(frozen=True)
class ValidatedPhoto:
    """Foto yang sudah divalidasi dan dibersihkan metadata-nya."""

    data: bytes
    extension: str
    mime_type: str
    size_bytes: int


@dataclass(frozen=True)
class StoredPhoto:
    """Metadata file foto yang sudah tersimpan."""

    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


def _detect_magic(data: bytes) -> str | None:
    if data.startswith(JPEG_MAGIC):
        return "jpeg"
    if data.startswith(PNG_MAGIC):
        return "png"
    return None


def _read_limited(stream, max_size_bytes: int) -> bytes:
    stream.seek(0)
    data = stream.read(max_size_bytes + 1)
    if len(data) > max_size_bytes:
        raise PhotoValidationError(
            f"Ukuran foto maksimal {max_size_bytes // (1024 * 1024)} MB."
        )
    if not data:
        raise PhotoValidationError("File foto kosong.")
    return data


def _decode_and_clean(data: bytes, max_dimension: int) -> tuple[bytes, str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            with Image.open(BytesIO(data)) as verifier:
                verifier.verify()

            with Image.open(BytesIO(data)) as image:
                image.load()
                width, height = image.size
                if width > max_dimension or height > max_dimension:
                    raise PhotoValidationError(
                        f"Dimensi foto maksimal {max_dimension} x {max_dimension} piksel."
                    )

                if image.format == "JPEG":
                    if image.mode not in ("RGB", "L"):
                        image = image.convert("RGB")
                    output = BytesIO()
                    image.save(
                        output,
                        format="JPEG",
                        quality=90,
                        optimize=True,
                    )
                    return output.getvalue(), "jpeg"

                if image.format == "PNG":
                    output = BytesIO()
                    image.save(output, format="PNG", optimize=True)
                    return output.getvalue(), "png"

                raise PhotoValidationError("Format foto tidak didukung.")
    except PhotoValidationError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise PhotoValidationError("File foto bukan gambar yang valid.") from exc


def validate_photo(
    upload: FileStorage | None,
    *,
    max_size_bytes: int,
    max_dimension: int,
    allowed_extensions: frozenset[str],
    allowed_mime_types: frozenset[str],
) -> ValidatedPhoto | None:
    """Validasi foto opsional dan kembalikan data yang sudah dibersihkan."""
    if upload is None or not upload.filename:
        return None

    safe_name = secure_filename(upload.filename)
    if not safe_name:
        raise PhotoValidationError("Nama file foto tidak valid.")

    extension = Path(safe_name).suffix.lower().lstrip(".")
    if extension not in allowed_extensions:
        raise PhotoValidationError(
            "Format foto harus JPG, JPEG, atau PNG."
        )

    client_mime = (upload.mimetype or "").lower()
    if client_mime not in allowed_mime_types:
        raise PhotoValidationError("Tipe MIME foto tidak diizinkan.")

    data = _read_limited(upload.stream, max_size_bytes)
    detected = _detect_magic(data)
    if detected is None:
        raise PhotoValidationError("File foto bukan gambar yang valid.")

    if detected == "jpeg" and extension not in JPEG_EXTENSIONS:
        raise PhotoValidationError("Ekstensi foto tidak sesuai dengan isi file.")
    if detected == "png" and extension not in PNG_EXTENSIONS:
        raise PhotoValidationError("Ekstensi foto tidak sesuai dengan isi file.")
    if client_mime == "image/jpeg" and detected != "jpeg":
        raise PhotoValidationError("Tipe MIME foto tidak sesuai dengan isi file.")
    if client_mime == "image/png" and detected != "png":
        raise PhotoValidationError("Tipe MIME foto tidak sesuai dengan isi file.")

    cleaned_data, actual_format = _decode_and_clean(data, max_dimension)
    if actual_format == "jpeg" and extension not in JPEG_EXTENSIONS:
        raise PhotoValidationError("Ekstensi foto tidak sesuai dengan isi file.")
    if actual_format == "png" and extension not in PNG_EXTENSIONS:
        raise PhotoValidationError("Ekstensi foto tidak sesuai dengan isi file.")

    if len(cleaned_data) > max_size_bytes:
        raise PhotoValidationError(
            f"Ukuran foto maksimal {max_size_bytes // (1024 * 1024)} MB."
        )

    if actual_format == "jpeg":
        return ValidatedPhoto(
            data=cleaned_data,
            extension="jpg",
            mime_type="image/jpeg",
            size_bytes=len(cleaned_data),
        )

    return ValidatedPhoto(
        data=cleaned_data,
        extension="png",
        mime_type="image/png",
        size_bytes=len(cleaned_data),
    )


def _safe_destination(root: Path, filename: str) -> Path:
    destination = (root / Path(filename).name).resolve()
    if destination.parent != root:
        raise PhotoStorageError("Lokasi penyimpanan foto tidak valid.")
    return destination


def store_photo(photo: ValidatedPhoto, upload_folder: str) -> StoredPhoto:
    """Simpan foto dengan nama acak di direktori non-publik."""
    root = Path(upload_folder).resolve()
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PhotoStorageError("Direktori penyimpanan foto tidak tersedia.") from exc

    for _ in range(5):
        filename = f"{secrets.token_hex(16)}.{photo.extension}"
        destination = _safe_destination(root, filename)
        temporary = root / f".{filename}.tmp"

        try:
            with temporary.open("xb") as handle:
                handle.write(photo.data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except FileExistsError:
            temporary.unlink(missing_ok=True)
            continue
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise PhotoStorageError("File foto gagal disimpan.") from exc

        try:
            os.chmod(destination, 0o600)
        except OSError:
            pass

        return StoredPhoto(
            filename=filename,
            mime_type=photo.mime_type,
            size_bytes=photo.size_bytes,
            uploaded_at=datetime.now(timezone.utc),
        )

    raise PhotoStorageError("File foto gagal disimpan.")


def delete_photo(filename: str, upload_folder: str) -> None:
    """Hapus file foto berdasarkan nama simpan yang tersimpan."""
    if not filename:
        return

    root = Path(upload_folder).resolve()
    destination = _safe_destination(root, filename)
    try:
        destination.unlink(missing_ok=True)
    except OSError as exc:
        raise PhotoStorageError("File foto gagal dihapus.") from exc
