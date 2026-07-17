"""Per-pair trading profile persistence (Phase 1 of multi-pair).

Stores a cfg-key overlay keyed by ``cat_asset_id`` so switching the active
CAT restores that pair's economics instead of leaking the previous pair's
spreads / tiers / reserves into the new focus.

Process-global keys (Sage, ``XCH_RESERVE``, ``LOOP_SECONDS``, ``DRY_RUN``,
fee pool, shared API endpoints) are never swapped by this module.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from super_log import slog


# Keys captured/restored per CAT. Intersected with cfg._UPDATABLE_KEYS at
# apply time. Intentionally excludes process-global capital floor XCH_RESERVE
# and CAT_ASSET_ID (identity is handled separately on select).
PAIR_ECONOMICS_KEYS = frozenset(
    {
        # Identity metadata (optional in JSON; columns are source of truth)
        "CAT_TICKER_ID",
        "CAT_NAME",
        "CAT_DECIMALS",
        "TIBET_PAIR_ID",
        # Liquidity / sides
        "LIQUIDITY_MODE",
        "ENABLE_BUY",
        "ENABLE_SELL",
        # Spreads
        "SPREAD_BPS",
        "BASE_SPREAD_BPS",
        "MIN_SPREAD_BPS",
        "MAX_SPREAD_BPS",
        "MIN_EDGE_BPS",
        "DYNAMIC_SPREAD_ENABLED",
        "VOLATILITY_WINDOW_HOURS",
        "DYNAMIC_FILL_RATE_START_PER_HOUR",
        "DYNAMIC_FILL_RATE_FULL_PER_HOUR",
        "DYNAMIC_FILL_RATE_MAX_BPS",
        # Pricing
        "PRICE_STRATEGY",
        "TIBET_WEIGHT",
        "ARB_ALERT_THRESHOLD_BPS",
        # Hard rails / safety
        "HARD_MIN_PRICE_XCH",
        "HARD_MAX_PRICE_XCH",
        "MIN_MID",
        "MAX_MID",
        "DYNAMIC_LIMIT_PCT",
        "MAX_STEP_CHANGE_FRACTION",
        "TIBET_SHOCK_CANCEL_TRIGGER_PCT",
        "TIBET_SHOCK_CANCEL_MID_PCT",
        "TIBET_SHOCK_CANCEL_OUTER_PCT",
        # Offer book / trade size
        "MAX_ACTIVE_BUY",
        "MAX_ACTIVE_SELL",
        "MAX_ACTIVE_BUY_OFFERS",
        "MAX_ACTIVE_SELL_OFFERS",
        "DEFAULT_TRADE_XCH",
        "MIN_TRADE_XCH",
        "MAX_TRADE_XCH",
        # Requote
        "AUTO_REQUOTE",
        "REQUOTE_BPS",
        "REQUOTE_COOLDOWN_SECS",
        "REQUOTE_BATCH_SIZE",
        "REQUOTE_COIN_FREE_WAIT",
        # Inventory
        "INVENTORY_ENABLED",
        "SKEW_INTENSITY",
        "MAX_POSITION_XCH",
        # Toxicity
        "MARKET_TOXICITY_ENABLED",
        "TOXICITY_PROTECTION_LEVEL",
        "TOXICITY_WIDEN_START",
        "TOXICITY_ELEVATED_START",
        "TOXICITY_THROTTLE_START",
        "TOXICITY_CANCEL_START",
        "TOXICITY_THROTTLE_SECS",
        "TOXICITY_DECAY_PER_LOOP",
        "TOXICITY_MAX_SPREAD_MULTIPLIER",
        "TOXICITY_MIN_THROTTLE_SIGNALS",
        "TOXICITY_CANCEL_ENABLED",
        # Tiers
        "TIER_ENABLED",
        "BUY_LADDER_REVERSED",
        "INNER_SIZE_XCH",
        "MID_SIZE_XCH",
        "OUTER_SIZE_XCH",
        "EXTREME_SIZE_XCH",
        "BUY_INNER_SIZE_XCH",
        "BUY_MID_SIZE_XCH",
        "BUY_OUTER_SIZE_XCH",
        "BUY_EXTREME_SIZE_XCH",
        "SELL_INNER_SIZE_XCH",
        "SELL_MID_SIZE_XCH",
        "SELL_OUTER_SIZE_XCH",
        "SELL_EXTREME_SIZE_XCH",
        "INNER_TIER_COUNT",
        "MID_TIER_COUNT",
        "OUTER_TIER_COUNT",
        "EXTREME_TIER_COUNT",
        "BUY_INNER_TIER_COUNT",
        "BUY_MID_TIER_COUNT",
        "BUY_OUTER_TIER_COUNT",
        "BUY_EXTREME_TIER_COUNT",
        "SELL_INNER_TIER_COUNT",
        "SELL_MID_TIER_COUNT",
        "SELL_OUTER_TIER_COUNT",
        "SELL_EXTREME_TIER_COUNT",
        "INNER_TIER_SPARE_COUNT",
        "MID_TIER_SPARE_COUNT",
        "OUTER_TIER_SPARE_COUNT",
        "EXTREME_TIER_SPARE_COUNT",
        "BUY_INNER_TIER_SPARE_COUNT",
        "BUY_MID_TIER_SPARE_COUNT",
        "BUY_OUTER_TIER_SPARE_COUNT",
        "BUY_EXTREME_TIER_SPARE_COUNT",
        "SELL_INNER_TIER_SPARE_COUNT",
        "SELL_MID_TIER_SPARE_COUNT",
        "SELL_OUTER_TIER_SPARE_COUNT",
        "SELL_EXTREME_TIER_SPARE_COUNT",
        # Tier replenishment / pace
        "TIER_TRIGGER_PCT_INNER",
        "TIER_TRIGGER_PCT_MID",
        "TIER_TRIGGER_PCT_OUTER",
        "TIER_TRIGGER_PCT_EXTREME",
        "TIER_TRIGGER_PCT_SNIPER",
        "TIER_TRIGGER_PCT_FEES",
        "TIER_TRIGGER_PACE_SCALE",
        "TIER_DRIP_PCT",
        "TOPUP_SLOW_PCT",
        "TOPUP_NORMAL_PCT",
        "TOPUP_BUSY_PCT",
        "FILLS_PER_HOUR_BUSY",
        "FILLS_PER_HOUR_SLOW",
        # Capital (CAT + Phase-1 XCH slice precursor; not XCH_RESERVE)
        "CAT_RESERVE",
        "TOPUP_POOL_PCT",
        "TOPUP_POOL_XCH",
        "TOPUP_POOL_CAT",
        "CAT_COIN_SIZE",
        "CAT_TARGET_COINS",
        "XCH_COIN_SIZE",
        "XCH_TARGET_COINS",
        "ENABLE_COIN_PREP",
        "COIN_PREP_MULTIPLIER",
        "COIN_PREP_HEADROOM_PCT",
        "COIN_MAX_SIZE_RATIO",
        "COIN_OVERSIZE_FALLBACK_RATIO",
        # Sniper / boost / gap-close
        "SNIPER_ENABLED",
        "SNIPER_SIZE_XCH",
        "SNIPER_PREP_COUNT",
        "SNIPER_EXPIRY_SECS",
        "SNIPER_COOLDOWN_SECS",
        "SNIPER_CONFIRM_SECS",
        "SNIPER_LINGER_SECS",
        "SNIPER_POLL_SECS",
        "SNIPER_BUFFER_BPS",
        "SNIPER_TOP_BOOK_BPS",
        "SNIPER_RETRY_BACKOFF_BPS",
        "SNIPER_MAIN_BOOK_GUARD_BPS",
        "SNIPER_MIN_GAP_BPS",
        "SNIPER_REARM_PRICE_MOVE_BPS",
        "SNIPER_REARM_GAP_MOVE_BPS",
        "SNIPER_FLOOR_TIGHTEN_ENABLED",
        "SNIPER_FLOOR_TIGHTEN_STEP_BPS",
        "SNIPER_FLOOR_TIGHTEN_COOLDOWN_SECS",
        "SNIPER_FLOOR_SAFETY_BPS",
        "BOOST_SIZE_XCH",
        "BOOST_EXPIRY_SECS",
        "BOOST_SPREAD_BPS",
        "GAP_CLOSE_START_PCT",
        "GAP_CLOSE_STEP_PCT",
        "GAP_CLOSE_SAFETY_BUFFER_BPS",
        "GAP_CLOSE_STEP_COOLDOWN_SECS",
        "GAP_CLOSE_CONVERGENCE_SECS",
        "GAP_CLOSE_CONVERGENCE_STEP_PCT",
        "GAP_CLOSE_CASCADE_WAIT_SECS",
        "GAP_CLOSE_CASCADE_BATCH_SIZE",
        # Competitor / offer lifecycle
        "COMPETITOR_AWARE_ENABLED",
        "DBX_MAX_SPREAD_BPS",
        "OFFER_EXPIRY_SECS",
        "OFFER_STAGGER_SECS",
        "OFFER_REFRESH_BEFORE",
        "FILL_PROTECT_SECS",
    }
)

# Never restore these from a pair overlay (process-global or select-owned).
_APPLY_SKIP_KEYS = frozenset(
    {
        "XCH_RESERVE",
        "CAT_ASSET_ID",
        "DRY_RUN",
        "LOOP_SECONDS",
        # Always re-resolved after select; identity columns hold last known id.
        "TIBET_PAIR_ID",
    }
)

PAIR_CONFIGS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS pair_configs (
    cat_asset_id    TEXT PRIMARY KEY,
    ticker_id       TEXT,
    name            TEXT,
    decimals        INTEGER NOT NULL DEFAULT 3,
    tibet_pair_id   TEXT,
    enabled         INTEGER NOT NULL DEFAULT 1,
    auto_start      INTEGER NOT NULL DEFAULT 0,
    config_json     TEXT NOT NULL DEFAULT '{}',
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pair_configs_updated ON pair_configs(updated_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_asset_id(asset_id: Optional[str]) -> str:
    raw = str(asset_id or "").strip().lower().replace("0x", "")
    if len(raw) != 64 or any(c not in "0123456789abcdef" for c in raw):
        return ""
    return raw


def _cfg_value_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def ensure_pair_configs_schema(conn: sqlite3.Connection) -> None:
    """Create pair_configs if missing. Safe to call repeatedly."""
    conn.executescript(PAIR_CONFIGS_SCHEMA_SQL)


def capture_pair_overlay_from_cfg(cfg: Any) -> Dict[str, str]:
    """Snapshot pair-economics keys from the live cfg object."""
    overlay: Dict[str, str] = {}
    for key in PAIR_ECONOMICS_KEYS:
        if key in _APPLY_SKIP_KEYS and key != "TIBET_PAIR_ID":
            # Still capture TIBET_PAIR_ID for identity column sync; skip
            # other process-global keys entirely.
            continue
        if key == "XCH_RESERVE" or key == "CAT_ASSET_ID":
            continue
        if not hasattr(cfg, key):
            continue
        overlay[key] = _cfg_value_to_str(getattr(cfg, key))
    return overlay


def apply_pair_overlay_to_cfg(
    cfg: Any, overlay: Optional[Dict[str, Any]], *, source: str = "pair_switch"
) -> List[str]:
    """Apply a saved overlay into .env + in-memory cfg.

    Uses a single lock + reload so pair switches stay fast. Returns the list
    of keys that were written.
    """
    if not isinstance(overlay, dict) or not overlay:
        return []

    from dotenv import set_key
    import config as config_mod

    updatable = getattr(cfg, "_UPDATABLE_KEYS", set()) or set()
    env_path = getattr(config_mod, "_ENV_PATH", None)
    if not env_path:
        return []

    applied: List[str] = []
    with cfg._lock:
        for key, value in overlay.items():
            key = str(key)
            if key not in PAIR_ECONOMICS_KEYS:
                continue
            if key in _APPLY_SKIP_KEYS:
                continue
            if key not in updatable:
                continue
            set_key(env_path, key, _cfg_value_to_str(value))
            applied.append(key)
        if applied:
            cfg.reload()

    if applied:
        slog(
            "PAIR_STORE",
            f"Applied {len(applied)} pair-profile keys (source={source})",
            {"keys": applied[:20], "source": source},
            level="info",
        )
        try:
            from database import log_event

            log_event(
                "info",
                "pair_profile_applied",
                f"Restored {len(applied)} settings from pair profile ({source})",
            )
        except Exception:
            pass
    return applied


def get_pair_config(asset_id: str) -> Optional[Dict[str, Any]]:
    """Return a pair_configs row (with parsed config_json) or None."""
    asset_id = _normalize_asset_id(asset_id)
    if not asset_id:
        return None
    from database import get_connection

    conn = get_connection()
    row = conn.execute(
        """
        SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
               enabled, auto_start, config_json, updated_at
        FROM pair_configs
        WHERE cat_asset_id = ?
        """,
        (asset_id,),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    try:
        parsed = json.loads(data.get("config_json") or "{}")
        if not isinstance(parsed, dict):
            parsed = {}
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    data["config"] = parsed
    return data


def list_pair_configs() -> List[Dict[str, Any]]:
    """List all saved pair profiles (identity + flags; config parsed)."""
    from database import get_connection

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
               enabled, auto_start, config_json, updated_at
        FROM pair_configs
        ORDER BY updated_at DESC
        """
    ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        try:
            parsed = json.loads(data.get("config_json") or "{}")
            if not isinstance(parsed, dict):
                parsed = {}
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        data["config"] = parsed
        out.append(data)
    return out


