"""Process-wide coin-prep queue with fair per-pair scheduling.

Full coin prep is a single Sage-wallet worker. Under multi-pair trading,
pairs must not launch parallel workers. This queue accepts one request per
asset, runs one worker at a time, and serves waiting pairs in fair FIFO
order (round-robin by asset: a pair that just finished goes behind any
pairs that were waiting).
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from super_log import slog


def _norm_asset(asset_id: Optional[str]) -> str:
    return str(asset_id or "").strip().lower().replace("0x", "")


@dataclass
class PrepRequest:
    asset_id: str
    request_id: str
    coin_multiplier: float = 1.0
    reset_pnl: bool = False
    reset_offer_history: bool = False
    reset_counters: bool = False
    source: str = "api"
    enqueued_at: float = field(default_factory=time.time)
    status: str = "queued"  # queued|running|done|failed|cancelled

    def to_params(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "request_id": self.request_id,
            "coin_multiplier": self.coin_multiplier,
            "reset_pnl": self.reset_pnl,
            "reset_offer_history": self.reset_offer_history,
            "reset_counters": self.reset_counters,
            "source": self.source,
        }

    def to_public(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "request_id": self.request_id,
            "status": self.status,
            "coin_multiplier": self.coin_multiplier,
            "enqueued_at": self.enqueued_at,
            "source": self.source,
        }


class PrepQueue:
    """Singleton-friendly fair prep scheduler."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # One pending request per asset (coalesced).
        self._pending: "OrderedDict[str, PrepRequest]" = OrderedDict()
        self._current: Optional[PrepRequest] = None
        self._last_served: str = ""
        self._launcher: Optional[Callable[[Dict[str, Any]], None]] = None

    def set_launcher(self, launcher: Callable[[Dict[str, Any]], None]) -> None:
        """Register the function that actually starts a prep worker."""
        with self._lock:
            self._launcher = launcher

    def current_asset_id(self) -> Optional[str]:
        with self._lock:
            if self._current is None:
                return None
            return self._current.asset_id or None

    def is_busy(self) -> bool:
        with self._lock:
            return self._current is not None

    def queued_assets(self) -> List[str]:
        with self._lock:
            return list(self._pending.keys())

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "busy": self._current is not None,
                "current": self._current.to_public() if self._current else None,
                "queued": [req.to_public() for req in self._pending.values()],
                "queue_depth": len(self._pending),
                "last_served": self._last_served or None,
            }

    def enqueue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Queue a prep request. Coalesces duplicate asset_ids.

        A pair that is currently running may still be queued for a follow-up
        run (starts after the current worker finishes, behind any other
        waiting pairs — fair skip of the just-finished asset).
        """
        aid = _norm_asset(params.get("asset_id"))
        if len(aid) != 64:
            return {
                "success": False,
                "error": "asset_id required to queue coin prep for a pair",
            }

        with self._lock:
            req = PrepRequest(
                asset_id=aid,
                request_id=str(params.get("request_id") or uuid.uuid4().hex[:10]),
                coin_multiplier=float(params.get("coin_multiplier", 1.0) or 1.0),
                reset_pnl=bool(params.get("reset_pnl", False)),
                reset_offer_history=bool(params.get("reset_offer_history", False)),
                reset_counters=bool(params.get("reset_counters", False)),
                source=str(params.get("source") or "api"),
            )

            replaced = aid in self._pending
            self._pending[aid] = req
            # Move to end so coalesced re-requests don't jump the queue.
            self._pending.move_to_end(aid)

            position = list(self._pending.keys()).index(aid) + 1
            slog(
                "PREP_QUEUE",
                f"{'Updated' if replaced else 'Queued'} prep for {aid[:12]}... "
                f"(position={position}, depth={len(self._pending)})",
            )
            return {
                "success": True,
                "status": "queued",
                "asset_id": aid,
                "request_id": req.request_id,
                "position": position,
                "queue_depth": len(self._pending),
                "message": (
                    f"Coin prep queued for this pair (position {position}). "
                    "Another pair's prep is running — yours starts next in fair order."
                ),
            }

    def try_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start immediately if idle; otherwise enqueue.

        Returns status: started | queued | already_running | error.
        """
        aid = _norm_asset(params.get("asset_id"))
        with self._lock:
            if self._current is not None:
                if aid and self._current.asset_id == aid:
                    return {
                        "success": True,
                        "status": "already_running",
                        "asset_id": aid,
                        "message": "Coin prep is already running for this pair.",
                    }
                if not aid:
                    return {
                        "success": True,
                        "status": "already_running",
                        "message": "Coin prep is already running.",
                    }
                return self.enqueue(params)

            if len(aid) != 64:
                # Legacy single-pair: allow start without queue identity.
                req = PrepRequest(
                    asset_id=aid,
                    request_id=str(params.get("request_id") or uuid.uuid4().hex[:10]),
                    coin_multiplier=float(params.get("coin_multiplier", 1.0) or 1.0),
                    reset_pnl=bool(params.get("reset_pnl", False)),
                    reset_offer_history=bool(params.get("reset_offer_history", False)),
                    reset_counters=bool(params.get("reset_counters", False)),
                    source=str(params.get("source") or "api"),
                )
            else:
                req = PrepRequest(
                    asset_id=aid,
                    request_id=str(params.get("request_id") or uuid.uuid4().hex[:10]),
                    coin_multiplier=float(params.get("coin_multiplier", 1.0) or 1.0),
                    reset_pnl=bool(params.get("reset_pnl", False)),
                    reset_offer_history=bool(params.get("reset_offer_history", False)),
                    reset_counters=bool(params.get("reset_counters", False)),
                    source=str(params.get("source") or "api"),
                )

            req.status = "running"
            self._current = req
            launch_params = req.to_params()
            # Merge any extra keys from caller (e.g. full_reset alias already resolved).
            for key, value in params.items():
                launch_params.setdefault(key, value)

        return {
            "success": True,
            "status": "started",
            "asset_id": aid or None,
            "request_id": req.request_id,
            "params": launch_params,
            "message": "Coin prep started",
        }

    def _pick_next_locked(self, skip_asset_id: str = "") -> Optional[PrepRequest]:
        if not self._pending:
            return None
        keys = list(self._pending.keys())
        # Fairness: if the pair that just finished is waiting again and
        # others are waiting too, serve another pair first.
        skip = skip_asset_id or self._last_served
        if skip and skip in self._pending and len(keys) > 1:
            keys = [k for k in keys if k != skip] + [skip]
        chosen = keys[0]
        return self._pending.pop(chosen)

    def complete_current(self, *, failed: bool = False) -> Optional[Dict[str, Any]]:
        """Mark current job done and return params for the next job, if any."""
        with self._lock:
            finished = ""
            if self._current is not None:
                self._current.status = "failed" if failed else "done"
                finished = self._current.asset_id or ""
                slog(
                    "PREP_QUEUE",
                    f"Prep finished for {(finished or '?')[:12]}... "
                    f"failed={failed}; pending={len(self._pending)}",
                )
            self._current = None
            nxt = self._pick_next_locked(skip_asset_id=finished)
            self._last_served = finished
            if nxt is None:
                return None
            nxt.status = "running"
            self._current = nxt
            return nxt.to_params()

    def cancel(
        self,
        *,
        asset_id: Optional[str] = None,
        request_id: Optional[str] = None,
        cancel_running: bool = False,
    ) -> Dict[str, Any]:
        """Cancel queued work. Optionally flag that the running job should die."""
        aid = _norm_asset(asset_id)
        removed = []
        with self._lock:
            if request_id:
                for key, req in list(self._pending.items()):
                    if req.request_id == request_id:
                        removed.append(self._pending.pop(key).to_public())
            elif aid:
                if aid in self._pending:
                    removed.append(self._pending.pop(aid).to_public())
            else:
                removed = [req.to_public() for req in self._pending.values()]
                self._pending.clear()

            running_match = False
            if self._current is not None:
                if request_id and self._current.request_id == request_id:
                    running_match = True
                elif aid and self._current.asset_id == aid:
                    running_match = True
                elif cancel_running and not aid and not request_id:
                    running_match = True

        return {
            "success": True,
            "cancelled_queued": removed,
            "cancel_running": running_match,
            "queue": self.status(),
        }

    def mark_worker_idle(self) -> None:
        """Clear the running slot when no worker is actually active.

        Keeps queued requests. Used when process state says idle but the
        queue still thinks a job is current (e.g. after test teardown or
        a crashed worker that never called complete_current).
        """
        with self._lock:
            self._current = None

    def reset(self) -> None:
        """Clear queue state (used by /coin-prep/reset)."""
        with self._lock:
            self._pending.clear()
            self._current = None


_QUEUE: Optional[PrepQueue] = None
_QUEUE_LOCK = threading.Lock()


def get_prep_queue() -> PrepQueue:
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is None:
            _QUEUE = PrepQueue()
        return _QUEUE
