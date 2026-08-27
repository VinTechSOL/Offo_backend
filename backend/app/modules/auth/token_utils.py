import hashlib
import secrets


def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure refresh token.

    The raw token is returned only to the authentication flow.
    It must never be stored directly in the database.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """
    Hash the refresh token before storing/looking it up in the database.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()