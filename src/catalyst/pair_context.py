"""Per-thread pair context for concurrent multi-pair trading.

Each BotLoop cycle runs under a PairSnapshot so ambient ``cfg.CAT_*`` /
pair-economics reads resolve to that pair's frozen overlay instead of the
GUI focus slot in global ``cfg``.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterator, Optional


@dataclass
class PairSnapshot:
    """Frozen identity + economics for one running pair."""

    asset_id: str
    wallet_id: Optional[int] = None
    name: str = ""
    ticker_id: str = ""
    decimals: int = 3
    tibet_pair_id: str = ""
    xch_budget_mojos: int = 0
    overlay: Dict[str, str] = field(default_factory=dict)

    def normalized_asset_id(self) -> str:
        return (
            str(self.asset_id or "")
            .strip()
            .lower()
            .replace("0x", "")
        )


_pair_ctx: ContextVar[Optional[PairSnapshot]] = ContextVar(
    "catalyst_pair_ctx", default=None
)

_IDENTITY_ATTRS = {
    "CAT_ASSET_ID": "asset_id",
    "CAT_WALLET_ID": "wallet_id",
    "CAT_NAME": "name",
    "CAT_TICKER_ID": "ticker_id",
    "CAT_DECIMALS": "decimals",
    "TIBET_PAIR_ID": "tibet_pair_id",
}

# Methods / internals that must never go through overlay lookup.
_CFG_PASSTHROUGH = frozenset(
    {
        "reload",
        "update",
        "update_persisted",
        "to_dict",
        "validate",
        "has_pending_restart_changes",
        "clear_pending_restart_changes",
        "get_pending_restart_keys",
    }
)


def get_pair_context() -> Optional[PairSnapshot]:
    return _pair_ctx.get()


def set_pair_context(snapshot: Optional[PairSnapshot]) -> Token:
    return _pair_ctx.set(snapshot)


def reset_pair_context(token: Token) -> None:
    _pair_ctx.reset(token)


@contextmanager
def pair_context(snapshot: Optional[PairSnapshot]) -> Iterator[Optional[PairSnapshot]]:
    token = set_pair_context(snapshot)
    try:
        yield snapshot
    finally:
        reset_pair_context(token)


def _coerce_overlay_value(key: str, raw: Any, template: Any) -> Any:
    if raw is None:
        return template
    if isinstance(template, bool):
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if isinstance(template, int) and not isinstance(template, bool):
        try:
            return int(Decimal(str(raw)))
        except (InvalidOperation, ValueError, TypeError):
            return template
    if isinstance(template, Decimal):
        try:
            return Decimal(str(raw))
        except (InvalidOperation, ValueError, TypeError):
            return template
    if isinstance(template, float):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return template
    return str(raw)


def install_config_overlay_hook() -> None:
    """Patch Config.__getattribute__ once so pair context overlays apply."""
    from config import Config

    if getattr(Config, "_pair_overlay_installed", False):
        return

    original = Config.__getattribute__

    def _getattribute(self, name: str):
        if name.startswith("_") or name in _CFG_PASSTHROUGH:
            return original(self, name)
        ctx = _pair_ctx.get()
        if ctx is None:
            return original(self, name)

        if name in _IDENTITY_ATTRS:
            attr = _IDENTITY_ATTRS[name]
            value = getattr(ctx, attr, None)
            if name == "CAT_ASSET_ID":
                return ctx.normalized_asset_id() or original(self, name)
            if name == "CAT_WALLET_ID":
                if value is None:
                    return original(self, name)
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return original(self, name)
            if name == "CAT_DECIMALS":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return original(self, name)
            return value if value not in (None, "") else original(self, name)

        overlay = ctx.overlay or {}
        if name in overlay:
            try:
                template = original(self, name)
            except AttributeError:
                return overlay[name]
            return _coerce_overlay_value(name, overlay[name], template)

        return original(self, name)

    Config.__getattribute__ = _getattribute  # type: ignore[method-assign]
    Config._pair_overlay_installed = True


def build_snapshot_from_store(
    asset_id: str,
    *,
    active_cat: Optional[Dict[str, Any]] = None,
    cfg: Any = None,
) -> PairSnapshot:
    """Build a PairSnapshot from pair_configs (+ optional active_cat/cfg)."""
    import pair_store

    aid = pair_store._normalize_asset_id(asset_id)
    row = pair_store.get_pair_config(aid) or {}
    overlay = dict(row.get("config") or {})
    # Prefer live cfg capture when this asset is the current focus and has
    # unsaved edits still only in memory.
    if cfg is not None:
        focus = pair_store._normalize_asset_id(getattr(cfg, "CAT_ASSET_ID", None))
        if focus == aid:
            overlay.update(pair_store.capture_pair_overlay_from_cfg(cfg))

    active = active_cat or {}
    budget = 0
    try:
        budget = int(row.get("xch_budget_mojos") or 0)
    except (TypeError, ValueError):
        budget = 0

    wallet_id = active.get("wallet_id")
    if wallet_id is None and cfg is not None:
        wallet_id = getattr(cfg, "CAT_WALLET_ID", None)

    return PairSnapshot(
        asset_id=aid,
        wallet_id=int(wallet_id) if wallet_id is not None else None,
        name=str(row.get("name") or active.get("name") or getattr(cfg, "CAT_NAME", "") or ""),
        ticker_id=str(
            row.get("ticker_id")
            or active.get("ticker_id")
            or getattr(cfg, "CAT_TICKER_ID", "")
            or ""
        ),
        decimals=int(
            row.get("decimals")
            if row.get("decimals") is not None
            else active.get("decimals")
            if active.get("decimals") is not None
            else getattr(cfg, "CAT_DECIMALS", 3)
            or 3
        ),
        tibet_pair_id=str(
            row.get("tibet_pair_id") or getattr(cfg, "TIBET_PAIR_ID", "") or ""
        ),
        xch_budget_mojos=max(0, budget),
        overlay=overlay,
    )
