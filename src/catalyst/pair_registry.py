"""Registry of concurrent pair runtimes (Phase 3 multi-pair).

One process hosts up to MAX_CONCURRENT_PAIRS BotLoops. Each runtime freezes
a PairSnapshot (identity + economics + XCH budget) and runs under
pair_context so ambient cfg reads stay pair-scoped. Shared XCH is gated by
shared_xch_ledger.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from super_log import slog

from pair_context import PairSnapshot, build_snapshot_from_store, install_config_overlay_hook
from shared_xch_ledger import MAX_CONCURRENT_PAIRS, ledger


@dataclass
class PairRuntime:
    asset_id: str
    snapshot: PairSnapshot
    bot: Any = None
    status: str = "stopped"  # stopped|starting|running|stopping|error
    last_error: str = ""


class PairRegistry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._runtimes: Dict[str, PairRuntime] = {}
        self._shared_fee_pool = None
        self._mempool_refs = 0
        self._splash_owner: Optional[str] = None
        install_config_overlay_hook()

    def _norm(self, asset_id: str) -> str:
        return str(asset_id or "").strip().lower().replace("0x", "")

    def list_running(self) -> List[str]:
        with self._lock:
            return [
                aid
                for aid, rt in self._runtimes.items()
                if rt.bot is not None and rt.bot.is_running()
            ]

    def is_running(self, asset_id: str) -> bool:
        aid = self._norm(asset_id)
        with self._lock:
            rt = self._runtimes.get(aid)
            return bool(rt and rt.bot and rt.bot.is_running())

    def any_running(self) -> bool:
        return bool(self.list_running())

    def get_runtime(self, asset_id: str) -> Optional[PairRuntime]:
        return self._runtimes.get(self._norm(asset_id))

    def get_focus_bot(self, focus_asset_id: Optional[str] = None) -> Any:
        """Return a bot suitable for legacy api_server.bot consumers."""
        focus = self._norm(focus_asset_id or "")
        with self._lock:
            if focus and focus in self._runtimes:
                bot = self._runtimes[focus].bot
                if bot is not None:
                    return bot
            for rt in self._runtimes.values():
                if rt.bot is not None and rt.bot.is_running():
                    return rt.bot
            for rt in self._runtimes.values():
                if rt.bot is not None:
                    return rt.bot
        return None

    def _ensure_fee_pool(self, bot: Any) -> None:
        """Share one FeeCoinPool across pair CoinManagers when possible."""
        try:
            pool = getattr(bot.coin_manager, "fee_pool", None)
            if self._shared_fee_pool is None and pool is not None:
                self._shared_fee_pool = pool
            elif self._shared_fee_pool is not None and pool is not self._shared_fee_pool:
                bot.coin_manager.fee_pool = self._shared_fee_pool
                bot.offer_manager._fee_pool = self._shared_fee_pool
        except Exception as exc:
            slog("PAIR_REGISTRY", f"fee pool share skipped: {exc}", level="warning")

    def start_pair(
        self,
        asset_id: str,
        *,
        cfg: Any = None,
        active_cat: Optional[Dict[str, Any]] = None,
        skip_budget_check: bool = False,
    ) -> Dict[str, Any]:
        """Start trading for one pair. Enforces max-4 and XCH budget gate."""
        aid = self._norm(asset_id)
        if len(aid) != 64:
            return {"success": False, "error": "Invalid CAT asset id"}

        with self._lock:
            running = self.list_running()
            if aid in running:
                return {"success": True, "status": "already_running", "asset_id": aid}
            if len(running) >= MAX_CONCURRENT_PAIRS:
                return {
                    "success": False,
                    "error": f"Already running {len(running)} pairs "
                    f"(max {MAX_CONCURRENT_PAIRS})",
                }

            if cfg is None:
                from config import cfg as _cfg

                cfg = _cfg

            snapshot = build_snapshot_from_store(
                aid, active_cat=active_cat, cfg=cfg
            )
            budget = int(snapshot.xch_budget_mojos or 0)
            if not skip_budget_check:
                ok, reason = ledger.can_allocate(
                    aid,
                    budget,
                    cfg=cfg,
                    running_asset_ids=running,
                )
                if not ok:
                    return {"success": False, "error": reason, "asset_id": aid}

            # Create or reuse BotLoop for this asset.
            rt = self._runtimes.get(aid)
            if rt is None or rt.bot is None:
                from bot_loop import BotLoop

                bot = BotLoop()
                bot._pair_snapshot = snapshot
                bot._pair_asset_id = aid
                bot._pair_registry = self
                self._ensure_fee_pool(bot)
                rt = PairRuntime(asset_id=aid, snapshot=snapshot, bot=bot)
                self._runtimes[aid] = rt
            else:
                rt.snapshot = snapshot
                rt.bot._pair_snapshot = snapshot
                rt.bot._pair_asset_id = aid
                rt.bot._pair_registry = self
                self._ensure_fee_pool(rt.bot)

            rt.status = "starting"
            rt.last_error = ""

            # Sync wallet_sage module CAT id for this start (context covers cycles).
            try:
                from wallet_sage import notify_cat_asset_id_changed

                notify_cat_asset_id_changed(aid)
            except Exception:
                pass

            started = False
            try:
                started = bool(rt.bot.start())
            except Exception as exc:
                rt.status = "error"
                rt.last_error = str(exc)
                slog("PAIR_REGISTRY", f"start_pair failed: {exc}", level="error")
                return {"success": False, "error": str(exc), "asset_id": aid}

            if not started:
                state = {}
                try:
                    state = rt.bot.get_state() or {}
                except Exception:
                    state = {}
                rt.status = "error"
                rt.last_error = str(state.get("status") or "blocked")
                return {
                    "success": False,
                    "error": "Bot start was blocked before trading could begin",
                    "bot_status": state.get("status") or "blocked",
                    "asset_id": aid,
                }

            rt.status = "running"
            self._mempool_refs += 1
            if self._splash_owner is None:
                self._splash_owner = aid
            slog(
                "PAIR_REGISTRY",
                f"Started pair {snapshot.name or aid[:12]} "
                f"(budget={ledger.mojos_to_xch(budget)} XCH)",
                level="info",
            )
            return {
                "success": True,
                "status": "started",
                "asset_id": aid,
                "xch_budget_mojos": budget,
                "running_pairs": self.list_running(),
            }

    def stop_pair(self, asset_id: str) -> Dict[str, Any]:
        """Stop one pair. Leaves open offers resting (no auto-cancel)."""
        aid = self._norm(asset_id)
        with self._lock:
            rt = self._runtimes.get(aid)
            if rt is None or rt.bot is None:
                return {"success": True, "status": "not_running", "asset_id": aid}
            if not rt.bot.is_running():
                rt.status = "stopped"
                return {"success": True, "status": "not_running", "asset_id": aid}

            rt.status = "stopping"
            # Tell BotLoop whether it should tear down shared watchers.
            other_running = [x for x in self.list_running() if x != aid]
            rt.bot._pair_stop_shared_services = len(other_running) == 0
            try:
                rt.bot.stop()
            except Exception as exc:
                rt.status = "error"
                rt.last_error = str(exc)
                return {"success": False, "error": str(exc), "asset_id": aid}

            rt.status = "stopped"
            self._mempool_refs = max(0, self._mempool_refs - 1)
            if self._splash_owner == aid:
                self._splash_owner = other_running[0] if other_running else None
            slog(
                "PAIR_REGISTRY",
                f"Stopped pair {aid[:12]}... (offers left resting)",
                level="info",
            )
            return {
                "success": True,
                "status": "stopped",
                "asset_id": aid,
                "running_pairs": self.list_running(),
            }

    def stop_all_for_prep(self, reason: str = "coin_prep") -> Dict[str, Any]:
        """Stop every running pair before a wallet-wide coin prep.

        Offers are left resting (same as stop_pair). Returns the asset ids
        that were stopped so the GUI can remind the operator to restart.
        """
        stopped: List[str] = []
        errors: Dict[str, str] = {}
        for aid in list(self.list_running()):
            result = self.stop_pair(aid)
            if result.get("success"):
                if result.get("status") == "stopped":
                    stopped.append(aid)
            else:
                errors[aid] = str(result.get("error") or "stop failed")
        if stopped:
            slog(
                "PAIR_REGISTRY",
                f"Stopped {len(stopped)} pair(s) for {reason}: "
                + ", ".join(a[:12] for a in stopped),
                level="info",
            )
        return {"success": not errors, "stopped": stopped, "errors": errors}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            pairs = []
            for aid, rt in self._runtimes.items():
                running = bool(rt.bot and rt.bot.is_running())
                pairs.append(
                    {
                        "asset_id": aid,
                        "name": rt.snapshot.name,
                        "running": running,
                        "status": "running" if running else rt.status,
                        "xch_budget_mojos": rt.snapshot.xch_budget_mojos,
                        "last_error": rt.last_error,
                    }
                )
            return {
                "running_count": len(self.list_running()),
                "max_concurrent_pairs": MAX_CONCURRENT_PAIRS,
                "pairs": pairs,
            }


_REGISTRY: Optional[PairRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_registry() -> PairRegistry:
    global _REGISTRY
    with _REGISTRY_LOCK:
        if _REGISTRY is None:
            _REGISTRY = PairRegistry()
        return _REGISTRY
