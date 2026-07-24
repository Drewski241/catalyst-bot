"""Phase 3 multi-pair: XCH ledger, pair registry gates, context overlay."""

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
    import pair_context
    import shared_xch_ledger
    import pair_registry

    _SKIP = None
except (ModuleNotFoundError, ImportError) as exc:
    _db = None
    api_server = None
    pair_store = None
    pair_context = None
    shared_xch_ledger = None
    pair_registry = None
    _SKIP = str(exc)


_LOOPBACK = {"REMOTE_ADDR": "127.0.0.1"}
_ASSET_A = "a" * 64
_ASSET_B = "b" * 64


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestSharedXchLedger(unittest.TestCase):
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

    def test_budget_roundtrip(self):
        self.assertTrue(pair_store.set_xch_budget_mojos(_ASSET_A, 1_500_000_000_000))
        self.assertEqual(pair_store.get_xch_budget_mojos(_ASSET_A), 1_500_000_000_000)

    def test_can_spend_buy_respects_remaining(self):
        pair_store.set_xch_budget_mojos(_ASSET_A, 1_000_000_000_000)  # 1 XCH
        _db.add_offer(
            trade_id="buy-a-1",
            side="buy",
            price_xch=Decimal("0.01"),
            size_xch=Decimal("0.6"),
            size_cat=Decimal("60"),
            cat_asset_id=_ASSET_A,
        )
        ledger = shared_xch_ledger.ledger
        ok, _ = ledger.can_spend_buy(_ASSET_A, 300_000_000_000)  # 0.3 XCH
        self.assertTrue(ok)
        ok, reason = ledger.can_spend_buy(_ASSET_A, 500_000_000_000)  # 0.5 XCH
        self.assertFalse(ok)
        self.assertIn("budget", reason.lower())

    def test_can_allocate_rejects_oversubscription(self):
        cfg = MagicMock()
        cfg.XCH_RESERVE = Decimal("0.1")
        cfg.FEE_PREP_COUNT = 0
        cfg.FEE_COIN_SIZE_XCH = Decimal("0")
        ledger = shared_xch_ledger.ledger
        with patch.object(ledger, "spendable_xch_mojos", return_value=2_000_000_000_000):
            # 2 XCH spendable, 0.1 reserve → ~1.9 allocatable
            ok, _ = ledger.can_allocate(
                _ASSET_A, 1_000_000_000_000, cfg=cfg, running_asset_ids=[]
            )
            self.assertTrue(ok)
            # Second pair wants 1.5 while first would take 1.0 → oversubscribe
            ok, reason = ledger.can_allocate(
                _ASSET_B,
                1_500_000_000_000,
                cfg=cfg,
                running_asset_ids=[_ASSET_A],
            )
            # running A has budget 0 unless set — set it
            pair_store.set_xch_budget_mojos(_ASSET_A, 1_000_000_000_000)
            ok, reason = ledger.can_allocate(
                _ASSET_B,
                1_500_000_000_000,
                cfg=cfg,
                running_asset_ids=[_ASSET_A],
            )
            self.assertFalse(ok)


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestPairContextOverlay(unittest.TestCase):
    def test_overlay_swaps_identity(self):
        pair_context.install_config_overlay_hook()
        cfg = api_server.cfg
        snap = pair_context.PairSnapshot(
            asset_id=_ASSET_B,
            wallet_id=9,
            name="Beta",
            ticker_id="BBB",
            decimals=4,
            overlay={"BASE_SPREAD_BPS": "2222"},
        )
        with pair_context.pair_context(snap):
            self.assertEqual(str(cfg.CAT_ASSET_ID).lower().replace("0x", ""), _ASSET_B)
            self.assertEqual(int(cfg.CAT_WALLET_ID), 9)
            self.assertEqual(Decimal(str(cfg.BASE_SPREAD_BPS)), Decimal("2222"))


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestPairRegistryAndApi(unittest.TestCase):
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
        # Reset registry singleton between tests.
        pair_registry._REGISTRY = None

    def tearDown(self):
        pair_registry._REGISTRY = None
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

    def test_start_requires_budget(self):
        registry = pair_registry.get_registry()
        result = registry.start_pair(_ASSET_A, cfg=api_server.cfg)
        self.assertFalse(result.get("success"))
        self.assertIn("budget", (result.get("error") or "").lower())

    def test_api_set_budget_and_start_stop(self):
        # Set budget via API
        with patch(
            "shared_xch_ledger.ledger.spendable_xch_mojos",
            return_value=10_000_000_000_000,
        ):
            resp = self.client.patch(
                f"/api/pairs/{_ASSET_A}/budget",
                json={"xch_budget": 1.25},
                headers={"X-Bot-Local-Token": self.token},
                environ_base=_LOOPBACK,
            )
        self.assertEqual(resp.status_code, 200, resp.get_json())
        self.assertTrue(resp.get_json().get("success"))
        self.assertEqual(pair_store.get_xch_budget_mojos(_ASSET_A), 1_250_000_000_000)

        # Start via registry with mocked BotLoop.start
        fake_bot = MagicMock()
        fake_bot.is_running.return_value = False
        fake_bot.start.return_value = True
        fake_bot.stop.return_value = True
        fake_bot.coin_manager = MagicMock()
        fake_bot.coin_manager.fee_pool = MagicMock()
        fake_bot.offer_manager = MagicMock()

        registry = pair_registry.get_registry()
        with (
            patch("bot_loop.BotLoop", return_value=fake_bot),
            patch(
                "shared_xch_ledger.ledger.spendable_xch_mojos",
                return_value=10_000_000_000_000,
            ),
            patch("wallet_sage.notify_cat_asset_id_changed"),
        ):
            # After start(), is_running should report True
            def _start():
                fake_bot.is_running.return_value = True
                return True

            fake_bot.start.side_effect = _start
            result = registry.start_pair(_ASSET_A, cfg=api_server.cfg)
            self.assertTrue(result.get("success"), result)
            self.assertTrue(registry.is_running(_ASSET_A))

            def _stop():
                fake_bot.is_running.return_value = False
                return True

            fake_bot.stop.side_effect = _stop
            stop = registry.stop_pair(_ASSET_A)
            self.assertTrue(stop.get("success"), stop)
            self.assertFalse(registry.is_running(_ASSET_A))

    def test_max_four_concurrent(self):
        registry = pair_registry.get_registry()
        assets = [("c" * 63 + str(i)) for i in range(5)]
        # Normalize to valid hex — use a000... style
        assets = [f"{i:064x}" for i in range(1, 6)]
        for aid in assets:
            pair_store.set_xch_budget_mojos(aid, 100_000_000_000)  # 0.1 XCH

        fake_bot = MagicMock()
        fake_bot.coin_manager = MagicMock()
        fake_bot.coin_manager.fee_pool = MagicMock()
        fake_bot.offer_manager = MagicMock()
        running = set()

        def _make_bot():
            bot = MagicMock()
            bot.coin_manager = MagicMock()
            bot.coin_manager.fee_pool = MagicMock()
            bot.offer_manager = MagicMock()
            bot._asset = None

            def start():
                running.add(id(bot))
                bot.is_running.return_value = True
                return True

            def stop():
                running.discard(id(bot))
                bot.is_running.return_value = False
                return True

            bot.start.side_effect = start
            bot.stop.side_effect = stop
            bot.is_running.return_value = False
            return bot

        with (
            patch("bot_loop.BotLoop", side_effect=_make_bot),
            patch(
                "shared_xch_ledger.ledger.spendable_xch_mojos",
                return_value=100_000_000_000_000,
            ),
            patch("wallet_sage.notify_cat_asset_id_changed"),
        ):
            for aid in assets[:4]:
                result = registry.start_pair(aid, cfg=api_server.cfg)
                self.assertTrue(result.get("success"), result)
            fifth = registry.start_pair(assets[4], cfg=api_server.cfg)
            self.assertFalse(fifth.get("success"))
            self.assertIn("max", (fifth.get("error") or "").lower())


if __name__ == "__main__":
    unittest.main()
