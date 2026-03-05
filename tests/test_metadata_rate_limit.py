from music_cleanup.metadata import RateLimiter


def test_rate_limiter_waits_between_calls():
    now = [0.0]
    sleeps: list[float] = []

    def fake_now() -> float:
        return now[0]

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(2.0, now_fn=fake_now, sleep_fn=fake_sleep)  # 0.5s interval

    limiter.acquire()
    limiter.acquire()
    limiter.acquire()

    assert sleeps == [0.5, 0.5]
