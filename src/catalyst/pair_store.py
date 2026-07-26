"""Per-pair trading profile persistence and multi-pair overview.

Phase 1: stores a cfg-key overlay keyed by ``cat_asset_id`` so switching the
active CAT restores that pair's economics instead of leaking the previous
pair's spreads / tiers / reserves into the new focus.

Phase 2: ``build_pairs_overview`` merges saved profiles with wallet balances
and open-offer counts for the dashboard Pairs panel.

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
    xch_budget_mojos INTEGER NOT NULL DEFAULT 0,
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
    try:
        conn.execute("SELECT xch_budget_mojos FROM pair_configs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute(
            "ALTER TABLE pair_configs ADD COLUMN xch_budget_mojos INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()


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
    try:
        row = conn.execute(
            """
            SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                   enabled, auto_start, xch_budget_mojos, config_json, updated_at
            FROM pair_configs
            WHERE cat_asset_id = ?
            """,
            (asset_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        # Pre-migration DBs mid-upgrade.
        ensure_pair_configs_schema(conn)
        row = conn.execute(
            """
            SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                   enabled, auto_start, xch_budget_mojos, config_json, updated_at
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
    try:
        rows = conn.execute(
            """
            SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                   enabled, auto_start, xch_budget_mojos, config_json, updated_at
            FROM pair_configs
            ORDER BY updated_at DESC
            """
        ).fetchall()
    except sqlite3.OperationalError:
        ensure_pair_configs_schema(conn)
        rows = conn.execute(
            """
            SELECT cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                   enabled, auto_start, xch_budget_mojos, config_json, updated_at
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
                enabled, auto_start, xch_budget_mojos, config_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, 1, 0, 0, '{}', ?)
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
                    enabled, auto_start, xch_budget_mojos, config_json, updated_at
                ) VALUES (?, '', '', 3, NULL, 1, 0, 0, ?, ?)
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


def get_xch_budget_mojos(asset_id: str) -> int:
    """Return the hard XCH budget (mojos) for a pair."""
    row = get_pair_config(asset_id)
    if not row:
        return 0
    try:
        return max(0, int(row.get("xch_budget_mojos") or 0))
    except (TypeError, ValueError):
        return 0


def set_xch_budget_mojos(asset_id: str, budget_mojos: int) -> bool:
    """Persist a hard XCH budget for a pair (mojos)."""
    asset_id = _normalize_asset_id(asset_id)
    if not asset_id:
        return False
    budget_mojos = max(0, int(budget_mojos or 0))
    from database import get_connection

    conn = get_connection()
    ensure_pair_configs_schema(conn)
    now = _now()
    existing = conn.execute(
        "SELECT cat_asset_id FROM pair_configs WHERE cat_asset_id = ?",
        (asset_id,),
    ).fetchone()
    try:
        if existing:
            conn.execute(
                """
                UPDATE pair_configs
                SET xch_budget_mojos = ?, updated_at = ?
                WHERE cat_asset_id = ?
                """,
                (budget_mojos, now, asset_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO pair_configs (
                    cat_asset_id, ticker_id, name, decimals, tibet_pair_id,
                    enabled, auto_start, xch_budget_mojos, config_json, updated_at
                ) VALUES (?, '', '', 3, NULL, 1, 0, ?, '{}', ?)
                """,
                (asset_id, budget_mojos, now),
            )
        conn.commit()
        return True
    except Exception as exc:
        slog(
            "PAIR_STORE",
            f"Failed to set XCH budget for {asset_id[:12]}...: {exc}",
            level="error",
        )
        return False


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


