"""Plan limits and atomic daily page accounting.

The reservation is a single Postgres statement so concurrent /convert calls for the
same user can never over-spend: `INSERT ... ON CONFLICT DO UPDATE` takes the row
lock, concurrent statements serialize on it, and each re-evaluates the WHERE guard
against the committed value.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Engine, select, text

from app.core.config import settings
from app.db.tables import usage_daily, users
from app.models.conversion_attempt import conversion_attempts

logger = logging.getLogger("doc-manager.quota")


@dataclass(frozen=True)
class PlanLimits:
    plan: str
    daily_pages: int
    max_doc_pages: int


class QuotaExceeded(Exception):
    def __init__(self, code: str, limit: int, used: int, plan: str):
        super().__init__(code)
        self.code = code
        self.limit = limit
        self.used = used
        self.plan = plan


def limits_for(plan: str | None) -> PlanLimits:
    """Limits for an account tier.

    Note the fall-through: an unrecognised plan gets FREE limits, not an error. That
    is deliberate (a typo must never hand out unlimited pages) but it is also why a
    new tier has to be added HERE as well as to the schema — setting users.plan to a
    value this function does not know silently *downgrades* the account.
    """
    if plan == "unlimited":
        return PlanLimits(
            "unlimited",
            settings.PLAN_UNLIMITED_DAILY_PAGES,
            settings.PLAN_UNLIMITED_MAX_DOC_PAGES,
        )
    if plan == "pro":
        return PlanLimits("pro", settings.PLAN_PRO_DAILY_PAGES, settings.PLAN_PRO_MAX_DOC_PAGES)
    return PlanLimits("free", settings.PLAN_FREE_DAILY_PAGES, settings.PLAN_FREE_MAX_DOC_PAGES)


def today() -> date:
    """Quota day boundary is UTC midnight."""
    return datetime.now(UTC).date()


def next_reset() -> datetime:
    return datetime.combine(today() + timedelta(days=1), datetime.min.time(), tzinfo=UTC)


def get_plan(engine: Engine, user_id: int) -> str:
    with engine.connect() as conn:
        row = conn.execute(select(users.c.plan).where(users.c.id == user_id)).first()
    return row[0] if row else "free"


def used_today(engine: Engine, user_id: int, day: date | None = None) -> int:
    day = day or today()
    with engine.connect() as conn:
        row = conn.execute(
            select(usage_daily.c.pages).where(
                usage_daily.c.user_id == user_id, usage_daily.c.day == day
            )
        ).first()
    return int(row[0]) if row else 0


_RESERVE_SQL = text(
    """
    INSERT INTO usage_daily (user_id, day, pages)
    VALUES (:uid, :day, :n)
    ON CONFLICT (user_id, day) DO UPDATE
        SET pages = usage_daily.pages + EXCLUDED.pages
        WHERE usage_daily.pages + EXCLUDED.pages <= :limit
    RETURNING pages
    """
)

_RELEASE_SQL = text(
    """
    UPDATE usage_daily SET pages = GREATEST(pages - :n, 0)
    WHERE user_id = :uid AND day = :day
    """
)


def reserve(
    engine: Engine, user_id: int, pages: int, limit: int, plan: str, day: date | None = None
) -> int:
    """Atomically add `pages` to today's counter iff the total stays <= limit.

    Returns the new total. Raises QuotaExceeded otherwise.
    """
    day = day or today()
    # The WHERE guard only runs on the conflict (UPDATE) path; the very first insert
    # of the day bypasses it, so guard that case explicitly. Inputs-only => no race.
    if pages > limit:
        raise QuotaExceeded("daily_pages_exceeded", limit, used_today(engine, user_id, day), plan)
    with engine.begin() as conn:
        row = conn.execute(
            _RESERVE_SQL, {"uid": user_id, "day": day, "n": pages, "limit": limit}
        ).first()
    if row is None:  # DO UPDATE ... WHERE was false -> nothing returned
        raise QuotaExceeded("daily_pages_exceeded", limit, used_today(engine, user_id, day), plan)
    return int(row[0])


def release(engine: Engine, user_id: int, pages: int, day: date | None = None) -> None:
    """Give pages back (e.g. the task could not be queued). Floors at 0."""
    day = day or today()
    with engine.begin() as conn:
        conn.execute(_RELEASE_SQL, {"uid": user_id, "day": day, "n": pages})


def record_attempt(
    engine: Engine,
    user_id: int,
    *,
    pages: int,
    outcome: str,
    plan: str,
    total_pages: int | None = None,
    start_page: int | None = None,
    end_page: int | None = None,
) -> None:
    """Persist one /convert decision.

    Best-effort on purpose: this is instrumentation, and a bookkeeping outage must
    not turn a conversion the user is entitled to into a 500. The failure is logged
    (and would show up as a gap in the table) rather than propagated.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                conversion_attempts.insert().values(
                    user_id=user_id,
                    pages=pages,
                    total_pages=total_pages,
                    start_page=start_page,
                    end_page=end_page,
                    outcome=outcome,
                    plan=plan,
                )
            )
    except Exception as e:  # noqa: BLE001
        logger.error(
            "Could not record conversion attempt (user=%s outcome=%s pages=%s): %s",
            user_id, outcome, pages, e,
        )
