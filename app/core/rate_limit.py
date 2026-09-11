import time
from threading import Lock

from fastapi import HTTPException

from app.core.config import settings


class SlidingWindowRateLimiter:
    """In-process sliding-window limiter for a single global key.

    Not distributed — each app process tracks its own counter, and it
    resets on restart. Sufficient for a single-instance deployment; a
    multi-instance deployment would need a shared store (e.g. Redis)
    instead.

    Global rather than per-user: this app currently runs without
    per-request authentication, so there is no user identity to key
    the limiter by.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: int,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: list[float] = []
        self._lock = Lock()

    def check(self) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            self._hits[:] = [
                hit
                for hit in self._hits
                if hit > cutoff
            ]

            if len(self._hits) >= self.limit:
                retry_after = int(
                    self._hits[0] + self.window_seconds - now
                ) + 1
                return False, retry_after

            self._hits.append(now)
            return True, 0


generate_rate_limiter = SlidingWindowRateLimiter(
    limit=settings.generate_rate_limit_count,
    window_seconds=(
        settings.generate_rate_limit_window_seconds
    ),
)


async def enforce_generate_rate_limit() -> None:
    allowed, retry_after = generate_rate_limiter.check()

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                "Generation limit reached "
                f"({settings.generate_rate_limit_count} per "
                f"{settings.generate_rate_limit_window_seconds // 60} "
                "minutes). Try again later."
            ),
            headers={
                "Retry-After": str(retry_after)
            },
        )
