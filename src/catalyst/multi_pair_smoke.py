"""Multi-pair readiness checks + live smoke checklist.

This module does **not** talk to Sage by default. Use it to:

1. Validate DB-level ownership / shared-pool invariants after prep
   (``verify_ownership_isolation``, ``verify_shared_pools``).
2. Print a concrete live 2-pair smoke checklist for an operator with
   Sage running (``live_smoke_checklist`` / ``python -m multi_pair_smoke``).

Live smoke still requires the operator's wallet — the cloud agent cannot
drive Sage for you. Run the checklist on the desktop app machine after
pulling this branch.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _norm_asset(asset_id: Optional[str]) -> str:
    aid = str(asset_id or "").strip().lower().replace("0x", "")
    return aid if len(aid) == 64 else ""


def verify_ownership_isolation(
    asset_a: str,
    asset_b: str,
    *,
    require_a_owned: bool = True,
) -> Dict[str, Any]:
    """Check that pair B cannot see pair A's owned XCH trading coins.

    Returns a result dict with ``ok`` and human-readable ``issues``.
    """
    from database import (
        get_foreign_owned_xch_coin_ids,
        get_free_coins,
        get_xch_coin_owners,
        norm_coin_id,
    )

    a = _norm_asset(asset_a)
    b = _norm_asset(asset_b)
    issues: List[str] = []
    if not a or not b:
        return {"ok": False, "issues": ["both asset ids must be 64-hex"], "owners": {}}
    if a == b:
        return {"ok": False, "issues": ["asset ids must differ"], "owners": {}}

    owners = get_xch_coin_owners()
    a_owned = {cid for cid, oid in owners.items() if oid == a}
    b_owned = {cid for cid, oid in owners.items() if oid == b}

    if require_a_owned and not a_owned:
        issues.append(f"pair A ({a[:12]}...) has no owned XCH trading coins yet")

    foreign_for_b = get_foreign_owned_xch_coin_ids(b)
    leaked = a_owned - foreign_for_b
    if leaked:
        issues.append(
            f"pair A's owned coins missing from B's foreign set: {len(leaked)}"
        )

    free_b = get_free_coins("xch", owner_asset_id=b)
    free_b_ids = {norm_coin_id(c.get("coin_id")) for c in free_b}
    visible_a = a_owned & free_b_ids
    if visible_a:
        issues.append(
            f"pair B free-coin query can see {len(visible_a)} of A's owned coins"
        )

    return {
        "ok": not issues,
        "issues": issues,
        "owners": {
            "a_owned": len(a_owned),
            "b_owned": len(b_owned),
            "foreign_for_b": len(foreign_for_b),
        },
    }


def verify_shared_pools(*, min_fees: int = 0, min_sniper: int = 0) -> Dict[str, Any]:
    """Check unowned shared fee/sniper inventory is present and unowned."""
    from database import count_shared_pool_xch_by_tier, get_xch_coin_owners, norm_coin_id

    existing = count_shared_pool_xch_by_tier()
    issues: List[str] = []
    if min_fees and int(existing.get("fees", 0) or 0) < min_fees:
        issues.append(
            f"shared fees have {existing.get('fees', 0)} < required {min_fees}"
        )
    if min_sniper and int(existing.get("sniper", 0) or 0) < min_sniper:
        issues.append(
            f"shared sniper have {existing.get('sniper', 0)} < required {min_sniper}"
        )

    # Shared-pool coin ids must not appear in the ownership map.
    owners = get_xch_coin_owners()
    from database import get_shared_pool_xch_coin_ids

    shared_ids = get_shared_pool_xch_coin_ids()
    owned_shared = {cid for cid in shared_ids if cid in owners}
    if owned_shared:
        issues.append(
            f"{len(owned_shared)} shared-pool coin(s) incorrectly have owner_asset_id"
        )

    return {
        "ok": not issues,
        "issues": issues,
        "existing": existing,
        "shared_coins": len(shared_ids),
        "mistagged": [norm_coin_id(c) for c in list(owned_shared)[:5]],
    }


def verify_protected_from_prep(owner_asset_id: str) -> Dict[str, Any]:
    """Sanity-check the protect-set used by selective physical prep."""
    from database import (
        get_foreign_owned_xch_coin_ids,
        get_shared_pool_xch_coin_ids,
        get_xch_coins_protected_from_prep,
    )

    owner = _norm_asset(owner_asset_id)
    issues: List[str] = []
    if not owner:
        return {"ok": False, "issues": ["owner_asset_id must be 64-hex"], "protected": 0}

    protected = get_xch_coins_protected_from_prep(owner)
    foreign = get_foreign_owned_xch_coin_ids(owner)
    shared = get_shared_pool_xch_coin_ids()
    if not foreign.issubset(protected):
        issues.append("foreign-owned coins missing from protect set")
    if not shared.issubset(protected):
        issues.append("shared-pool coins missing from protect set")
    return {
        "ok": not issues,
        "issues": issues,
        "protected": len(protected),
        "foreign": len(foreign),
        "shared": len(shared),
    }


def live_smoke_checklist(
    asset_a: Optional[str] = None,
    asset_b: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Return the operator steps for a live 2-pair Sage smoke."""
    a = _norm_asset(asset_a) or "<ASSET_A_64HEX>"
    b = _norm_asset(asset_b) or "<ASSET_B_64HEX>"
    return [
        {
            "step": "1",
            "action": "Backup / note current XCH coin inventory (GUI Coins tab or logs)",
        },
        {
            "step": "2",
            "action": f"Smart Settings + Coin Prep for pair A ({a[:12]}...), set XCH budget",
        },
        {
            "step": "3",
            "action": "Start pair A only; confirm buy/sell ladders and fee pool healthy",
        },
        {
            "step": "4",
            "action": (
                "Record pair A owned XCH via GET /api/pairs → pairs[].xch_owned_coins "
                "and xch_ownership.pairs"
            ),
        },
        {
            "step": "5",
            "action": f"Stop pair A (leave offers resting). Queue Coin Prep for pair B ({b[:12]}...)",
        },
        {
            "step": "6",
            "action": (
                "During/after B prep: confirm logs show protected foreign/shared coins "
                "and 'Shared fees/sniper … skipping recreate' when pools already exist"
            ),
        },
        {
            "step": "7",
            "action": (
                "Re-check /api/pairs: pair A xch_owned_coins unchanged; "
                "shared fees_coins not zeroed; pair B has its own owned slice"
            ),
        },
        {
            "step": "8",
            "action": "Start pair B; confirm both pairs can run within budgets (incremental)",
        },
        {
            "step": "9",
            "action": (
                "Optional: python -c \"from multi_pair_smoke import *; "
                f"print(verify_ownership_isolation('{a}', '{b}'))\""
            ),
        },
    ]


