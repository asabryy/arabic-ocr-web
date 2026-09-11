from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services import quota


def test_limits_for_plan():
    assert quota.limits_for("free").daily_pages == 10
    assert quota.limits_for("pro").max_doc_pages == 100
    assert quota.limits_for(None).plan == "free"
    assert quota.limits_for("unknown").plan == "free"


def test_reserve_within_limit_accumulates(db):
    assert quota.reserve(db, 1, 3, 10, "free") == 3
    assert quota.reserve(db, 1, 4, 10, "free") == 7
    assert quota.used_today(db, 1) == 7


def test_reserve_over_limit_raises_with_used(db):
    quota.reserve(db, 1, 8, 10, "free")
    with pytest.raises(quota.QuotaExceeded) as ex:
        quota.reserve(db, 1, 3, 10, "free")
    assert ex.value.code == "daily_pages_exceeded"
    assert ex.value.used == 8 and ex.value.limit == 10 and ex.value.plan == "free"
    assert quota.used_today(db, 1) == 8  # nothing was consumed


def test_reserve_more_than_limit_on_empty_day(db):
    with pytest.raises(quota.QuotaExceeded):
        quota.reserve(db, 1, 11, 10, "free")
    assert quota.used_today(db, 1) == 0


def test_release_floors_at_zero(db):
    quota.reserve(db, 1, 2, 10, "free")
    quota.release(db, 1, 5)
    assert quota.used_today(db, 1) == 0


def test_get_plan(db):
    assert quota.get_plan(db, 1) == "free"
    assert quota.get_plan(db, 2) == "pro"
    assert quota.get_plan(db, 999) == "free"  # unknown user falls back to free


def test_concurrent_reserves_never_exceed_limit(db):
    """20 parallel 1-page reservations against a 10-page limit → exactly 10 succeed."""

    def attempt(_):
        try:
            quota.reserve(db, 1, 1, 10, "free")
            return True
        except quota.QuotaExceeded:
            return False

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(attempt, range(20)))

    assert results.count(True) == 10
    assert results.count(False) == 10
    assert quota.used_today(db, 1) == 10
