"""Structural checks for the full-app QA scenario matrix.

These tests do not validate trading behavior. They keep the scenario matrix
usable as a living test contract: IDs must stay unique, statuses must be from
the known set, and the highest-risk scenarios must not disappear during edits.
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "testing" / "full_app_scenario_matrix.md"


def _matrix_text() -> str:
    return MATRIX.read_text(encoding="utf-8")


def _scenario_ids(text: str) -> list[str]:
    return re.findall(r"^\|\s*([A-Z]+-\d{2})\s*\|", text, flags=re.MULTILINE)


def test_scenario_matrix_exists_and_has_unique_ids():
    text = _matrix_text()
    ids = _scenario_ids(text)

    assert len(ids) >= 80
    assert len(ids) == len(set(ids))


def test_scenario_matrix_uses_known_status_values():
    text = _matrix_text()
    allowed = {"covered", "partial", "gap", "live-only", "unknown"}
    statuses = re.findall(
        r"\|\s*(covered|partial|gap|live-only|unknown)\s*\|",
        text,
    )

    assert statuses
    assert set(statuses).issubset(allowed)


def test_scenario_matrix_keeps_high_risk_flows():
    text = _matrix_text()
    ids = set(_scenario_ids(text))

    required = {
        "MODE-02",  # buy-only
        "MODE-03",  # sell-only
        "PREP-07",  # cancel-confirm-before-coin-combine race
        "PRICE-04",  # whipsaw while cancels pending
        "FILL-08",  # external CAT deposit
        "COIN-04",  # topup pool empty guidance
        "COIN-10",  # reduced ladder when funds are low
        "REC-04",  # shutdown must not close Sage
        "UX-07",  # coin prep guidance only when appropriate
    }

    assert required.issubset(ids)
