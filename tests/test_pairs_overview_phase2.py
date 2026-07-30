"""Phase 2 multi-pair: coins.asset_id schema + GET /api/pairs overview."""

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
class TestCoinsAssetIdSchema(unittest.TestCase):
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

    def test_upsert_coin_stores_asset_id(self):
        self.assertTrue(
            _db.upsert_coin(
                "0x" + ("11" * 32),
                "cat",
                1000,
                asset_id=_ASSET_A,
            )
        )
        rows = _db.get_free_coins("cat", asset_id=_ASSET_A)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["asset_id"], _ASSET_A)

    def test_get_free_coins_filters_by_asset(self):
        _db.upsert_coin("0x" + ("22" * 32), "cat", 100, asset_id=_ASSET_A)
        _db.upsert_coin("0x" + ("33" * 32), "cat", 200, asset_id=_ASSET_B)
        a_rows = _db.get_free_coins("cat", asset_id=_ASSET_A)
        b_rows = _db.get_free_coins("cat", asset_id=_ASSET_B)
        self.assertEqual(len(a_rows), 1)
        self.assertEqual(len(b_rows), 1)
        self.assertEqual(a_rows[0]["asset_id"], _ASSET_A)
        self.assertEqual(b_rows[0]["asset_id"], _ASSET_B)


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestCoinsAssetIdUpgradeFromLegacy(unittest.TestCase):
    """Older DBs have coins without asset_id; SCHEMA_SQL must not fail on them."""

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

        # Simulate a pre-multi-pair coins table (no asset_id / owner_asset_id).
        import sqlite3

        conn = sqlite3.connect(self._tmp_path)
        conn.executescript(
            """
            CREATE TABLE coins (
                coin_id         TEXT PRIMARY KEY,
                wallet_type     TEXT NOT NULL,
                amount_mojos    INTEGER NOT NULL,
                tier            TEXT,
                status          TEXT NOT NULL DEFAULT 'free',
                trade_id        TEXT,
                first_seen      TEXT NOT NULL,
                last_seen       TEXT NOT NULL,
                designation     TEXT DEFAULT 'unknown',
                assigned_tier   TEXT DEFAULT 'none'
            );
            INSERT INTO coins (
                coin_id, wallet_type, amount_mojos, status, first_seen, last_seen
            ) VALUES (
                'legacy-coin-1',
                'xch', 1000, 'free', datetime('now'), datetime('now')
            );
            """
        )
        conn.commit()
        conn.close()

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

    def test_init_database_migrates_legacy_coins_table(self):
        _db.init_database()
        cols = {
            row["name"]
            for row in _db.get_connection()
            .execute("PRAGMA table_info(coins)")
            .fetchall()
        }
        self.assertIn("asset_id", cols)
        self.assertIn("owner_asset_id", cols)
        idx = _db.get_connection().execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_coins_wallet_asset_status'"
        ).fetchone()
        self.assertIsNotNone(idx)

    def test_xch_coins_get_xch_asset_id(self):
        _db.upsert_coin("0x" + ("44" * 32), "xch", 1_000_000_000_000)
        rows = _db.get_free_coins("xch", asset_id="xch")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["asset_id"], "xch")


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestOpenOfferCountsAndPairsApi(unittest.TestCase):
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
        self._orig_active_cat = dict(api_server._active_cat)
        api_server._active_cat.update(
            {
                "asset_id": _ASSET_A,
                "name": "Alpha",
                "ticker_id": "AAA",
                "decimals": 3,
                "wallet_id": 2,
            }
        )

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
        api_server._active_cat.clear()
        api_server._active_cat.update(self._orig_active_cat)

    def _seed_offer(self, asset_id, side, trade_id):
        _db.add_offer(
            trade_id=trade_id,
            side=side,
            price_xch=Decimal("0.01"),
            size_xch=Decimal("0.1"),
            size_cat=Decimal("10"),
            cat_asset_id=asset_id,
        )

    def test_count_open_offers_by_cat(self):
        self._seed_offer(_ASSET_A, "buy", "t-a-buy")
        self._seed_offer(_ASSET_A, "sell", "t-a-sell")
        self._seed_offer(_ASSET_B, "buy", "t-b-buy")
        counts = _db.count_open_offers_by_cat()
        self.assertEqual(counts[_ASSET_A]["buy"], 1)
        self.assertEqual(counts[_ASSET_A]["sell"], 1)
        self.assertEqual(counts[_ASSET_A]["total"], 2)
        self.assertEqual(counts[_ASSET_B]["buy"], 1)
        self.assertEqual(counts[_ASSET_B]["total"], 1)

    def test_api_pairs_shape(self):
        pair_store.save_pair_overlay(
            _ASSET_A, {"BASE_SPREAD_BPS": "900", "LIQUIDITY_MODE": "two_sided"}
        )
        pair_store.upsert_pair_identity(
            _ASSET_A, name="Alpha", ticker_id="AAA", decimals=3
        )
        self._seed_offer(_ASSET_A, "buy", "t-focus-buy")

        with (
            patch("wallet.get_wallets", return_value={"success": True, "wallets": []}),
            patch(
                "wallet.get_wallet_balance",
                return_value={
                    "success": True,
                    "wallet_balance": {
                        "spendable_balance": 2_000_000_000_000,
                        "confirmed_wallet_balance": 3_000_000_000_000,
                    },
                },
            ),
        ):
            resp = self.client.get(
                "/api/pairs",
                headers={"X-Bot-Local-Token": self.token},
                environ_base=_LOOPBACK,
            )
        self.assertEqual(resp.status_code, 200, resp.get_json())
        body = resp.get_json()
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("focus_asset_id"), _ASSET_A)
        self.assertEqual(body.get("max_concurrent_pairs"), 4)
        self.assertIn("xch", body)
        pairs = body.get("pairs") or []
        self.assertTrue(any(p.get("asset_id") == _ASSET_A for p in pairs))
        focus = next(p for p in pairs if p["asset_id"] == _ASSET_A)
        self.assertTrue(focus["is_focus"])
        self.assertTrue(focus["has_saved_profile"])
        self.assertEqual(focus["open_offers"]["buy"], 1)

    def test_build_pairs_overview_merges_wallet_cats(self):
        wallets = {
            "success": True,
            "wallets": [
                {
                    "id": 5,
                    "type": 6,
                    "name": "Beta",
                    "asset_id": _ASSET_B,
                    "decimals": 3,
                }
            ],
        }

        def _bal(wallet_id):
            if int(wallet_id) == 1:
                return {
                    "success": True,
                    "wallet_balance": {
                        "spendable_balance": 1_000_000_000_000,
                        "confirmed_wallet_balance": 1_000_000_000_000,
                    },
                }
            return {
                "success": True,
                "wallet_balance": {
                    "spendable_balance": 5000,
                    "confirmed_wallet_balance": 5000,
                },
            }

        with (
            patch("wallet.get_wallets", return_value=wallets),
            patch("wallet.get_wallet_balance", side_effect=_bal),
        ):
            payload = pair_store.build_pairs_overview(
                focus_asset_id=_ASSET_A,
                active_cat={
                    "asset_id": _ASSET_A,
                    "name": "Alpha",
                    "ticker_id": "AAA",
                    "wallet_id": 2,
                },
            )
        asset_ids = {p["asset_id"] for p in payload["pairs"]}
        self.assertIn(_ASSET_A, asset_ids)
        self.assertIn(_ASSET_B, asset_ids)
        beta = next(p for p in payload["pairs"] if p["asset_id"] == _ASSET_B)
        self.assertTrue(beta["in_wallet"])
        self.assertFalse(beta["is_focus"])
        self.assertAlmostEqual(beta["balances"]["spendable"], 5.0)

    def _seed_matched_trip(self, asset_id, buy_trade, sell_trade, pnl):
        buy_id = _db.record_fill(
            trade_id=buy_trade,
            side="buy",
            price_xch=Decimal("0.01"),
            size_xch=Decimal("0.1"),
            size_cat=Decimal("10"),
            cat_asset_id=asset_id,
        )
        sell_id = _db.record_fill(
            trade_id=sell_trade,
            side="sell",
            price_xch=Decimal("0.012"),
            size_xch=Decimal("0.12"),
            size_cat=Decimal("10"),
            cat_asset_id=asset_id,
        )
        self.assertGreater(buy_id, 0)
        self.assertGreater(sell_id, 0)
        _db.match_round_trip(buy_id, sell_id, Decimal(str(pnl)))

    def test_pairs_overview_includes_per_pair_and_aggregate_pnl(self):
        pair_store.upsert_pair_identity(
            _ASSET_A, name="Alpha", ticker_id="AAA", decimals=3
        )
        pair_store.upsert_pair_identity(
            _ASSET_B, name="Beta", ticker_id="BBB", decimals=3
        )
        self._seed_matched_trip(_ASSET_A, "buy-a-1", "sell-a-1", "0.05")
        self._seed_matched_trip(_ASSET_B, "buy-b-1", "sell-b-1", "0.02")

        with (
            patch("wallet.get_wallets", return_value={"success": True, "wallets": []}),
            patch(
                "wallet.get_wallet_balance",
                return_value={
                    "success": True,
                    "wallet_balance": {
                        "spendable_balance": 1_000_000_000_000,
                        "confirmed_wallet_balance": 1_000_000_000_000,
                    },
                },
            ),
            patch.object(api_server, "_get_run_history_cutoff", return_value=None),
        ):
            payload = pair_store.build_pairs_overview(focus_asset_id=_ASSET_A)

        alpha = next(p for p in payload["pairs"] if p["asset_id"] == _ASSET_A)
        beta = next(p for p in payload["pairs"] if p["asset_id"] == _ASSET_B)
        self.assertEqual(Decimal(str(alpha["realised_pnl_xch"])), Decimal("0.05"))
        self.assertEqual(Decimal(str(beta["realised_pnl_xch"])), Decimal("0.02"))
        self.assertEqual(alpha["round_trips"], 1)
        self.assertEqual(beta["round_trips"], 1)
        self.assertIn("pnl", payload)
        self.assertEqual(
            Decimal(str(payload["pnl"]["realised_pnl_xch"])), Decimal("0.07")
        )
        self.assertEqual(payload["pnl"]["round_trips"], 2)

    def test_pairs_overview_includes_xch_ownership(self):
        pair_store.upsert_pair_identity(
            _ASSET_A, name="Alpha", ticker_id="AAA", decimals=3
        )
        pair_store.set_xch_budget_mojos(_ASSET_A, 10_000_000_000_000)
        _db.upsert_coin(
            "owned-a",
            "xch",
            2_000_000_000_000,
            designation="tier_spare",
            assigned_tier="inner",
        )
        _db.upsert_coin(
            "fee-shared",
            "xch",
            50_000_000,
            designation="tier_spare",
            assigned_tier="fees",
        )
        claim = _db.claim_xch_ownership_for_pair(
            _ASSET_A, max_mojos=10_000_000_000_000
        )
        self.assertEqual(claim["claimed_coins"], 1)

        with (
            patch("wallet.get_wallets", return_value={"success": True, "wallets": []}),
            patch(
                "wallet.get_wallet_balance",
                return_value={
                    "success": True,
                    "wallet_balance": {
                        "spendable_balance": 1_000_000_000_000,
                        "confirmed_wallet_balance": 1_000_000_000_000,
                    },
                },
            ),
        ):
            payload = pair_store.build_pairs_overview(focus_asset_id=_ASSET_A)

        self.assertIn("xch_ownership", payload)
        alpha = next(p for p in payload["pairs"] if p["asset_id"] == _ASSET_A)
        self.assertEqual(alpha["xch_owned_mojos"], 2_000_000_000_000)
        self.assertAlmostEqual(alpha["xch_owned"], 2.0)
        self.assertEqual(alpha["xch_owned_coins"], 1)
        self.assertEqual(payload["xch_ownership"]["shared"]["fees_coins"], 1)


if __name__ == "__main__":
    unittest.main()
