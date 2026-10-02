from datetime import date, timedelta

import pytest

from app.core import lifecycle as lc
from app.services.notifications import threshold_for

REF = date(2026, 1, 1)


@pytest.mark.parametrize(
    "offset,expected",
    [
        (-10, lc.EXPIRE),
        (0, lc.EXPIRE),
        (1, lc.CRITIQUE),
        (30, lc.CRITIQUE),
        (31, lc.ALERTE),
        (90, lc.ALERTE),
        (91, lc.OK),
        (400, lc.OK),
    ],
)
def test_status(offset, expected):
    end = REF + timedelta(days=offset)
    assert lc.days_remaining(end, REF) == offset
    assert lc.compute_status(end, REF) == expected


def test_no_date_is_unknown():
    assert lc.compute_status(None) == lc.INCONNU
    assert lc.days_remaining(None) is None


def test_status_ranges_are_consistent():
    for status in (lc.EXPIRE, lc.CRITIQUE, lc.ALERTE, lc.OK):
        lo, hi = lc.status_date_range(status, REF)
        for bound in (lo, hi):
            if bound is not None:
                assert lc.compute_status(bound, REF) == status


def test_renewal_start_date():
    assert lc.renewal_start_date(date(2026, 12, 31), 90) == date(2026, 10, 2)
    assert lc.renewal_start_date(date(2026, 12, 31), None) == date(2026, 12, 31)


@pytest.mark.parametrize(
    "days,expected", [(120, None), (90, 90), (61, 90), (45, 60), (30, 30), (10, 30), (7, 7), (1, 7), (0, 0), (-3, 0)]
)
def test_alert_thresholds(days, expected):
    assert threshold_for(days, [90, 60, 30, 7]) == expected