def build_pairs_overview(
    *,
    focus_asset_id: Optional[str] = None,
    active_cat: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the Phase 2 multi-pair overview payload.

    Merges saved ``pair_configs`` with wallet CAT balances and open-offer
    counts. Safe when the wallet RPC is unreachable — balances simply come
    back empty / zero.
    """
    cfg_focus = None
    try:
        from config import cfg as _cfg

        cfg_focus = getattr(_cfg, "CAT_ASSET_ID", None)
    except Exception:
        cfg_focus = None
    focus = _normalize_asset_id(
        focus_asset_id or (active_cat or {}).get("asset_id") or cfg_focus
    )

    profiles = {row["cat_asset_id"]: row for row in list_pair_configs()}
    offer_counts: Dict[str, Dict[str, int]] = {}
    try:
        from database import count_open_offers_by_cat

        offer_counts = count_open_offers_by_cat() or {}
    except Exception as exc:
        slog("PAIR_STORE", f"open-offer counts unavailable: {exc}", level="warning")

    wallet_cats: Dict[str, Dict[str, Any]] = {}
    xch_balances = {"spendable": 0.0, "total": 0.0}
    try:
        from wallet import get_wallets, get_wallet_balance, WALLET_ID_XCH

        try:
            xch_result = get_wallet_balance(WALLET_ID_XCH)
            if xch_result and xch_result.get("success") is not False:
                wb = xch_result.get("wallet_balance") or xch_result
                xch_balances = {
                    "spendable": float(wb.get("spendable_balance", 0) or 0) / 1e12,
                    "total": float(
                        wb.get("confirmed_wallet_balance", wb.get("balance", 0)) or 0
                    )
                    / 1e12,
                }
        except Exception:
            pass

        wallets_resp = get_wallets() or {}
        wallets = wallets_resp.get("wallets") or []
        if isinstance(wallets_resp, list):
            wallets = wallets_resp
        for w in wallets:
            wtype = w.get("type", 0)
            is_cat = wtype == 6 or str(wtype) == "6" or str(wtype).upper() == "CAT"
            if not is_cat:
                continue
            aid = _normalize_asset_id(
                w.get("asset_id") or w.get("data") or w.get("assetId")
            )
            if not aid:
                continue
            decimals = int(w.get("decimals") or 3)
            scale = 10**decimals
            spendable = 0.0
            total = 0.0
            try:
                bal = get_wallet_balance(int(w.get("id") or w.get("wallet_id") or 0))
                if bal and bal.get("success") is not False:
                    wb = bal.get("wallet_balance") or bal
                    spendable = float(wb.get("spendable_balance", 0) or 0) / scale
                    total = (
                        float(
                            wb.get("confirmed_wallet_balance", wb.get("balance", 0))
                            or 0
                        )
                        / scale
                    )
            except Exception:
                pass
            wallet_cats[aid] = {
                "asset_id": aid,
                "wallet_id": int(w.get("id") or w.get("wallet_id") or 0),
                "name": w.get("name") or aid[:8],
                "ticker_id": w.get("ticker_id") or w.get("ticker") or "",
                "decimals": decimals,
                "balances": {"spendable": spendable, "total": total},
                "in_wallet": True,
            }
    except Exception as exc:
        slog("PAIR_STORE", f"wallet CAT scan unavailable: {exc}", level="warning")

    # Union of profile keys + wallet keys + any asset with open offers.
    asset_ids = set(profiles.keys()) | set(wallet_cats.keys()) | set(offer_counts.keys())
    if focus:
        asset_ids.add(focus)

    pairs: List[Dict[str, Any]] = []
    for aid in asset_ids:
        if not aid or len(aid) != 64:
            continue
        profile = profiles.get(aid) or {}
        wallet = wallet_cats.get(aid) or {}
        counts = offer_counts.get(aid) or {"buy": 0, "sell": 0, "total": 0}
        overlay = profile.get("config") or {}
        has_profile = bool(overlay)
        name = (
            profile.get("name")
            or wallet.get("name")
            or (active_cat or {}).get("name")
            or aid[:8]
        )
        ticker = (
            profile.get("ticker_id")
            or wallet.get("ticker_id")
            or (active_cat or {}).get("ticker_id")
            or ""
        )
        decimals = (
            profile.get("decimals")
            if profile.get("decimals") is not None
            else wallet.get("decimals", 3)
        )
        budget_mojos = 0
        try:
            budget_mojos = int(profile.get("xch_budget_mojos") or 0)
        except (TypeError, ValueError):
            budget_mojos = 0
        used_mojos = 0
        remaining_mojos = budget_mojos
        try:
            from shared_xch_ledger import ledger as _ledger

            used_mojos = _ledger.open_buy_xch_mojos(aid)
            remaining_mojos = max(0, budget_mojos - used_mojos)
            budget_xch = float(_ledger.mojos_to_xch(budget_mojos))
            used_xch = float(_ledger.mojos_to_xch(used_mojos))
            remaining_xch = float(_ledger.mojos_to_xch(remaining_mojos))
        except Exception:
            budget_xch = budget_mojos / 1e12
            used_xch = 0.0
            remaining_xch = budget_xch

        running = False
        try:
            from pair_registry import get_registry

            running = get_registry().is_running(aid)
        except Exception:
            running = False

        pairs.append(
            {
                "asset_id": aid,
                "name": name,
                "ticker_id": ticker,
                "decimals": int(decimals) if decimals is not None else 3,
                "wallet_id": wallet.get("wallet_id")
                or (active_cat or {}).get("wallet_id"),
                "enabled": int(profile.get("enabled", 1) if profile else 1),
                "auto_start": int(profile.get("auto_start", 0) if profile else 0),
                "has_saved_profile": has_profile,
                "is_focus": aid == focus,
                "in_wallet": bool(wallet.get("in_wallet")),
                "running": running,
                "balances": wallet.get("balances")
                or {"spendable": 0.0, "total": 0.0},
                "open_offers": {
                    "buy": int(counts.get("buy", 0)),
                    "sell": int(counts.get("sell", 0)),
                    "total": int(counts.get("total", 0)),
                },
                "xch_budget_mojos": budget_mojos,
                "xch_budget": budget_xch,
                "xch_budget_used": used_xch,
                "xch_budget_remaining": remaining_xch,
                "updated_at": profile.get("updated_at"),
            }
        )

    # Session-scoped realised P&L per pair + aggregate (Phase 4).
    # Uses the same get_stats path as the dashboard / focus PnL tab so the
    # numbers share RUN_HISTORY_CUTOFF and economic-fill filtering.
    since = None
    try:
        import api_server as _api

        since = _api._get_run_history_cutoff() or None
    except Exception:
        since = None

    aggregate_pnl = {
        "realised_pnl_xch": "0",
        "round_trips": 0,
        "total_fills": 0,
        "since": since,
    }
    try:
        from database import get_stats
        from decimal import Decimal as _Dec

        listed_pnl = _Dec("0")
        listed_trips = 0
        listed_fills = 0
        for pair in pairs:
            aid = pair.get("asset_id")
            try:
                stats = get_stats(aid, since=since) or {}
            except Exception:
                stats = {}
            realised = str(stats.get("realised_pnl_xch") or "0")
            trips = int(stats.get("round_trips") or 0)
            fills = int(stats.get("total_fills") or 0)
            pair["realised_pnl_xch"] = realised
            pair["round_trips"] = trips
            pair["total_fills"] = fills
            try:
                listed_pnl += _Dec(str(realised))
            except Exception:
                pass
            listed_trips += trips
            listed_fills += fills

        # Prefer summing listed pairs (what the panel shows). Fall back to an
        # all-fills aggregate when no pairs are listed yet.
        if pairs:
            aggregate_pnl = {
                "realised_pnl_xch": str(listed_pnl),
                "round_trips": listed_trips,
                "total_fills": listed_fills,
                "since": since,
            }
        else:
            all_stats = get_stats(None, since=since) or {}
            aggregate_pnl = {
                "realised_pnl_xch": str(all_stats.get("realised_pnl_xch") or "0"),
                "round_trips": int(all_stats.get("round_trips") or 0),
                "total_fills": int(all_stats.get("total_fills") or 0),
                "since": since,
            }
    except Exception as exc:
        slog("PAIR_STORE", f"pair PnL aggregate unavailable: {exc}", level="warning")
        for pair in pairs:
            pair.setdefault("realised_pnl_xch", "0")
            pair.setdefault("round_trips", 0)
            pair.setdefault("total_fills", 0)

    # Running first, then focus, then profiles with offers, then name.
    def _sort_key(p: Dict[str, Any]):
        return (
            0 if p.get("running") else 1,
            0 if p.get("is_focus") else 1,
            0 if p.get("open_offers", {}).get("total", 0) else 1,
            0 if p.get("has_saved_profile") else 1,
            str(p.get("name") or "").lower(),
        )

    pairs.sort(key=_sort_key)

    ledger_snap = {}
    try:
        from shared_xch_ledger import ledger as _ledger

        ledger_snap = _ledger.snapshot([p["asset_id"] for p in pairs])
    except Exception:
        ledger_snap = {}

    # Physical XCH ownership (prep-claimed trading UTXOs) — complements the
    # soft ledger budget which tracks open-buy exposure.
    xch_ownership: Dict[str, Any] = {}
    try:
        from database import summarize_xch_ownership

        xch_ownership = summarize_xch_ownership() or {}
        owned_pairs = xch_ownership.get("pairs") or {}
        for pair in pairs:
            aid = pair.get("asset_id")
            bucket = owned_pairs.get(aid) or {}
            owned_mojos = int(bucket.get("mojos") or 0)
            pair["xch_owned_mojos"] = owned_mojos
            pair["xch_owned"] = owned_mojos / 1e12
            pair["xch_owned_coins"] = int(bucket.get("coins") or 0)
    except Exception as exc:
        slog("PAIR_STORE", f"XCH ownership summary unavailable: {exc}", level="warning")
        xch_ownership = {}
        for pair in pairs:
            pair.setdefault("xch_owned_mojos", 0)
            pair.setdefault("xch_owned", 0.0)
            pair.setdefault("xch_owned_coins", 0)

    return {
        "success": True,
        "focus_asset_id": focus or None,
        "xch": xch_balances,
        "pairs": pairs,
        "pnl": aggregate_pnl,
        "max_concurrent_pairs": 4,
        "xch_ledger": ledger_snap,
        "xch_ownership": xch_ownership,
    }