def upsert_pair_identity(
    asset_id: str,
    *,
    name: Optional[str] = None,
    ticker_id: Optional[str] = None,
    decimals: Optional[int] = None,
    tibet_pair_id: Optional[str] = None,
) -> bool:
    """Ensure a pair_configs row exists and update identity columns."""
    asset_id = _normalize_asset_id(asset_id)
    if not asset_id:
        return False
    from database import get_connection

    conn = get_connection()
    existing = conn.execute(
        "SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id, "
        "config_json FROM pair_configs WHERE cat_asset_id = ?",
        (asset_id,),
    ).fetchone()
    now = _now()
    if existing:
        conn.execute(
            """
            UPDATE pair_configs
            SET ticker_id = COALESCE(?, ticker_id),
                name = COALESCE(?, name),
                decimals = COALESCE(?, decimals),
                tibet_pair_id = COALESCE(?, tibet_pair_id),
                updated_at = ?
            WHERE cat_asset_id = ?
            """,
            (
                ticker_id,
                name,
                int(decimals) if decimals is not None else None,
                tibet_pair_id,
                now,
                asset_id,
            ),
        )
    else:
        conn.execute(
            """
            INSERT INTO pair_configs (
                cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                enabled, auto_start, config_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 0, '{}', ?)
            """,
            (
                asset_id,
                ticker_id or "",
                name or "",
                int(decimals) if decimals is not None else 3,
                tibet_pair_id,
                now,
            ),
        )
    conn.commit()
    return True


