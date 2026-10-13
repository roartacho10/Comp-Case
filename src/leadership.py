"""Leadership view: where the risk is, how much value is at stake and what the decisions produced.
Aggregated only (no names), with groups below the minimum size hidden."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import Assumptions
from src.interventions import is_recurring
from src.signals import DAYS_PER_MONTH
from src.periods import OUTCOME_WINDOW_MONTHS


def at_t0(world: dict, a: Assumptions, decisions: pd.DataFrame) -> dict:
    engine = world["engine"]
    cases = engine.cases.copy()
    hris = world["public"]["hris"]
    active = hris[hris["status"] == "ativo"]
    replacement = cases["replacement_cost"]
    exits_no_action = float(cases["exit_window_no_action"].sum())
    loss = float((cases["exit_window_no_action"] * replacement).sum())
    d = decisions.set_index("employee_id")
    exits_with_decisions = float((1 - d["system_prediction"]).sum())
    loss_with_decisions = float(((1 - d["system_prediction"]) * replacement.set_axis(cases["employee_id"]).reindex(d.index)).sum())

    area_cause = cases.groupby(["area", "cause"]).size().reset_index(name="cases")

    min_group = a.int("privacy.min_group_size")
    team_size = active[active["role"] == "Individual"].groupby("team_id").size()
    by_team = cases[cases["role"] == "Individual"].groupby("team_id").agg(
        cases=("employee_id", "size"), cause=("cause", lambda s: s.value_counts().idxmax()))
    teams = by_team.join(team_size.rename("people")).join(
        world["public"]["managers"].dropna(subset=["team_id"]).set_index("team_id")["area"])
    teams = teams[teams["people"] >= min_group]
    teams["share"] = teams["cases"] / teams["people"]
    teams = teams.sort_values(["share", "cases"], ascending=False).reset_index()

    by_intervention = d.groupby("intervention").agg(cases=("intervention", "size"), cost=("cost_window", "sum")).reset_index()
    # Share that followed the suggestion, among decided cases; "—" when no case had this option as the suggestion.
    dec = d[d["decided"]]
    by_intervention["followed"] = [
        dec.loc[dec["intervention"] == i, "followed"].mean() if (d["recommended"] == i).any() else float("nan")
        for i in by_intervention["intervention"]]
    return dict(
        employees=len(active), cases=len(cases), exits_no_action=exits_no_action, loss=loss,
        regretted_loss=loss * a.num("exit.regretted_share"), regretted_share=a.num("exit.regretted_share"), exits_with_decisions=exits_with_decisions,
        loss_with_decisions=loss_with_decisions, intervention_cost=float(d["cost_window"].sum()),
        followed=float(d.loc[d["decided"], "followed"].mean()), area_cause=area_cause, teams=teams, by_intervention=by_intervention,
        turnover_12m=_turnover(hris, a),
    )


def after_window(world: dict, a: Assumptions, t0_view: dict, results: dict) -> dict:
    learn, outcomes = results["learning"], results["outcomes"]
    closed = learn["closed"]
    s = learn["summary"].iloc[0]
    cases = world["engine"].cases.set_index("employee_id")
    window = OUTCOME_WINDOW_MONTHS
    replacement = cases["replacement_cost"].reindex(closed["employee_id"]).to_numpy()
    expected_exit = cases.loc[closed["employee_id"], "exit_window_no_action"].to_numpy()
    exited = (~closed["stayed"].astype(bool)).to_numpy(dtype=float)
    avoided = t0_view["exits_no_action"] - s["exits_realized"]
    # Each case weighs by its own replacement cost: (chance of leaving with no action − left or not) × replacement.
    saved = float(((expected_exit - exited) * replacement).sum())
    # Cost actually paid: recurring costs (salary adjustment) only while the person stayed; one-off costs in full.
    recurring = closed["intervention"].map({i: is_recurring(a, i) for i in a.interventions["intervention"]}).fillna(False)
    months_paid = closed["exit_month"].astype(float).fillna(window).clip(upper=window).where(~closed["stayed"], window)
    cost_paid = float(np.where(recurring, closed["cost_window"] * months_paid / window, closed["cost_window"]).sum())

    c = closed.assign(no_action=cases.loc[closed["employee_id"], "exit_window_no_action"].values,
                      cause=cases.loc[closed["employee_id"], "cause"].values)
    by_cause = c.groupby("cause").agg(cases=("employee_id", "size"), expected=("no_action", "sum"),
                                      realized=("stayed", lambda x: int((~x).sum()))).reset_index()
    by_cause["avoided"] = by_cause["expected"] - by_cause["realized"]
    followed = c[c["decided"]].groupby("followed")["stayed"].agg(["mean", "size"])  # no decision: neither

    hris = world["public"]["hris"]
    t0 = a.date("general.reference_date")
    former = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
    former = former[(t0 - pd.to_datetime(former["exit_date"])).dt.days <= window * DAYS_PER_MONTH]  # same length as after
    active = int((hris["status"] == "ativo").sum())
    return dict(
        exits_realized=int(s["exits_realized"]), avoided=float(avoided), saved=saved, cost_paid=cost_paid,
        value=float(saved - cost_paid),
        return_per_real=float(saved / cost_paid) if cost_paid else float("nan"),
        by_cause=by_cause,
        stay_followed=float(followed.loc[True, "mean"]) if True in followed.index else float("nan"),
        stay_diverged=float(followed.loc[False, "mean"]) if False in followed.index else float("nan"),
        n_followed=int(followed.loc[True, "size"]) if True in followed.index else 0,
        n_diverged=int(followed.loc[False, "size"]) if False in followed.index else 0,
        company_exits=int((~outcomes["stayed"]).sum()), company_regretted=int(outcomes["regretted"].sum()),
        turnover_before=len(former) / active, turnover_after=int((~outcomes["stayed"]).sum()) / active,
        regretted_before=int(former["regretted"].astype(bool).sum()),
    )


def _turnover(hris: pd.DataFrame, a: Assumptions) -> float:
    t0 = a.date("general.reference_date")
    former = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
    recent = former[(t0 - pd.to_datetime(former["exit_date"])).dt.days <= 12 * DAYS_PER_MONTH]  # "últimos 12 meses"
    return len(recent) / int((hris["status"] == "ativo").sum())
