"""Shared-tier credit + multi-pair smoke verification helpers."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import database as _db
    import multi_pair_smoke as smoke

    _SKIP = None
except (ModuleNotFoundError, ImportError) as exc:
    _db = None
    smoke = None
    _SKIP = str(exc)


_ASSET_A = "a" * 64
_ASSET_B = "b" * 64


@unittest.skipIf(_SKIP, f"Import failed: {_SKIP}")
class TestSharedTierCredit(unittest.TestCase):
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

    def test_credit_skips_full_shared_fee_target(self):
        for i in range(3):
            _db.upsert_coin(
                f"fee-{i}",
                "xch",
                50_000_000,
                designation="tier_spare",
                assigned_tier="fees",
            )
        result = _db.credit_shared_xch_tier_targets(
            {"inner": 10, "fees": 3, "sniper": 2}
        )
        self.assertEqual(result["credited"]["fees"], 3)
        self.assertNotIn("fees", result["adjusted_counts"])
        self.assertEqual(result["adjusted_counts"]["inner"], 10)
        self.assertEqual(result["adjusted_counts"]["sniper"], 2)

    def test_credit_partial_sniper(self):
        _db.upsert_coin(
            "snip-0",
            "xch",
            10_000_000_000,
            designation="tier_spare",
            assigned_tier="sniper",
        )
        result = _db.credit_shared_xch_tier_targets({"sniper": 3, "mid": 4})
        self.assertEqual(result["credited"]["sniper"], 1)
        self.assertEqual(result["adjusted_counts"]["sniper"], 2)

    def test_ownership_isolation_and_shared_verify(self):
        _db.upsert_coin(
            "owned-a",
            "xch",
            1_000_000_000_000,
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
        _db.claim_xch_ownership_for_pair(_ASSET_A, max_mojos=1_000_000_000_000)

        iso = smoke.verify_ownership_isolation(_ASSET_A, _ASSET_B)
        self.assertTrue(iso["ok"], iso["issues"])
        shared = smoke.verify_shared_pools(min_fees=1)
        self.assertTrue(shared["ok"], shared["issues"])
        prot = smoke.verify_protected_from_prep(_ASSET_B)
        self.assertTrue(prot["ok"], prot["issues"])
        self.assertGreaterEqual(prot["foreign"], 1)
        self.assertGreaterEqual(prot["shared"], 1)

    def test_checklist_mentions_both_assets(self):
        text = smoke.format_checklist(
            smoke.live_smoke_checklist(_ASSET_A, _ASSET_B)
        )
        self.assertIn(_ASSET_A[:12], text)
        self.assertIn(_ASSET_B[:12], text)
        self.assertIn("GET /api/pairs", text)


if __name__ == "__main__":
    unittest.main()