def format_checklist(steps: Optional[List[Dict[str, str]]] = None) -> str:
    lines = ["# Multi-pair live smoke checklist", ""]
    for row in steps or live_smoke_checklist():
        lines.append(f"{row['step']}. {row['action']}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Multi-pair smoke helpers")
    parser.add_argument("--checklist", action="store_true", help="Print live smoke steps")
    parser.add_argument("--asset-a", default="", help="Pair A asset id (64 hex)")
    parser.add_argument("--asset-b", default="", help="Pair B asset id (64 hex)")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run DB ownership/shared-pool checks (needs local Catalyst DB)",
    )
    parser.add_argument("--min-fees", type=int, default=0)
    parser.add_argument("--min-sniper", type=int, default=0)
    args = parser.parse_args(argv)

    if args.checklist or not args.verify:
        print(format_checklist(live_smoke_checklist(args.asset_a, args.asset_b)))

    if args.verify:
        out = {
            "shared_pools": verify_shared_pools(
                min_fees=args.min_fees, min_sniper=args.min_sniper
            ),
        }
        if args.asset_a and args.asset_b:
            out["ownership"] = verify_ownership_isolation(args.asset_a, args.asset_b)
            out["protected_b"] = verify_protected_from_prep(args.asset_b)
        print(json.dumps(out, indent=2))
        oks = [v.get("ok", True) for v in out.values() if isinstance(v, dict)]
        return 0 if all(oks) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
