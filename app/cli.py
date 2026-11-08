"""Perintah CLI lokal untuk provisioning akun staf (SECURITY.md §4.4).

Hanya perintah ``create-staff``. Password selalu dimasukkan lewat prompt
tersembunyi; password maupun hash tidak pernah dicetak.
"""
import re

import click
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.user import User
from app.utils.decorators import STAFF_ROLES
from app.utils.password import hash_password

USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,64}$")
MIN_PASSWORD_LENGTH = 12
FULL_NAME_MAX_LENGTH = 120


def validate_username(username: str) -> str:
    """Normalisasi dan validasi username; lempar ClickException bila tidak valid."""
    normalized = (username or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise click.ClickException(
            "Username tidak valid. Gunakan 3-64 karakter: huruf kecil, angka, "
            "titik, garis bawah, atau tanda hubung."
        )
    return normalized


def validate_password(password: str, username: str) -> str:
    """Validasi kebijakan password minimal; tolak password yang menyamai username."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise click.ClickException(
            f"Password minimal {MIN_PASSWORD_LENGTH} karakter."
        )
    if password.strip().lower() == username:
        raise click.ClickException("Password tidak boleh sama dengan username.")
    return password


@click.command("create-staff")
@click.option("--username", prompt=True, help="Username staf (huruf kecil, 3-64 karakter).")
@click.option(
    "--role",
    prompt=True,
    type=click.Choice(sorted(STAFF_ROLES)),
    help="Peran staf yang diberikan.",
)
@click.option("--full-name", prompt="Nama lengkap", help="Nama lengkap staf.")
def create_staff(username: str, role: str, full_name: str) -> None:
    """Buat satu akun staf internal (admin_sarpras, teknisi, atau pimpinan)."""
    cleaned_username = validate_username(username)

    cleaned_full_name = (full_name or "").strip()
    if not cleaned_full_name:
        raise click.ClickException("Nama lengkap wajib diisi.")
    if len(cleaned_full_name) > FULL_NAME_MAX_LENGTH:
        raise click.ClickException(
            f"Nama lengkap maksimal {FULL_NAME_MAX_LENGTH} karakter."
        )

    if role not in STAFF_ROLES:
        raise click.ClickException(
            "Role tidak valid untuk akun staf: " + ", ".join(sorted(STAFF_ROLES))
        )

    existing_id = db.session.scalar(
        select(User.id).where(User.username == cleaned_username)
    )
    if existing_id is not None:
        raise click.ClickException(f"Username '{cleaned_username}' sudah dipakai.")

    password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
    validate_password(password, cleaned_username)

    user = User(
        username=cleaned_username,
        full_name=cleaned_full_name,
        role=role,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise click.ClickException(f"Username '{cleaned_username}' sudah dipakai.")

    click.echo(f"Akun staf dibuat: {cleaned_username} (role={role})")


def register_cli(app) -> None:
    """Daftarkan perintah CLI KlasiFas pada instance aplikasi Flask."""
    app.cli.add_command(create_staff)
