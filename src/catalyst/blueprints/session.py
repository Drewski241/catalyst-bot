"""Session lifecycle routes: fresh-start and resume-chosen.

Two small routes that mediate between the resume-modal on the GUI and
the run-history cutoff bookkeeping in api_server. Delegates to the
session helpers (`_reset_fresh_run_session`, `_fresh_start_set/clear`)
that still live in api_server since they touch lots of module state.

Start Fresh also releases multi-pair XCH ownership tags and pair budgets
so Smart Settings / coin prep can reallocate reshapeable inventory.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

import api_server
from database import log_event


bp = Blueprint("session", __name__)


def _release_shared_xch_for_fresh_start() -> dict:
    """Clear trading-tier ownership + pair budgets for a clean reallocation."""
    out = {
        "ownership_cleared_coins": 0,
        "ownership_cleared_mojos": 0,
        "budgets_cleared_pairs": 0,
    }
    try:
        from database import clear_all_xch_trading_ownership

        own = clear_all_xch_trading_ownership() or {}
        out["ownership_cleared_coins"] = int(own.get("cleared_coins") or 0)
        out["ownership_cleared_mojos"] = int(own.get("cleared_mojos") or 0)
    except Exception as exc:
        log_event(
            "warning",
            "session_fresh_start_ownership",
            f"Could not clear XCH ownership: {exc}",
        )
    try:
        from pair_store import clear_all_xch_budgets

        budgets = clear_all_xch_budgets() or {}
        out["budgets_cleared_pairs"] = int(budgets.get("pairs_cleared") or 0)
    except Exception as exc:
        log_event(
            "warning",
            "session_fresh_start_budgets",
            f"Could not clear pair XCH budgets: {exc}",
        )
    return out


@bp.route("/api/session/fresh-start", methods=["POST"])
def api_session_fresh_start():
    """Begin a brand new run without carrying forward old session state.

    Body (optional JSON):
      - release_xch (bool, default True): clear trading-tier owner tags and
        zero all pair XCH budgets so the next Smart Settings/coin-prep pass
        can claim reshapeable inventory again.
      - cancel_open_offers (bool, default False): mark DB open offers
        cancelled (does not cancel on-chain Sage/Dexie offers).
    """
    try:
        body = request.get_json(silent=True) or {}
        release_xch = True if not isinstance(body, dict) else bool(
            body.get("release_xch", True)
        )
        cancel_open_offers = bool(
            isinstance(body, dict) and body.get("cancel_open_offers", False)
        )

        payload = api_server._reset_fresh_run_session(
            clear_coins=False,
            clear_price_history=False,
            clear_inventory=False,
            cancel_open_offers=cancel_open_offers,
            reason="session_fresh_start",
        )
        release = {}
        if release_xch:
            release = _release_shared_xch_for_fresh_start()
            payload.update(release)
            if release.get("ownership_cleared_coins") or release.get(
                "budgets_cleared_pairs"
            ):
                log_event(
                    "info",
                    "session_fresh_start_xch_released",
                    "Start Fresh released XCH ownership/budgets for reallocation",
                    release,
                )

        # Persist the choice so check-resume returns can_resume=False on the
        # next page load, even though the old live offers may still be in Sage.
        # Cleared automatically when the bot starts a new run.
        api_server._fresh_start_set()
        return jsonify(
            {
                "success": True,
                "message": (
                    "Fresh run session started"
                    + (
                        " — XCH ownership and pair budgets cleared for reallocation"
                        if release_xch
                        else ""
                    )
                ),
                "release_xch": release_xch,
                **api_server._serialize_dict(payload),
            }
        )
    except Exception as e:
        log_event(
            "warning",
            "session_fresh_start_failed",
            f"Failed to reset fresh run session: {e}",
        )
        return api_server._api_exception(request.path)


@bp.route("/api/session/resume-chosen", methods=["POST"])
def api_session_resume_chosen():
    """User explicitly chose 'Load Previous Session' — clear the fresh-start flag."""
    api_server._fresh_start_clear()
    return jsonify({"success": True})
