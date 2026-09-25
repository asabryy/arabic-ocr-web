from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services import quota


def test_limits_for_plan():
    assert quota.limits_for("free").daily_pages == 10
    assert quota.limits_for(None).plan == "free"
    assert quota.limits_for("unknown").plan == "free"
    assert quota.limits_for("pro").daily_pages > quota.limits_for("free").daily_pages


def test_pro_max_document_does_not_consume_the_whole_day():
    """On a paid plan the per-document figure is sold as a repeatable allowance, so
    it must sit below the daily cap. At parity one maximum-size document exhausts
    the day and the advertised number is usable exactly once.

    Free is deliberately at parity (10/10): "one 10-page document a day" is the
    offer, not a promise of repeated use.
    """
    pro = quota.limits_for("pro")
    assert pro.max_doc_pages < pro.daily_pages, (
        f"per-document cap {pro.max_doc_pages} must be below the daily cap "
        f"{pro.daily_pages}"
    )


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


def test_release_targets_the_reservation_day_not_today(db):
    """A task reserved at 23:59 and failing at 00:00 must credit the day it was
    reserved on. Crediting 'today' zeroed a fresh day's counter and handed out a
    repeatable nightly cap bypass."""
    from datetime import date, timedelta

    yesterday = date.today() - timedelta(days=1)
    quota.reserve(db, 1, 10, 10, "free", day=yesterday)
    quota.reserve(db, 1, 10, 10, "free")  # a new day, a fresh allowance

    quota.release(db, 1, 10, day=yesterday)

    assert quota.used_today(db, 1) == 10, "today's counter must be untouched"
    assert quota.used_today(db, 1, day=yesterday) == 0


def test_unlimited_tier_is_recognised():
    """limits_for() falls through to FREE for unknown plans, so a tier added to the
    schema but not here would silently give a comped account *less* than Pro."""
    u = quota.limits_for("unlimited")
    pro = quota.limits_for("pro")
    assert u.plan == "unlimited"
    assert u.daily_pages > pro.daily_pages
    assert u.max_doc_pages > pro.max_doc_pages


def test_an_unknown_plan_still_falls_back_to_free():
    """The fall-through is the safety property: a typo must never grant pages."""
    assert quota.limits_for("ulimited").plan == "free"
    assert quota.limits_for("PRO").plan == "free"
    assert quota.limits_for(None).plan == "free"
