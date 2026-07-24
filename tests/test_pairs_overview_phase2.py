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


if __name__ == "__main__":
    unittest.main()
