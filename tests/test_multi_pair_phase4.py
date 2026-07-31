"""Phase 4 multi-pair: allocation-aware Smart Settings, portfolio cap, SSE tags."""

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

    _SKIP = None
except (ModuleNotFoundError, ImportError) as exc:
    _db = None
    api_server = None
    pair_store = None
    pair_context = None
    shared_xch_ledger = None
    _SKIP = str(exc)


_ASSET_A = "a" * 64
_ASSET_B = "b" * 64


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestSharedAllocHelpers(unittest.TestCase):
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

    def test_remaining_allocatable_excludes_focus_budget(self):
        cfg = MagicMock()
        cfg.XCH_RESERVE = Decimal("0.1")
        cfg.FEE_PREP_COUNT = 0
        cfg.FEE_COIN_SIZE_XCH = Decimal("0")
        cfg.PORTFOLIO_MAX_XCH_EXPOSURE = Decimal("0")
        ledger = shared_xch_ledger.ledger
        pair_store.set_xch_budget_mojos(_ASSET_A, 1_000_000_000_000)  # 1 XCH
        pair_store.set_xch_budget_mojos(_ASSET_B, 500_000_000_000)  # 0.5 XCH
        with patch.object(ledger, "spendable_xch_mojos", return_value=3_000_000_000_000):
            # 3 spendable - 0.1 reserve - 0.01 default fee buffer = 2.89
            # exclude A → 2.89 - 0.5 (B's budget) = 2.39
            remain = ledger.remaining_allocatable_mojos(_ASSET_A, cfg=cfg)
            self.assertEqual(remain, 2_390_000_000_000)

    def test_remaining_allocatable_clamps_to_reshapeable_inventory(self):
        cfg = MagicMock()
        cfg.XCH_RESERVE = Decimal("0")
        cfg.FEE_PREP_COUNT = 0
        cfg.FEE_COIN_SIZE_XCH = Decimal("0")
        cfg.PORTFOLIO_MAX_XCH_EXPOSURE = Decimal("0")
        ledger = shared_xch_ledger.ledger
        pair_store.set_xch_budget_mojos(_ASSET_A, 0)
        # Pair A owns 2 XCH trading; 0.5 XCH is still unowned/reshapeable for B.
        _db.upsert_coin(
            "owned-a",
            "xch",
            2_000_000_000_000,
            designation="tier_spare",
            assigned_tier="inner",
        )
        _db.upsert_coin(
            "free-trade",
            "xch",
            500_000_000_000,
            designation="tier_spare",
            assigned_tier="mid",
        )
        _db.upsert_coin(
            "fee-shared",
            "xch",
            50_000_000,
            designation="tier_spare",
            assigned_tier="fees",
        )
        _db.claim_xch_ownership_for_pair(_ASSET_A, max_mojos=2_000_000_000_000)
        with patch.object(ledger, "spendable_xch_mojos", return_value=5_000_000_000_000):
            remain = ledger.remaining_allocatable_mojos(_ASSET_B, cfg=cfg)
        self.assertEqual(remain, 500_000_000_000)
        self.assertEqual(_db.sum_reshapeable_xch_mojos(_ASSET_B), 500_000_000_000)

    def test_start_fresh_clears_ownership_and_budgets(self):
        """Start Fresh must free reshapeable XCH for a second-pair reallocation."""
        pair_store.set_xch_budget_mojos(_ASSET_A, 2_000_000_000_000)
        pair_store.set_xch_budget_mojos(_ASSET_B, 500_000_000_000)
        _db.upsert_coin(
            "owned-fresh-a",
            "xch",
            1_000_000_000_000,
            designation="tier_spare",
            assigned_tier="inner",
        )
        _db.claim_xch_ownership_for_pair(_ASSET_A, max_mojos=1_000_000_000_000)
        self.assertGreater(_db.summarize_xch_ownership()["total_owned_coins"], 0)

        own = _db.clear_all_xch_trading_ownership()
        budgets = pair_store.clear_all_xch_budgets()
        self.assertGreaterEqual(own.get("cleared_coins", 0), 1)
        self.assertGreaterEqual(budgets.get("pairs_cleared", 0), 1)
        self.assertEqual(_db.summarize_xch_ownership()["total_owned_coins"], 0)
        self.assertEqual(pair_store.get_xch_budget_mojos(_ASSET_A), 0)
        self.assertEqual(pair_store.get_xch_budget_mojos(_ASSET_B), 0)

    def test_portfolio_cap_blocks_over_exposure(self):
        cfg = MagicMock()
        cfg.PORTFOLIO_MAX_XCH_EXPOSURE = Decimal("1.0")
        ledger = shared_xch_ledger.ledger
        pair_store.set_xch_budget_mojos(_ASSET_A, 2_000_000_000_000)
        _db.add_offer(
            trade_id="buy-a-port",
            side="buy",
            price_xch=Decimal("0.01"),
            size_xch=Decimal("0.8"),
            size_cat=Decimal("80"),
            cat_asset_id=_ASSET_A,
        )
        ok, reason = ledger.can_spend_portfolio(300_000_000_000, cfg=cfg)
        self.assertFalse(ok)
        self.assertIn("portfolio", reason.lower())
        ok, _ = ledger.can_spend_portfolio(100_000_000_000, cfg=cfg)
        self.assertTrue(ok)

    def test_portfolio_cap_disabled_when_zero(self):
        cfg = MagicMock()
        cfg.PORTFOLIO_MAX_XCH_EXPOSURE = Decimal("0")
        ledger = shared_xch_ledger.ledger
        ok, _ = ledger.can_spend_portfolio(10_000_000_000_000, cfg=cfg)
        self.assertTrue(ok)


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestSmartDefaultsSharedClamp(unittest.TestCase):
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
        pair_store.set_xch_budget_mojos(_ASSET_A, 1_500_000_000_000)  # 1.5 XCH

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

    def test_shared_clamp_reduces_available_for_second_pair(self):
        """Exercise the shared-allocation clamp without full market APIs."""
        cfg = MagicMock()
        cfg.XCH_RESERVE = Decimal("0.1")
        cfg.FEE_PREP_COUNT = 0
        cfg.FEE_COIN_SIZE_XCH = Decimal("0")
        cfg.CAT_ASSET_ID = _ASSET_B
        ledger = shared_xch_ledger.ledger

        # Simulate the Smart Settings clamp block.
        xch_spendable = 3.0
        xch_reserve = 0.1
        avail = max(0.0, xch_spendable - xch_reserve)
        with patch.object(ledger, "spendable_xch_mojos", return_value=3_000_000_000_000):
            remaining = ledger.remaining_allocatable_mojos(_ASSET_B, cfg=cfg)
            shared_avail = float(ledger.mojos_to_xch(remaining))
        self.assertLess(shared_avail, avail)
        # Other pair holds 1.5; allocatable ≈ 2.89 (after 0.01 fee buffer)
        # → remaining ≈ 1.39
        self.assertAlmostEqual(shared_avail, 1.39, places=3)
        clamped = min(avail, shared_avail)
        self.assertAlmostEqual(clamped, 1.39, places=3)


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestPairContextWatchersAndSse(unittest.TestCase):
    def test_pair_context_resolves_cfg_for_watcher_style_block(self):
        pair_context.install_config_overlay_hook()
        cfg = api_server.cfg
        snap = pair_context.PairSnapshot(
            asset_id=_ASSET_B,
            wallet_id=7,
            name="Beta",
            ticker_id="BBB",
            decimals=3,
        )
        with pair_context.pair_context(snap):
            self.assertEqual(str(cfg.CAT_ASSET_ID).lower().replace("0x", ""), _ASSET_B)
            self.assertEqual(int(cfg.CAT_WALLET_ID), 7)

    def test_emit_stamps_asset_id(self):
        from bot_loop import BotLoop

        bus = MagicMock()
        bot = BotLoop.__new__(BotLoop)
        bot._event_bus = bus
        bot._pair_asset_id = _ASSET_A
        bot._pair_snapshot = pair_context.PairSnapshot(
            asset_id=_ASSET_A, name="Alpha", ticker_id="AAA"
        )
        bot._emit("dashboard_update", {"mid_price": 1.23})
        bus.emit.assert_called_once()
        event_type, payload = bus.emit.call_args[0]
        self.assertEqual(event_type, "dashboard_update")
        self.assertEqual(payload.get("asset_id"), _ASSET_A)
        self.assertEqual(payload.get("mid_price"), 1.23)

    def test_emit_alert_namespaces_id(self):
        from bot_loop import BotLoop

        bus = MagicMock()
        bot = BotLoop.__new__(BotLoop)
        bot._event_bus = bus
        bot._pair_asset_id = _ASSET_A
        bot._pair_snapshot = pair_context.PairSnapshot(
            asset_id=_ASSET_A, name="Alpha", ticker_id="AAA"
        )
        bot._emit_alert("position_limit", "warning", "Too big", "details")
        bus.alert.assert_called_once()
        args, kwargs = bus.alert.call_args
        self.assertEqual(args[0], f"{_ASSET_A}:position_limit")
        self.assertIn("[AAA]", args[2])
        self.assertEqual(kwargs.get("asset_id"), _ASSET_A)


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestAlertStoreAssetFields(unittest.TestCase):
    def test_set_alert_stores_asset_id(self):
        store = api_server.AlertStore()
        store.set_alert(
            f"{_ASSET_A}:test",
            "info",
            "Title",
            "Msg",
            asset_id=_ASSET_A,
            pair_ticker="AAA",
        )
        active = store.get_active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].get("asset_id"), _ASSET_A)
        self.assertEqual(active[0].get("pair_ticker"), "AAA")


if __name__ == "__main__":
    unittest.main()
