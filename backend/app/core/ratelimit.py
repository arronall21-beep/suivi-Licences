"""Limiteur simple de tentatives de connexion échouées (en mémoire, par processus)."""

import time
from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60

_failures: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def _purge(key: tuple[str, str], now: float) -> deque[float]:
    q = _failures[key]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    return q


def retry_after(ip: str, email: str) -> int:
    """Secondes d'attente restantes si la limite est atteinte, sinon 0."""
    now = time.monotonic()
    q = _purge((ip, email.lower()), now)
    if len(q) >= MAX_FAILURES:
        return int(WINDOW_SECONDS - (now - q[0])) + 1
    return 0


def register_failure(ip: str, email: str) -> None:
    now = time.monotonic()
    _purge((ip, email.lower()), now).append(now)


def reset(ip: str, email: str) -> None:
    _failures.pop((ip, email.lower()), None)


def clear_all() -> None:
    _failures.clear()
