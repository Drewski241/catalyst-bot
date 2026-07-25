"""Shared coin-prep queue: fair per-pair scheduling + XCH ownership helpers."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import database as _db
    import prep_queue
    import api_server
    from blueprints import coin_prep as coin_prep_bp

    _SKIP = None
except (ModuleNotFoundError, ImportError) as exc:
    _db = None
    prep_queue = None
    api_server = None
    coin_prep_bp = None
    _SKIP = str(exc)


_ASSET_A = "a" * 64
_ASSET_B = "b" * 64
_ASSET_C = "c" * 64
_LOOPBACK = {"REMOTE_ADDR": "127.0.0.1"}


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestPrepQueueFairness(unittest.TestCase):
    def setUp(self):
        prep_queue._QUEUE = None
        self.q = prep_queue.get_prep_queue()

    def tearDown(self):
        prep_queue._QUEUE = None

    def test_try_start_when_idle(self):
        result = self.q.try_start({"asset_id": _ASSET_A, "coin_multiplier": 1.5})
        self.assertEqual(result["status"], "started")
        self.assertEqual(self.q.current_asset_id(), _ASSET_A)

    def test_same_asset_while_running_is_already_running(self):
        self.q.try_start({"asset_id": _ASSET_A})
        result = self.q.try_start({"asset_id": _ASSET_A})
        self.assertEqual(result["status"], "already_running")

    def test_other_asset_is_queued(self):
        self.q.try_start({"asset_id": _ASSET_A})
        result = self.q.try_start({"asset_id": _ASSET_B, "coin_multiplier": 2.0})
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["position"], 1)
        self.assertEqual(self.q.queued_assets(), [_ASSET_B])

    def test_fair_order_skips_last_served_when_others_wait(self):
        self.q.try_start({"asset_id": _ASSET_A})
        self.q.enqueue({"asset_id": _ASSET_B})
        # Queue A again for a follow-up run while A is still current.
        self.q.enqueue({"asset_id": _ASSET_A})
        nxt = self.q.complete_current()
        # A just finished and is waiting again, but B was already waiting —
        # serve B first (fair skip).
        self.assertEqual(nxt["asset_id"], _ASSET_B)
        nxt2 = self.q.complete_current()
        self.assertEqual(nxt2["asset_id"], _ASSET_A)

    def test_coalesce_updates_pending_params(self):
        self.q.try_start({"asset_id": _ASSET_A})
        self.q.enqueue({"asset_id": _ASSET_B, "coin_multiplier": 1.0})
        self.q.enqueue({"asset_id": _ASSET_B, "coin_multiplier": 2.5})
        self.assertEqual(len(self.q.queued_assets()), 1)
        nxt = self.q.complete_current()
        self.assertEqual(nxt["coin_multiplier"], 2.5)

    def test_cancel_clears_queued(self):
        self.q.try_start({"asset_id": _ASSET_A})
        self.q.enqueue({"asset_id": _ASSET_B})
        result = self.q.cancel(asset_id=_ASSET_B)
        self.assertEqual(len(result["cancelled_queued"]), 1)
        self.assertEqual(self.q.queued_assets(), [])


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestXchOwnership(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self._tmp_path = self._tmp.name
        self._orig_db_path = _db.DB_PATH
        _db.DB_PATH = self._tmp_path
        self._orig_init_path = _db._db_initialized_path
        _db._db_initialized_path = ""
        if hasattr(_db._local, "conn") and _db._local.conn:
            try:
                _db._local.conn.close()
            except Exception:
                pass
        _db._local.conn = None
        _db.init_database()

    def tearDown(self):
        if hasattr(_db._local, "conn") and _db._local.conn:
            try:
                _db._local.conn.close()
            except Exception:
                pass
        _db._local.conn = None
        _db.DB_PATH = self._orig_db_path
        _db._db_initialized_path = self._orig_init_path
        try:
            os.unlink(self._tmp_path)
        except Exception:
            pass

    def test_assign_and_filter_free_xch(self):
        _db.upsert_coin("coin-a", "xch", 1_000_000_000_000, asset_id="xch")
        _db.upsert_coin("coin-b", "xch", 2_000_000_000_000, asset_id="xch")
        tagged = _db.assign_xch_owner_to_free_coins(_ASSET_A)
        self.assertEqual(tagged, 2)

        # Insert an unowned coin after tagging
        _db.upsert_coin("coin-c", "xch", 3_000_000_000_000, asset_id="xch")

        def _ids(rows):
            return {_db.norm_coin_id(c["coin_id"]) for c in rows}

        # Pair A sees owned + unowned
        free_a = _db.get_free_coins("xch", owner_asset_id=_ASSET_A)
        self.assertEqual(
            _ids(free_a),
            {_db.norm_coin_id(x) for x in ("coin-a", "coin-b", "coin-c")},
        )

        # Pair B only sees unowned (not A's coins)
        free_b = _db.get_free_coins("xch", owner_asset_id=_ASSET_B)
        self.assertEqual(_ids(free_b), {_db.norm_coin_id("coin-c")})

    def test_scoped_reset_preserves_other_pair_cat_coins(self):
        _db.upsert_coin("cat-a", "cat", 1000, asset_id=_ASSET_A)
        _db.upsert_coin("cat-b", "cat", 2000, asset_id=_ASSET_B)
        _db.upsert_coin("xch-unowned", "xch", 1_000_000_000_000, asset_id="xch")
        summary = api_server._reset_fresh_run_session(
            clear_coins=True,
            cancel_open_offers=True,
            preserve_history=True,
            cat_asset_id=_ASSET_A,
            reason="test",
        )
        self.assertGreaterEqual(summary["coins_cleared"], 1)
        remaining = _db.get_connection().execute(
            "SELECT coin_id FROM coins ORDER BY coin_id"
        ).fetchall()
        ids = {_db.norm_coin_id(r["coin_id"]) for r in remaining}
        self.assertIn(_db.norm_coin_id("cat-b"), ids)
        self.assertNotIn(_db.norm_coin_id("cat-a"), ids)


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestPrepTriggerQueueApi(unittest.TestCase):
    _FAKE_SUMMARY = {
        "fills_cleared": 0,
        "round_trips_cleared": 0,
        "price_history_cleared": False,
        "inventory_cleared": False,
        "coins_cleared": 0,
        "open_offers_cancelled": 0,
        "reset_at": "2026-01-01T00:00:00",
        "preserve_history": True,
    }

    def setUp(self):
        api_server.app.testing = True
        self.client = api_server.app.test_client()
        self.token = api_server._LOCAL_API_TOKEN
        self.auth = {"X-Bot-Local-Token": self.token}
        api_server._rate_limit_log.clear()
        api_server._coin_prep_state["running"] = False
        api_server._coin_prep_state["complete"] = False
        api_server._coin_prep_state["error"] = None
        api_server._coin_prep_state["phase"] = "idle"
        api_server._coin_prep_state["asset_id"] = None
        api_server._coin_prep_proc = None
        prep_queue._QUEUE = None

    def tearDown(self):
        prep_queue._QUEUE = None
        api_server._coin_prep_state["running"] = False
        api_server._coin_prep_proc = None

    def _post(self, body):
        return self.client.post(
            "/api/coin-prep/trigger",
            json=body,
            headers=self.auth,
            environ_base=_LOOPBACK,
        )

    def test_second_pair_is_queued_while_first_runs(self):
        with (
            patch("threading.Thread") as mock_thread,
            patch.object(
                api_server, "_reset_fresh_run_session", return_value=self._FAKE_SUMMARY
            ),
            patch.object(api_server, "bot", None),
            patch.object(coin_prep_bp.cfg, "CAT_ASSET_ID", _ASSET_A),
        ):
            mock_thread.return_value.start = lambda: None
            first = self._post({"asset_id": _ASSET_A, "coin_multiplier": 1})
            second = self._post({"asset_id": _ASSET_B, "coin_multiplier": 1})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.get_json().get("status"), "started")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json().get("status"), "queued")
        self.assertEqual(second.get_json().get("position"), 1)

    def test_same_pair_duplicate_still_already_running(self):
        with (
            patch("threading.Thread") as mock_thread,
            patch.object(
                api_server, "_reset_fresh_run_session", return_value=self._FAKE_SUMMARY
            ),
            patch.object(api_server, "bot", None),
        ):
            mock_thread.return_value.start = lambda: None
            first = self._post({"asset_id": _ASSET_A})
            second = self._post({"asset_id": _ASSET_A})
        self.assertEqual(first.get_json().get("status"), "started")
        self.assertEqual(second.get_json().get("status"), "already_running")


if __name__ == "__main__":
    unittest.main()
