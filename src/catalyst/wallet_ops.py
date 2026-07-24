"""Process-wide wallet mutation lock for multi-pair trading.

Concurrent BotLoops share one Sage wallet. Mutating RPCs (make/cancel
offer, split, send, etc.) must be serialized to avoid MEMPOOL_CONFLICT
and double-spend races on shared XCH coins.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator


WALLET_OP_LOCK = threading.RLock()

# Sage / wallet endpoints that change chain or mempool state.
MUTATING_ENDPOINTS = frozenset(
    {
        "make_offer",
        "take_offer",
        "cancel_offer",
        "cancel_offers",
        "create_offer_for_ids",
        "send_xch",
        "send_cat",
        "send",
        "split",
        "combine",
        "create_signed_transaction",
        "create_transaction",
        "multi_send",
        "bulk_mint",
        "submit_transaction",
        "push_tx",
    }
)


def is_mutating_endpoint(endpoint: str) -> bool:
    name = str(endpoint or "").strip().lower()
    if not name:
        return False
    if name in MUTATING_ENDPOINTS:
        return True
    # Defensive: anything that looks like a write.
    for token in ("make_", "cancel_", "send_", "split", "combine", "create_", "submit_"):
        if token in name:
            return True
    return False


@contextmanager
def wallet_op_lock(endpoint: str = "") -> Iterator[None]:
    """Acquire the process wallet lock for mutating work."""
    if endpoint and not is_mutating_endpoint(endpoint):
        yield
        return
    with WALLET_OP_LOCK:
        yield
