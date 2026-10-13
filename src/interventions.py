"""Cost rules of the intervention catalogue (data/interventions.csv), in one place.

- raise_to_market: salary adjustment that brings the person to a target share of the market median, with a
  minimum raise (premises cost.raise_target_compa and cost.raise_min_share). Paid every year while the person stays.
- manager_hours: hours of the decision maker's time (premise in cost_key) at their hourly cost, paid once.
- fixed: a fixed cost per case (premise in cost_key), paid once.

Also the cost of losing someone (replacement), which grows with tenure.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import Assumptions

RAISE_RULE = "raise_to_market"
FIXED_RULE = "fixed"
HOURS_RULE = "manager_hours"


def _row(a: Assumptions, intervention: str):
    return a.interventions.set_index("intervention").loc[intervention]


def is_recurring(a: Assumptions, intervention: str) -> bool:
    return _row(a, intervention)["cost_rule"] == RAISE_RULE


def fallback_hourly(a: Assumptions, country_factor=1.0):
    """Hourly cost of a typical manager (market median for managers), when the decision maker's own cost is unknown."""
    return a.num("market.median.Gestor") * np.asarray(country_factor, dtype=float) / a.num("general.work_hours_per_year")


def hours(a: Assumptions, intervention: str) -> float | None:
    """Hours of the decision maker's time the intervention takes, if its cost is counted in hours."""
    row = _row(a, intervention)
    return a.num(row["cost_key"]) if row["cost_rule"] == HOURS_RULE else None


def annual_cost(a: Assumptions, intervention: str, salary, median, hourly=None):
    """Cost of the intervention per year (recurring) or per case (one-off). Works on numbers or arrays.
    `hourly` is the decision maker's cost per hour (a typical manager's when not given)."""
    row = _row(a, intervention)
    if row["cost_rule"] == RAISE_RULE:
        to_target = a.num("cost.raise_target_compa") * np.asarray(median, dtype=float) - np.asarray(salary, dtype=float)
        minimum = a.num(row["cost_key"]) * np.asarray(salary, dtype=float)
        return np.maximum(to_target, minimum)
    if row["cost_rule"] == HOURS_RULE:
        rate = fallback_hourly(a) if hourly is None else np.asarray(hourly, dtype=float)
        return a.num(row["cost_key"]) * rate + 0 * np.asarray(salary, dtype=float)
    if row["cost_rule"] == FIXED_RULE:
        return a.num(row["cost_key"]) + 0 * np.asarray(salary, dtype=float)
    raise ValueError(f"Regra de custo desconhecida em data/interventions.csv: {row['cost_rule']}")


def tenure_years(hire_date, on) -> np.ndarray | float:
    """Years of tenure on a date (numbers or Series)."""
    days = (pd.Timestamp(on) - pd.to_datetime(hire_date))
    days = days.dt.days if isinstance(days, pd.Series) else days.days
    return np.asarray(days, dtype=float) / 365.25 if np.ndim(days) else days / 365.25


def replacement_share(a: Assumptions, tenure) -> np.ndarray | float:
    """Replacement cost as a share of the annual cost: a base for a newcomer plus a step per year of tenure, capped.
    Longer tenure means company-specific knowledge the substitute does not bring."""
    t = np.maximum(np.asarray(tenure, dtype=float), 0.0)
    share = np.minimum(a.num("cost.replacement_base") + a.num("cost.replacement_per_tenure_year") * t,
                       a.num("cost.replacement_max"))
    return float(share) if np.ndim(share) == 0 else share
