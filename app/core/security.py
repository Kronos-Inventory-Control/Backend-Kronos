"""Seguridad de contraseñas de Kronos Inventory Control (Argon2id)."""

from pwdlib import PasswordHash

# Argon2id: algoritmo recomendado para proteger contraseñas.
password_hasher = PasswordHash.recommended()

MIN_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    """
    Recibe una contraseña y devuelve su hash seguro.

    La contraseña original nunca se almacena en la base de datos.
    """

    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )

    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba si una contraseña coincide con el hash almacenado."""

    return password_hasher.verify(plain_password, hashed_password)
