"""Rate limiting en mémoire (mono-serveur) pour /api/auth/login.

5 tentatives échouées par (email, IP) sur 15 minutes → 429.
Simple et suffisant pour une instance mono-serveur (pas de Redis).
"""
import time
from collections import defaultdict, deque

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

_failures: dict[str, deque[float]] = defaultdict(deque)


def _key(email: str, ip: str) -> str:
    return f"{email.lower().strip()}|{ip}"


def check_login_allowed(email: str, ip: str) -> None:
    """Lève une exception si le quota de tentatives est dépassé."""
    from fastapi import HTTPException
    dq = _failures[_key(email, ip)]
    now = time.monotonic()
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()
    if len(dq) >= MAX_ATTEMPTS:
        raise HTTPException(
            429,
            "Trop de tentatives de connexion, réessayez dans quelques minutes",
        )


def record_failure(email: str, ip: str) -> None:
    _failures[_key(email, ip)].append(time.monotonic())


def clear_failures(email: str, ip: str) -> None:
    _failures.pop(_key(email, ip), None)
