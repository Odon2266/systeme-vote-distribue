import hashlib
import os

SECRET_SALT = os.getenv("SECRET_SALT", "default_salt")

def hash_vote(cin: str, candidat_numero: int) -> str:
    """Génère un hash SHA-256 unique pour garantir l'immuabilité du vote."""
    raw_string = f"{cin}-{candidat_numero}-{SECRET_SALT}"
    return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()

def hash_password(password: str) -> str:
    """Hache un mot de passe brut en SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()