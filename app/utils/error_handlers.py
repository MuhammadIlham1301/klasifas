"""
Handler halaman error KlasiFas: 403, 404, dan 500.

Status HTTP tetap dipertahankan dan detail teknis internal tidak pernah
diteruskan ke pengguna (khususnya pada 500).
"""
from flask import g, render_template


ERROR_SPECS = {
    403: {
        "icon": "bi-shield-lock",
        "eyebrow": "Akses Ditolak",
        "heading": "Anda tidak memiliki akses ke halaman ini",
        "message": (
            "Halaman ini hanya tersedia untuk peran tertentu. "
            "Pastikan Anda masuk dengan akun yang sesuai, atau kembali ke halaman utama peran Anda."
        ),
    },
    404: {
        "icon": "bi-compass",
        "eyebrow": "Halaman Tidak Ditemukan",
        "heading": "Halaman yang Anda cari tidak tersedia",
        "message": (
            "Tautan mungkin sudah berubah atau data yang diminta tidak ada. "
            "Periksa kembali alamat halaman atau gunakan navigasi di bawah ini."
        ),
    },
    500: {
        "icon": "bi-exclamation-triangle",
        "eyebrow": "Kesalahan Server",
        "heading": "Terjadi kesalahan pada sistem",
        "message": (
            "Permintaan Anda belum dapat diproses. Silakan coba beberapa saat lagi "
            "atau hubungi pengelola sistem apabila masalah berlanjut."
        ),
    },
}


def _role_home():
    """Kembalikan (href, label) halaman utama sesuai peran pengguna saat ini."""
    user = getattr(g, "current_user", None)
    role = getattr(user, "role", None)

    if role == "admin_sarpras":
        return ("admin.ticket_queue", "Kembali ke Antrean Sarpras")
    if role == "teknisi":
        return ("technician.ticket_queue", "Kembali ke Papan Tugas")
    if role == "pimpinan":
        return ("dashboard.dashboard_view", "Kembali ke Dasbor")
    return (None, None)


def _render_error(status_code):
    spec = ERROR_SPECS[status_code]
    endpoint, label = _role_home()
    back_href = None
    if endpoint is not None:
        from flask import url_for

        back_href = url_for(endpoint)
    return (
        render_template(
            "errors/error.html",
            status_code=status_code,
            icon=spec["icon"],
            eyebrow=spec["eyebrow"],
            heading=spec["heading"],
            message=spec["message"],
            back_href=back_href,
            back_label=label,
        ),
        status_code,
    )


def register_error_handlers(app):
    """Daftarkan handler error 403, 404, dan 500 pada aplikasi Flask."""

    @app.errorhandler(403)
    def forbidden(_error):
        return _render_error(403)

    @app.errorhandler(404)
    def not_found(_error):
        return _render_error(404)

    @app.errorhandler(500)
    def server_error(_error):
        return _render_error(500)
