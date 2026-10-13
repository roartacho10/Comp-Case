"""Cost rules of the intervention catalogue (data/interventions.csv), in one place.

- raise_to_market: salary adjustment that brings the person to a target share of the market median, with a
  minimum raise (premises cost.raise_target_compa and cost.raise_min_share). Paid every year while the person stays.
- fixed: a fixed reference cost per case (premise in cost_key), paid once.
"""

from __future__ import annotations

import numpy as np

from src.assumptions import Assumptions

RAISE_RULE = "raise_to_market"
FIXED_RULE = "fixed"


def _row(a: Assumptions, intervention: str):
    return a.interventions.set_index("intervention").loc[intervention]


def is_recurring(a: Assumptions, intervention: str) -> bool:
    return _row(a, intervention)["cost_rule"] == RAISE_RULE


def annual_cost(a: Assumptions, intervention: str, salary, median):
    """Cost of the intervention per year (recurring) or per case (fixed). Works on numbers or arrays."""
    row = _row(a, intervention)
    if row["cost_rule"] == RAISE_RULE:
        to_target = a.num("cost.raise_target_compa") * np.asarray(median, dtype=float) - np.asarray(salary, dtype=float)
        minimum = a.num(row["cost_key"]) * np.asarray(salary, dtype=float)
        return np.maximum(to_target, minimum)
    if row["cost_rule"] == FIXED_RULE:
        return a.num(row["cost_key"]) + 0 * np.asarray(salary, dtype=float)
    raise ValueError(f"Regra de custo desconhecida em data/interventions.csv: {row['cost_rule']}")


def reference_costs(a: Assumptions) -> dict[str, float]:
    """Fixed reference costs above zero (e.g. carreira e projeto), used to label estimated totals."""
    inter = a.interventions
    fixed = inter[inter["cost_rule"] == FIXED_RULE]
    return {r["intervention"]: a.num(r["cost_key"]) for _, r in fixed.iterrows() if a.num(r["cost_key"]) > 0}
