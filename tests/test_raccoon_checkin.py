import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import raccoon_daily as rc  # noqa: E402


CST = timezone(timedelta(hours=8))
NOW = datetime.fromisoformat("2026-11-10T12:00:00+08:00")


def grant(points=300, grant_at=None, created_at=None, expire_at=None, biz_type="daily_grant"):
    return {
        "biz_type": biz_type,
        "points": points,
        "grant_at": grant_at,
        "created_at": created_at,
        "expire_at": expire_at,
    }


class CheckinSemanticsTests(unittest.TestCase):
    def test_today_grant_prefers_largest_and_supports_grant_at_fallback(self):
        items = [
            grant(points=100, grant_at="2026-11-10T00:00:00+08:00"),
            grant(points=300, created_at="2026-11-10T00:01:00+08:00"),
            grant(points=999, grant_at="2026-11-09T00:00:00+08:00"),
        ]
        self.assertEqual(300, rc.pick_today_grant(items, NOW)["points"])

    def test_freshness_uses_created_at_and_90_second_window(self):
        fresh = grant(created_at=(NOW - timedelta(seconds=30)).isoformat(),
                      grant_at=NOW.isoformat())
        old = grant(created_at=(NOW - timedelta(seconds=120)).isoformat(),
                    grant_at=NOW.isoformat())
        result = rc.checkin_result([fresh], NOW.timestamp(), now=NOW)
        self.assertTrue(result["ok"])
        self.assertFalse(result["already_checked_in"])
        result = rc.checkin_result([old], NOW.timestamp(), now=NOW)
        self.assertTrue(result["ok"])
        self.assertTrue(result["already_checked_in"])

    def test_missing_created_at_is_success_but_not_fresh(self):
        item = grant(grant_at=NOW.isoformat(), expire_at="2026-11-11T23:59:59+08:00")
        result = rc.checkin_result([item], NOW.timestamp(), now=NOW)
        self.assertTrue(result["ok"])
        self.assertTrue(result["already_checked_in"])
        self.assertEqual(300.0, result["credit"])

    def test_active_grants_require_expiry_and_exclude_expired_or_consumed(self):
        items = [
            grant(grant_at="2026-11-04T00:00:00+08:00",
                  expire_at="2026-11-10T23:59:59+08:00"),
            grant(grant_at="2026-11-05T00:00:00+08:00",
                  expire_at="2026-11-11T23:59:59+08:00"),
            grant(grant_at="2026-11-01T00:00:00+08:00",
                  expire_at="2026-11-09T23:59:59+08:00"),
            grant(grant_at="2026-11-06T00:00:00+08:00"),
            grant(grant_at="2026-11-03T00:00:00+08:00",
                  expire_at="2026-11-12T23:59:59+08:00"),
            grant(points=-300, biz_type="daily_expire",
                  grant_at="2026-11-03T00:00:00+08:00"),
        ]
        active = rc.pick_active_grants(items, NOW)
        self.assertEqual([300, 300], [item["points"] for item in active])
        self.assertEqual("2026-11-10T23:59:59+08:00", active[0]["expire_at"])

    def test_daily_expire_pairing_uses_cst_date_and_absolute_points(self):
        base = grant(grant_at="2026-11-03T00:00:00+08:00",
                     expire_at="2026-11-12T23:59:59+08:00")
        unmatched = grant(grant_at="2026-11-04T00:00:00+08:00",
                          expire_at="2026-11-12T23:59:59+08:00")
        expire = grant(points=-300, biz_type="daily_expire",
                       grant_at="2026-11-03T00:00:00+08:00")
        active = rc.pick_active_grants([base, unmatched, expire], NOW)
        self.assertEqual([unmatched], active)

    def test_daily_expire_removes_all_grants_with_the_same_day_and_points(self):
        first = grant(grant_at="2026-11-03T00:00:00+08:00",
                      expire_at="2026-11-12T23:59:59+08:00")
        second = dict(first)
        expire = grant(points=-300, biz_type="daily_expire",
                       grant_at="2026-11-03T00:00:00+08:00")
        self.assertEqual([], rc.pick_active_grants([first, second, expire], NOW))

    def test_grace_boundaries(self):
        early = datetime.fromisoformat("2026-11-10T00:10:00+08:00")
        before = rc.checkin_result([], early.timestamp(), now=early)
        self.assertFalse(before["ok"])
        self.assertEqual(int(rc.grant_grace_at(early).timestamp()), before["retry_at"])
        active_item = grant(grant_at="2026-11-09T00:00:00+08:00",
                            expire_at="2026-11-12T23:59:59+08:00")
        active = rc.checkin_result([active_item], early.timestamp(), now=early)
        self.assertTrue(active["ok"])
        self.assertEqual(int(rc.grant_grace_at(early).timestamp()), active["seal_until"])
        at_grace = datetime.fromisoformat("2026-11-10T01:30:00+08:00")
        self.assertIsNone(rc.checkin_result([], at_grace.timestamp(), now=at_grace)["retry_at"])

    def test_bills_endpoint_covers_more_than_twenty_rows(self):
        self.assertIn("/points/v2/bills", rc.BILLS_PATH)
        self.assertIn("paging.limit=60", rc.BILLS_PATH)
        self.assertIn("type=all", rc.BILLS_PATH)


