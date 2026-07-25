"""Shared XCH capital ledger for multi-pair trading.

XCH is shared across pairs on one Sage wallet. Each enabled/running pair
gets a hard ``xch_budget_mojos`` allocation. Buy-side offer creation must
stay within that budget. A process-global ``XCH_RESERVE`` floor and fee
buffer are never allocated to any pair.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from super_log import slog


XCH_MOJOS = 1_000_000_000_000
DEFAULT_FEE_BUFFER_XCH = Decimal("0.01")
MAX_CONCURRENT_PAIRS = 4


class SharedXchLedger:
    """Tracks per-pair XCH budgets and remaining capacity."""

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def xch_to_mojos(self, xch: Any) -> int:
        try:
            return int(Decimal(str(xch)) * XCH_MOJOS)
        except Exception:
            return 0

    def mojos_to_xch(self, mojos: int) -> Decimal:
        return Decimal(mojos) / Decimal(XCH_MOJOS)

    def fee_buffer_mojos(self, cfg: Any = None) -> int:
        if cfg is None:
            try:
                from config import cfg as _cfg

                cfg = _cfg
            except Exception:
                cfg = None
        # Prefer explicit fee coin inventory when available.
        try:
            fee_count = int(getattr(cfg, "FEE_PREP_COUNT", 0) or 0)
            fee_size = Decimal(str(getattr(cfg, "FEE_COIN_SIZE_XCH", "0") or "0"))
            if fee_count > 0 and fee_size > 0:
                return self.xch_to_mojos(fee_size * fee_count)
        except Exception:
            pass
        return self.xch_to_mojos(DEFAULT_FEE_BUFFER_XCH)

    def wallet_reserve_mojos(self, cfg: Any = None) -> int:
        if cfg is None:
            try:
                from config import cfg as _cfg

                cfg = _cfg
            except Exception:
                return 0
        try:
            return self.xch_to_mojos(getattr(cfg, "XCH_RESERVE", 0) or 0)
        except Exception:
            return 0

    def spendable_xch_mojos(self) -> int:
        """Best-effort spendable XCH from the wallet (mojos)."""
        try:
            from wallet import get_wallet_balance, WALLET_ID_XCH

            result = get_wallet_balance(WALLET_ID_XCH)
            if not result or result.get("success") is False:
                return 0
            wb = result.get("wallet_balance") or result
            spendable = wb.get("spendable_balance", 0) or 0
            # Sage may return mojos already (int) or XCH float depending on path.
            spendable_dec = Decimal(str(spendable))
            if spendable_dec > Decimal("1000000"):
                # Likely already mojos.
                return int(spendable_dec)
            return self.xch_to_mojos(spendable_dec)
        except Exception as exc:
            slog("XCH_LEDGER", f"spendable lookup failed: {exc}", level="warning")
            return 0

    def open_buy_xch_mojos(self, asset_id: str) -> int:
        """Sum size_xch of open buy offers for a pair (mojos)."""
        aid = str(asset_id or "").strip().lower().replace("0x", "")
        if len(aid) != 64:
            return 0
        try:
            from database import get_open_offers

            total = 0
            for offer in get_open_offers(side="buy", cat_asset_id=aid) or []:
                raw = offer.get("size_xch")
                if raw is None:
                    continue
                try:
                    size = Decimal(str(raw))
                except Exception:
                    continue
                # Heuristic: values >= 1e6 are already mojos.
                if size >= Decimal("1000000"):
                    total += int(size)
                else:
                    total += self.xch_to_mojos(size)
            return total
        except Exception as exc:
            slog("XCH_LEDGER", f"open buy sum failed: {exc}", level="warning")
            return 0

    def get_budget_mojos(self, asset_id: str) -> int:
        import pair_store

        return int(pair_store.get_xch_budget_mojos(asset_id) or 0)

    def remaining_budget_mojos(self, asset_id: str) -> int:
        budget = self.get_budget_mojos(asset_id)
        used = self.open_buy_xch_mojos(asset_id)
        return max(0, budget - used)

    def allocatable_mojos(self, cfg: Any = None) -> int:
        """XCH mojos available to assign across pairs (after reserve + fees)."""
        spendable = self.spendable_xch_mojos()
        reserve = self.wallet_reserve_mojos(cfg)
        fees = self.fee_buffer_mojos(cfg)
        return max(0, spendable - reserve - fees)

    def sum_budgets_mojos(self, exclude_asset_id: Optional[str] = None) -> int:
        import pair_store

        exclude = str(exclude_asset_id or "").strip().lower().replace("0x", "")
        total = 0
        for row in pair_store.list_pair_configs():
            aid = str(row.get("cat_asset_id") or "")
            if exclude and aid == exclude:
                continue
            try:
                total += int(row.get("xch_budget_mojos") or 0)
            except (TypeError, ValueError):
                continue
        return total

    def remaining_allocatable_mojos(
        self,
        asset_id: Optional[str] = None,
        *,
        cfg: Any = None,
        running_asset_ids: Optional[List[str]] = None,
    ) -> int:
        """XCH mojos still free to assign to ``asset_id``.

        Subtracts other pairs' budgets from process allocatable capital.
        When ``running_asset_ids`` is provided, only those pairs' budgets
        count as reserved (plus any saved budget for non-running pairs is
        ignored) — matching the start-gate semantics in ``can_allocate``.
        """
        aid = str(asset_id or "").strip().lower().replace("0x", "")
        available = self.allocatable_mojos(cfg)
        if running_asset_ids is not None:
            others = 0
            for running_id in running_asset_ids:
                rid = str(running_id or "").strip().lower().replace("0x", "")
                if rid and rid != aid:
                    others += self.get_budget_mojos(rid)
        else:
            others = self.sum_budgets_mojos(exclude_asset_id=aid or None)
        return max(0, available - others)

    def portfolio_open_buy_mojos(self) -> int:
        """Sum open buy XCH across all pairs with a saved budget."""
        import pair_store

        total = 0
        for row in pair_store.list_pair_configs():
            aid = str(row.get("cat_asset_id") or "")
            if len(aid) == 64:
                total += self.open_buy_xch_mojos(aid)
        return total

    def portfolio_cap_mojos(self, cfg: Any = None) -> int:
        """Process-global portfolio exposure cap in mojos (0 = disabled)."""
        if cfg is None:
            try:
                from config import cfg as _cfg

                cfg = _cfg
            except Exception:
                return 0
        try:
            return self.xch_to_mojos(
                getattr(cfg, "PORTFOLIO_MAX_XCH_EXPOSURE", 0) or 0
            )
        except Exception:
            return 0

    def can_spend_portfolio(
        self, spend_xch_mojos: int, *, cfg: Any = None
    ) -> Tuple[bool, str]:
        """Optional hard cap on aggregate open buy XCH across all pairs."""
        spend = max(0, int(spend_xch_mojos or 0))
        if spend <= 0:
            return True, ""
        cap = self.portfolio_cap_mojos(cfg)
        if cap <= 0:
            return True, ""
        used = self.portfolio_open_buy_mojos()
        if used + spend > cap:
            return (
                False,
                f"Portfolio exposure cap: open buys would reach "
                f"{self.mojos_to_xch(used + spend)} XCH but "
                f"PORTFOLIO_MAX_XCH_EXPOSURE is {self.mojos_to_xch(cap)} XCH",
            )
        return True, ""

    def can_allocate(
        self,
        asset_id: str,
        budget_mojos: int,
        *,
        cfg: Any = None,
        running_asset_ids: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """Validate a proposed budget for a pair against shared capital."""
        aid = str(asset_id or "").strip().lower().replace("0x", "")
        budget_mojos = max(0, int(budget_mojos or 0))
        if budget_mojos <= 0:
            return False, "Set an XCH budget for this pair before starting"

        others = self.sum_budgets_mojos(exclude_asset_id=aid)
        # If only counting running pairs' budgets, prefer that for start gate.
        if running_asset_ids is not None:
            others = 0
            for running_id in running_asset_ids:
                rid = str(running_id or "").strip().lower().replace("0x", "")
                if rid and rid != aid:
                    others += self.get_budget_mojos(rid)

        available = self.allocatable_mojos(cfg)
        if others + budget_mojos > available:
            need = self.mojos_to_xch(others + budget_mojos)
            have = self.mojos_to_xch(available)
            return (
                False,
                f"XCH budgets exceed shared capital: need {need} XCH, "
                f"have {have} XCH after reserve + fee buffer",
            )
        return True, ""

    def can_spend_buy(
        self, asset_id: str, spend_xch_mojos: int
    ) -> Tuple[bool, str]:
        """Check whether a new buy offer fits the pair's remaining budget."""
        spend = max(0, int(spend_xch_mojos or 0))
        if spend <= 0:
            return True, ""
        remaining = self.remaining_budget_mojos(asset_id)
        if spend > remaining:
            return (
                False,
                f"Buy spends {self.mojos_to_xch(spend)} XCH but pair only has "
                f"{self.mojos_to_xch(remaining)} XCH budget remaining",
            )
        return True, ""

    def snapshot(self, asset_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        import pair_store

        ids = asset_ids or [
            r.get("cat_asset_id") for r in pair_store.list_pair_configs()
        ]
        pairs = []
        for aid in ids:
            aid_n = str(aid or "").strip().lower().replace("0x", "")
            if len(aid_n) != 64:
                continue
            budget = self.get_budget_mojos(aid_n)
            used = self.open_buy_xch_mojos(aid_n)
            pairs.append(
                {
                    "asset_id": aid_n,
                    "budget_mojos": budget,
                    "budget_xch": str(self.mojos_to_xch(budget)),
                    "used_mojos": used,
                    "used_xch": str(self.mojos_to_xch(used)),
                    "remaining_mojos": max(0, budget - used),
                    "remaining_xch": str(self.mojos_to_xch(max(0, budget - used))),
                }
            )
        available = self.allocatable_mojos()
        allocated = self.sum_budgets_mojos()
        open_buys = self.portfolio_open_buy_mojos()
        portfolio_cap = self.portfolio_cap_mojos()
        return {
            "available_mojos": available,
            "available_xch": str(self.mojos_to_xch(available)),
            "allocated_mojos": allocated,
            "allocated_xch": str(self.mojos_to_xch(allocated)),
            "remaining_allocatable_mojos": max(0, available - allocated),
            "remaining_allocatable_xch": str(
                self.mojos_to_xch(max(0, available - allocated))
            ),
            "portfolio_open_buy_mojos": open_buys,
            "portfolio_open_buy_xch": str(self.mojos_to_xch(open_buys)),
            "portfolio_cap_mojos": portfolio_cap,
            "portfolio_cap_xch": str(self.mojos_to_xch(portfolio_cap))
            if portfolio_cap > 0
            else None,
            "reserve_mojos": self.wallet_reserve_mojos(),
            "fee_buffer_mojos": self.fee_buffer_mojos(),
            "max_concurrent_pairs": MAX_CONCURRENT_PAIRS,
            "pairs": pairs,
        }


# Process singleton
ledger = SharedXchLedger()
