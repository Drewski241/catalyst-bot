"""Slice 04-10 — smart-defaults endpoint contract tests.

Tests GET /api/smart-defaults:
  - No auth required (read-only)
  - liquidity_mode parameter routing (two_sided/buy_only/sell_only)
  - Invalid liquidity_mode falls back to two_sided
  - risk_profile parameter forwarded
  - Exception path returns 500
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import api_server
    from flask import jsonify as _jsonify
    _SKIP = None
except (ModuleNotFoundError, ImportError) as exc:
    api_server = None
    _SKIP = str(exc)


def _fake_defaults_response(**kwargs):
    """Return a Flask Response mimicking _calculate_smart_defaults output."""
    with api_server.app.app_context():
        return _jsonify({
            "success": True,
            "spread_bps": 200,
            "default_trade_xch": "0.5",
            "liquidity_mode": kwargs.get("liquidity_mode", "two_sided"),
            "risk_profile": kwargs.get("risk_profile", "balanced"),
        })


class _FlaskBase(unittest.TestCase):
    _LOOPBACK = {"REMOTE_ADDR": "127.0.0.1"}

    def setUp(self):
        api_server.app.testing = True
        self.client = api_server.app.test_client()
        api_server._rate_limit_log.clear()

    def tearDown(self):
        api_server._rate_limit_log.clear()


@unittest.skipIf(_SKIP is not None, f"api_server unavailable: {_SKIP}")
class TestSmartDefaults(_FlaskBase):

    def test_returns_200(self):
        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=_fake_defaults_response):
            resp = self.client.get("/api/smart-defaults",
                                   environ_base=self._LOOPBACK)
        self.assertEqual(resp.status_code, 200)

    def test_default_liquidity_mode_two_sided(self):
        captured = {}

        def capture(**kwargs):
            captured.update(kwargs)
            return _fake_defaults_response(**kwargs)

        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=capture):
            self.client.get("/api/smart-defaults",
                            environ_base=self._LOOPBACK)
        self.assertEqual(captured.get("liquidity_mode"), "two_sided")

    def test_buy_only_mode_forwarded(self):
        captured = {}

        def capture(**kwargs):
            captured.update(kwargs)
            return _fake_defaults_response(**kwargs)

        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=capture):
            self.client.get("/api/smart-defaults?liquidity_mode=buy_only",
                            environ_base=self._LOOPBACK)
        self.assertEqual(captured.get("liquidity_mode"), "buy_only")

    def test_sell_only_mode_forwarded(self):
        captured = {}

        def capture(**kwargs):
            captured.update(kwargs)
            return _fake_defaults_response(**kwargs)

        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=capture):
            self.client.get("/api/smart-defaults?liquidity_mode=sell_only",
                            environ_base=self._LOOPBACK)
        self.assertEqual(captured.get("liquidity_mode"), "sell_only")

    def test_invalid_liquidity_mode_falls_back_to_two_sided(self):
        captured = {}

        def capture(**kwargs):
            captured.update(kwargs)
            return _fake_defaults_response(**kwargs)

        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=capture):
            self.client.get("/api/smart-defaults?liquidity_mode=invalid_mode",
                            environ_base=self._LOOPBACK)
        self.assertEqual(captured.get("liquidity_mode"), "two_sided")

    def test_risk_profile_forwarded(self):
        captured = {}

        def capture(**kwargs):
            captured.update(kwargs)
            return _fake_defaults_response(**kwargs)

        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=capture):
            self.client.get("/api/smart-defaults?risk_profile=conservative",
                            environ_base=self._LOOPBACK)
        self.assertEqual(captured.get("risk_profile"), "conservative")

    def test_exception_returns_500(self):
        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=Exception("market data unavailable")):
            resp = self.client.get("/api/smart-defaults",
                                   environ_base=self._LOOPBACK)
        self.assertEqual(resp.status_code, 500)
        body = resp.get_json()
        self.assertIn("error", body)

    def test_reserve_params_forwarded(self):
        captured = {}

        def capture(**kwargs):
            captured.update(kwargs)
            return _fake_defaults_response(**kwargs)

        with patch.object(api_server, "_calculate_smart_defaults",
                          side_effect=capture):
            self.client.get(
                "/api/smart-defaults?xch_reserve=0.5&cat_reserve=100",
                environ_base=self._LOOPBACK,
            )
        self.assertEqual(str(captured.get("xch_reserve")), "0.5")
        self.assertEqual(str(captured.get("cat_reserve")), "100")


if __name__ == "__main__":
    unittest.main()
