from src.infra.rate_limit import PerMinuteRateLimiter


def test_per_minute_rate_limiter_waits_after_limit():
    now = [0.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    limiter = PerMinuteRateLimiter(2, monotonic=lambda: now[0], sleep=sleep)

    limiter.wait()
    limiter.wait()
    limiter.wait()

    assert sleeps == [60.0]