def save_pair_overlay(asset_id: str, overlay: Dict[str, Any]) -> bool:
    """Replace config_json for an asset (creates the row if needed)."""
    asset_id = _normalize_asset_id(asset_id)
    if not asset_id:
        return False
    if not isinstance(overlay, dict):
        return False

    cleaned: Dict[str, str] = {}
    for key, value in overlay.items():
        key = str(key)
        if key not in PAIR_ECONOMICS_KEYS:
            continue
        if key in ("XCH_RESERVE", "CAT_ASSET_ID"):
            continue
        cleaned[key] = _cfg_value_to_str(value)

    from database import get_connection

    conn = get_connection()
    now = _now()
    payload = json.dumps(cleaned, separators=(",", ":"), sort_keys=True)
    existing = conn.execute(
        "SELECT cat_asset_id FROM pair_configs WHERE cat_asset_id = ?",
        (asset_id,),
    ).fetchone()
    try:
        if existing:
            conn.execute(
                """
                UPDATE pair_configs
                SET config_json = ?, updated_at = ?
                WHERE cat_asset_id = ?
                """,
                (payload, now, asset_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO pair_configs (
                    cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                    enabled, auto_start, config_json, updated_at
                ) VALUES (?, '', '', 3, NULL, 1, 0, ?, ?)
                """,
                (asset_id, payload, now),
            )
        conn.commit()
    except Exception as exc:
        slog(
            "PAIR_STORE",
            f"Failed to save pair overlay for {asset_id[:12]}...: {exc}",
            level="error",
        )
        return False
    return True


def persist_current_pair_overlay(cfg: Any) -> bool:
    """Capture live cfg economics for the current CAT_ASSET_ID."""
    asset_id = _normalize_asset_id(getattr(cfg, "CAT_ASSET_ID", None))
    if not asset_id:
        return False
    overlay = capture_pair_overlay_from_cfg(cfg)
    ok = save_pair_overlay(asset_id, overlay)
    if ok:
        upsert_pair_identity(
            asset_id,
            name=getattr(cfg, "CAT_NAME", None) or None,
            ticker_id=getattr(cfg, "CAT_TICKER_ID", None) or None,
            decimals=getattr(cfg, "CAT_DECIMALS", None),
            tibet_pair_id=getattr(cfg, "TIBET_PAIR_ID", None) or None,
        )
    return ok
