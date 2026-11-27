"""The feed token: validation at start and constant-time comparison."""

import hmac

MIN_TOKEN_LENGTH = 32


def validate_token(token: str | None) -> str:
    """Return the token, or raise ValueError if it is missing or too short.

    The message never contains the token itself.
    """
    if not token or len(token) < MIN_TOKEN_LENGTH:
        raise ValueError(f"FEED_TOKEN must be at least {MIN_TOKEN_LENGTH} characters long")
    return token


def token_matches(candidate: str, expected: str) -> bool:
    """Compare a token taken from the address with the expected one in constant time."""
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))
