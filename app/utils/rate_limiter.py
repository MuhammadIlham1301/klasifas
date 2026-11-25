"""
Utilitas pembatasan frekuensi permintaan (Rate Limiter) berbasis in-memory sliding window.
Digunakan untuk melindungi endpoint publik dari serangan brute-force dan enumerasi (FR-02).
"""
import math
import threading
import time
from collections import defaultdict
from flask import Request, current_app, has_app_context


class SlidingWindowRateLimiter:
    """
    Rate limiter berbasis in-memory sliding window dengan jaminan thread safety.

    Keterbatasan Arsitektural (Dicatat Resmi):
    1. Multi-Worker: Status disimpan dalam memori proses saat ini. Jika menggunakan
       server WSGI multi-worker (seperti Gunicorn N workers), kuota efektif per IP
       dapat mencapai N x limit karena worker tidak berbagi memori.
    2. Restart: Jika proses aplikasi di-restart, riwayat sliding window akan ter-reset.
    Untuk skala produksi kampus multi-server, delegasikan ke Nginx limit_req atau Redis.
    """

    def __init__(self, limit: int = 15, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _resolve_limits(self) -> tuple[int, int]:
        return self.limit, self.window_seconds

    def hit(self, key: str) -> tuple[bool, int]:
        """
        Catat percobaan akses untuk `key` dan tentukan apakah permintaan diizinkan.

        Args:
            key (str): Kunci unik pengenal pemanggil (misalnya alamat IP klien).

        Returns:
            tuple[bool, int]:
                - bool: True jika permintaan diizinkan, False jika kuota terlampaui.
                - int: Sisa detik sebelum pemanggil boleh mencoba lagi (Retry-After).
                       Bernilai 0 jika permintaan diizinkan.
        """
        limit, window_seconds = self._resolve_limits()
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            # 1. Bersihkan entri kedaluwarsa untuk kunci aktif ini
            timestamps = [t for t in self._requests.get(key, []) if t > cutoff]

            # 2. Pembersihan proaktif berkala untuk menjaga batas memori (bounded memory)
            if len(self._requests) > 200:
                self._prune_expired_locked(cutoff)

            # 3. Evaluasi kuota
            if len(timestamps) >= limit:
                # Kuota terlampaui: hitung Retry-After dari request tertua dalam window
                oldest_timestamp = timestamps[0]
                retry_after = max(1, math.ceil((oldest_timestamp + window_seconds) - now))
                self._requests[key] = timestamps
                return False, int(retry_after)

            # 4. Kuota tersedia: catat timestamp saat ini
            timestamps.append(now)
            self._requests[key] = timestamps
            return True, 0

    def _prune_expired_locked(self, cutoff: float) -> None:
        """Bersihkan IP yang seluruh timestamp-nya sudah kedaluwarsa (harus dalam lock)."""
        stale_keys = [
            k for k, ts in self._requests.items()
            if not ts or ts[-1] <= cutoff
        ]
        for k in stale_keys:
            del self._requests[k]

    def clear(self, key: str) -> None:
        """Hapus riwayat satu kunci setelah autentikasi berhasil."""
        with self._lock:
            self._requests.pop(key, None)

    def reset(self) -> None:
        """Kosongkan seluruh riwayat rate limiter (berguna untuk isolasi pengujian)."""
        with self._lock:
            self._requests.clear()


def get_client_ip(req: Request) -> str:
    """
    Ekstrak alamat IP klien secara aman.

    Catatan Reverse Proxy:
    - Jika TRUSTED_PROXIES_COUNT > 0, middleware Werkzeug ProxyFix telah mengoreksi
      req.remote_addr secara terpercaya berdasarkan jumlah hop proxy resmi.
    - Jika ProxyFix nonaktif (default), req.remote_addr dibaca langsung dari koneksi socket
      tanpa mempercayai header X-Forwarded-For mentah dari klien yang berpotensi di-spoof.
    """
    return (req.remote_addr or "127.0.0.1").strip()


class ConfigBoundRateLimiter(SlidingWindowRateLimiter):
    """Rate limiter yang membaca konfigurasi Flask saat app context aktif."""

    def _resolve_limits(self) -> tuple[int, int]:
        if has_app_context():
            return (
                current_app.config.get("TRACK_RATE_LIMIT_PER_MINUTE", 15),
                current_app.config.get("TRACK_RATE_LIMIT_WINDOW_SECONDS", 60),
            )
        return 15, 60


# Instance singleton default untuk pelacakan tiket publik (/lacak)
track_limiter = ConfigBoundRateLimiter(limit=15, window_seconds=60)

