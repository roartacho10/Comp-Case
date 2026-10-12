"""Signals computed from raw data only (HRIS, events, benchmark, context).

This is what the system can observe. It never reads the hidden truth. In Phase 1 it
proves that the generated raw data reproduces exactly the signals drawn by the
world rules; in Phase 2 the rule engine builds on it.
"""

from __future__ import annotations

import pandas as pd

from src.assumptions import Assumptions

DAYS_PER_MONTH = 30.4375
DAYS_PER_YEAR = 365.25
CAUSES = ["remuneração", "crescimento"]  # causes the platform can detect and act on

CONTEXT_EVENT_TO_SIGNAL = {
    "proposta_externa": "external_offer",
    "fim_de_projeto_sem_escopo": "growth_request",
    "pedido_crescimento_sem_plano": "growth_request",
}


def milestones(a: Assumptions) -> list[int]:
    return sorted(int(v) for v in a.group("signals.milestone_years").values())


def milestone_active(hire_date: pd.Timestamp, t0: pd.Timestamp, years: list[int], window_days: float) -> bool:
    """True if the person completes one of the tenure milestones within the window after T0."""
    for m in years:
        delta = (hire_date + pd.DateOffset(years=m) - t0).days
        if 0 < delta <= window_days:
            return True
    return False


def compute_signals(tables: dict[str, pd.DataFrame], a: Assumptions) -> pd.DataFrame:
    """One row per active employee, one boolean column per signal."""
    t0 = a.date("general.reference_date")
    hris = tables["hris"]
    active = hris[hris["status"] == "ativo"].set_index("employee_id")
    bench = tables["benchmark"].drop_duplicates(["level", "country"]).set_index(["level", "country"])[
        "median_annual_brl"
    ]

    out = pd.DataFrame(index=active.index)

    # Compensation
    median = [bench[(lvl, ctry)] for lvl, ctry in zip(active["level"], active["country"])]
    compa = active["annual_cost_brl"] / pd.Series(median, index=active.index)
    out["compa_below"] = compa < a.num("signals.compa_threshold")
    days_since_pay_change = (t0 - pd.to_datetime(active["last_pay_change_date"])).dt.days
    out["no_raise"] = days_since_pay_change > a.num("signals.no_raise_months") * DAYS_PER_MONTH

    # Growth
    ref_years = a.group("signals.time_in_level_ref")
    days_in_level = (t0 - pd.to_datetime(active["last_promotion_date"])).dt.days
    threshold_days = active["level"].map(ref_years) * a.num("signals.time_in_level_multiple") * DAYS_PER_YEAR
    out["time_in_level"] = days_in_level >= threshold_days
    years = milestones(a)
    window = a.num("signals.milestone_window_months") * DAYS_PER_MONTH
    out["tenure_milestone"] = [
        milestone_active(h, t0, years, window) for h in pd.to_datetime(active["hire_date"])
    ]

    # Context (career conversations and project records)
    ctx = tables["context"].copy()
    ctx["date"] = pd.to_datetime(ctx["date"])
    recent = ctx[(t0 - ctx["date"]).dt.days <= a.num("signals.context_window_months") * DAYS_PER_MONTH]
    recent = recent[recent["extracted_event"].isin(CONTEXT_EVENT_TO_SIGNAL)]
    for signal in ("external_offer", "growth_request"):
        events = [e for e, s in CONTEXT_EVENT_TO_SIGNAL.items() if s == signal]
        ids = set(recent.loc[recent["extracted_event"].isin(events), "employee_id"])
        out[signal] = out.index.isin(ids)

    return out[a.signals["signal"].tolist()].astype(bool)
