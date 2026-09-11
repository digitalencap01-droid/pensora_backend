import time

from app.core.rate_limit import (
    SlidingWindowRateLimiter,
)


def test_allows_calls_up_to_the_limit():
    limiter = SlidingWindowRateLimiter(
        limit=3, window_seconds=60
    )

    results = [
        limiter.check()[0] for _ in range(3)
    ]

    assert results == [True, True, True]


def test_blocks_once_the_limit_is_exceeded():
    limiter = SlidingWindowRateLimiter(
        limit=2, window_seconds=60
    )

    limiter.check()
    limiter.check()
    allowed, retry_after = limiter.check()

    assert allowed is False
    assert retry_after > 0


def test_old_hits_fall_out_of_the_window():
    limiter = SlidingWindowRateLimiter(
        limit=1, window_seconds=60
    )

    # Simulate a hit from well outside the window by writing directly
    # into the internal store rather than sleeping in a test.
    limiter._hits.append(time.time() - 120)

    allowed, _ = limiter.check()

    assert allowed is True