class CheckinFlowTests(unittest.TestCase):
    def account(self):
        return {"token": "token", "refresh": "refresh", "note": "test"}

    def test_checkin_order_is_visit_balance_bills(self):
        calls = []

        def fake_call(_account, fn):
            return fn(self.account())

        with mock.patch.object(rc, "QUERY_ONLY", False), \
                mock.patch.object(rc, "ONBOARDING", False), \
                mock.patch.object(rc, "call_with_auth", side_effect=fake_call), \
                mock.patch.object(rc, "visit_page", side_effect=lambda *_: calls.append("visit")), \
                mock.patch.object(rc, "account_balance", side_effect=lambda *_: calls.append("balance")), \
                mock.patch.object(rc, "bill_items", side_effect=lambda *_: calls.append("bills") or []), \
                mock.patch.object(rc, "checkin_result", return_value={
                    "ok": False, "message": "pending", "retry_at": None,
                }):
            ok, _message = rc.do_checkin(self.account())
        self.assertFalse(ok)
        self.assertEqual(["visit", "balance", "bills"], calls)

    def test_visit_failure_is_best_effort(self):
        with mock.patch.object(rc, "QUERY_ONLY", False), \
                mock.patch.object(rc, "ONBOARDING", False), \
                mock.patch.object(rc, "call_with_auth", side_effect=lambda _a, fn: fn(self.account())), \
                mock.patch.object(rc, "visit_page", side_effect=RuntimeError("visit failed")), \
                mock.patch.object(rc, "account_balance", return_value={"available_points": 300}), \
                mock.patch.object(rc, "bill_items", return_value=[]), \
                mock.patch.object(rc, "checkin_result", return_value={
                    "ok": True, "message": "available", "retry_at": None,
                }), \
                mock.patch.object(rc, "log"):
            ok, message = rc.do_checkin(self.account())
        self.assertTrue(ok)
        self.assertEqual("available", message)

    def test_query_only_skips_visit_and_balance(self):
        with mock.patch.object(rc, "QUERY_ONLY", True), \
                mock.patch.object(rc, "ONBOARDING", False), \
                mock.patch.object(rc, "call_with_auth", side_effect=lambda _a, fn: fn(self.account())), \
                mock.patch.object(rc, "visit_page") as visit, \
                mock.patch.object(rc, "account_balance") as balance, \
                mock.patch.object(rc, "bill_items", return_value=[]), \
                mock.patch.object(rc, "checkin_result", return_value={
                    "ok": False, "message": "pending", "retry_at": None,
                }):
            ok, _message = rc.do_checkin(self.account())
        self.assertFalse(ok)
        visit.assert_not_called()
        balance.assert_not_called()

    def test_balance_requires_numeric_available_points(self):
        class Response:
            status_code = 200

            def __init__(self, value):
                self.value = value

            def json(self):
                return {"code": 0, "data": {"available_points": self.value}}

        for value in (None, True, "300"):
            with self.subTest(value=value), \
                    mock.patch.object(rc, "request", return_value=Response(value)):
                with self.assertRaisesRegex(RuntimeError, "available_points"):
                    rc.account_balance("token", self.account())
        with mock.patch.object(rc, "request", return_value=Response(300)):
            self.assertEqual(300, rc.account_balance("token", self.account())["available_points"])

    def test_bills_require_items_list(self):
        class Response:
            status_code = 200

            def json(self):
                return {"code": 0, "data": {"items": {"bad": True}}}

        with mock.patch.object(rc, "request", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "items"):
                rc.bill_items("token", self.account())


if __name__ == "__main__":
    unittest.main()
