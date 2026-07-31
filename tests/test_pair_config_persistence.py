"""Phase 1 multi-pair: per-CAT pair profile persistence.

Verifies that switching A → B → A restores A's economics, and that
process-global keys (XCH_RESERVE, LOOP_SECONDS, DRY_RUN) are not swapped.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import database as _db
    import api_server
    import pair_store

    _SKIP = None
except (ModuleNotFoundError, ImportError) as exc:
    _db = None
    api_server = None
    pair_store = None
    _SKIP = str(exc)


_LOOPBACK = {"REMOTE_ADDR": "127.0.0.1"}
_ASSET_A = "a" * 64
_ASSET_B = "b" * 64


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestPairConfigPersistence(unittest.TestCase):
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

        api_server.app.testing = True
        self.client = api_server.app.test_client()
        self.token = api_server._LOCAL_API_TOKEN
        api_server._rate_limit_log.clear()
        api_server._fresh_start_clear()

        self._orig_active_cat = dict(api_server._active_cat)
        self._cfg = api_server.cfg
        self._orig_asset = getattr(self._cfg, "CAT_ASSET_ID", None)
        self._orig_loop = getattr(self._cfg, "LOOP_SECONDS", None)
        self._orig_reserve = getattr(self._cfg, "XCH_RESERVE", None)
        self._orig_dry = getattr(self._cfg, "DRY_RUN", None)
        self._orig_spread = getattr(self._cfg, "BASE_SPREAD_BPS", None)
        self._orig_mode = getattr(self._cfg, "LIQUIDITY_MODE", None)
        self._orig_cat_reserve = getattr(self._cfg, "CAT_RESERVE", None)

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
        api_server._rate_limit_log.clear()
        api_server._fresh_start_clear()
        api_server._active_cat.clear()
        api_server._active_cat.update(self._orig_active_cat)

        # Best-effort restore of mutated cfg attrs for other tests.
        for key, value in (
            ("CAT_ASSET_ID", self._orig_asset),
            ("LOOP_SECONDS", self._orig_loop),
            ("XCH_RESERVE", self._orig_reserve),
            ("DRY_RUN", self._orig_dry),
            ("BASE_SPREAD_BPS", self._orig_spread),
            ("LIQUIDITY_MODE", self._orig_mode),
            ("CAT_RESERVE", self._orig_cat_reserve),
        ):
            if value is not None and hasattr(self._cfg, key):
                try:
                    setattr(self._cfg, key, value)
                except Exception:
                    pass

    def _switch(self, asset_id, name="TestCAT", ticker="TST", decimals=3, wallet_id=2):
        bot = MagicMock()
        bot.is_running.return_value = False
        bot.risk_manager = MagicMock()
        with (
            patch.object(api_server, "bot", bot),
            patch("wallet.get_wallets", return_value={"success": True, "wallets": []}),
            patch("wallet_sage.notify_cat_asset_id_changed", create=True),
            patch("cat_resolver.resolve_and_apply", return_value={}),
            patch("api_server.threading") as mock_threading,
        ):
            mock_threading.Thread.return_value = MagicMock()
            resp = self.client.post(
                "/api/cat/select",
                json={
                    "asset_id": asset_id,
                    "wallet_id": wallet_id,
                    "name": name,
                    "ticker_id": ticker,
                    "decimals": decimals,
                },
                headers={"X-Bot-Local-Token": self.token},
                environ_base=_LOOPBACK,
            )
        return resp

    def test_pair_store_roundtrip(self):
        overlay = {
            "BASE_SPREAD_BPS": "1234",
            "LIQUIDITY_MODE": "buy_only",
            "CAT_RESERVE": "42",
            "XCH_RESERVE": "9.9",  # must be ignored on save/apply
        }
        self.assertTrue(pair_store.save_pair_overlay(_ASSET_A, overlay))
        row = pair_store.get_pair_config(_ASSET_A)
        self.assertIsNotNone(row)
        self.assertEqual(row["config"]["BASE_SPREAD_BPS"], "1234")
        self.assertNotIn("XCH_RESERVE", row["config"])

    def _clear_pair_focus(self):
        """Start from a blank focus so outgoing-save does not invent profiles."""
        api_server._active_cat.update(
            {
                "asset_id": None,
                "name": None,
                "decimals": 3,
                "ticker_id": None,
                "wallet_id": None,
            }
        )
        try:
            self._cfg.CAT_ASSET_ID = ""
        except Exception:
            pass

    def test_switch_a_b_a_restores_economics(self):
        self._clear_pair_focus()

        # Focus A and seed distinctive economics into cfg + pair profile.
        resp = self._switch(_ASSET_A, name="Alpha", ticker="AAA")
        self.assertEqual(resp.status_code, 200, resp.get_json())
        self.assertFalse(resp.get_json().get("pair_profile_loaded"))

        self._cfg.update("BASE_SPREAD_BPS", "1111", source="test")
        self._cfg.update("LIQUIDITY_MODE", "buy_only", source="test")
        self._cfg.update("CAT_RESERVE", "11", source="test")
        self._cfg.update("XCH_RESERVE", "0.55", source="test")
        self._cfg.update("LOOP_SECONDS", "77", source="test")
        self._cfg.update("DRY_RUN", "true", source="test")
        pair_store.persist_current_pair_overlay(self._cfg)

        # Switch to B (first visit — no saved economics yet).
        resp = self._switch(_ASSET_B, name="Beta", ticker="BBB")
        self.assertEqual(resp.status_code, 200, resp.get_json())
        body = resp.get_json()
        self.assertFalse(body.get("pair_profile_loaded"))

        self._cfg.update("BASE_SPREAD_BPS", "2222", source="test")
        self._cfg.update("LIQUIDITY_MODE", "sell_only", source="test")
        self._cfg.update("CAT_RESERVE", "22", source="test")
        pair_store.persist_current_pair_overlay(self._cfg)

        # Globals should still be whatever we set (not pair-swapped).
        global_reserve = Decimal(str(self._cfg.XCH_RESERVE))
        global_loop = int(self._cfg.LOOP_SECONDS)
        global_dry = bool(self._cfg.DRY_RUN)

        # Switch back to A — profile should restore A's pair economics.
        resp = self._switch(_ASSET_A, name="Alpha", ticker="AAA")
        self.assertEqual(resp.status_code, 200, resp.get_json())
        body = resp.get_json()
        self.assertTrue(body.get("pair_profile_loaded"))

        self.assertEqual(Decimal(str(self._cfg.BASE_SPREAD_BPS)), Decimal("1111"))
        self.assertEqual(str(self._cfg.LIQUIDITY_MODE).lower(), "buy_only")
        self.assertEqual(Decimal(str(self._cfg.CAT_RESERVE)), Decimal("11"))

        # Process-global keys must not be restored from the pair overlay.
        self.assertEqual(Decimal(str(self._cfg.XCH_RESERVE)), global_reserve)
        self.assertEqual(int(self._cfg.LOOP_SECONDS), global_loop)
        self.assertEqual(bool(self._cfg.DRY_RUN), global_dry)

    def test_first_visit_does_not_invent_other_pair_economics(self):
        self._clear_pair_focus()
        resp = self._switch(_ASSET_A, name="Alpha", ticker="AAA")
        self.assertEqual(resp.status_code, 200)
        self._cfg.update("BASE_SPREAD_BPS", "3333", source="test")
        pair_store.persist_current_pair_overlay(self._cfg)

        resp = self._switch(_ASSET_B, name="Beta", ticker="BBB")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertFalse(body.get("pair_profile_loaded"))
        # B has no saved overlay; select must not claim a profile load.
        row = pair_store.get_pair_config(_ASSET_B)
        # Identity row may exist, but economics should be empty.
        if row is not None:
            self.assertFalse(row.get("config"))


if __name__ == "__main__":
    unittest.main()
