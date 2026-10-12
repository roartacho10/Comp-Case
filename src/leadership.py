"""Leadership view: where the risk is, how much value is at stake and what the decisions produced.
Aggregated only (no names), with groups below the minimum size hidden."""

from __future__ import annotations

import pandas as pd

from src.assumptions import Assumptions


def at_t0(world: dict, a: Assumptions, decisions: pd.DataFrame) -> dict:
    engine = world["engine"]
    cases = engine.cases.copy()
    hris = world["public"]["hris"]
    active = hris[hris["status"] == "ativo"]
    replacement = a.num("cost.replacement_share") * cases["salary"]
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

    by_intervention = d.groupby("intervention").agg(cases=("intervention", "size"), cost=("cost_window", "sum"),
                                                   followed=("followed", "mean")).reset_index()
    return dict(
        employees=len(active), cases=len(cases), exits_no_action=exits_no_action, loss=loss,
        regretted_loss=loss * a.num("exit.regretted_share"), exits_with_decisions=exits_with_decisions,
        loss_with_decisions=loss_with_decisions, intervention_cost=float(d["cost_window"].sum()),
        followed=float(d["followed"].mean()), area_cause=area_cause, teams=teams, by_intervention=by_intervention,
        turnover_12m=_turnover(hris, a),
    )


def after_window(world: dict, a: Assumptions, t0_view: dict, results: dict) -> dict:
    learn, outcomes = results["learning"], results["outcomes"]
    closed = learn["closed"]
    s = learn["summary"].iloc[0]
    cases = world["engine"].cases.set_index("employee_id")
    replacement = (a.num("cost.replacement_share") * cases["salary"]).reindex(closed["employee_id"])
    avoided = t0_view["exits_no_action"] - s["exits_realized"]
    avg_replacement = float(replacement.mean())
    saved = avoided * avg_replacement

    c = closed.assign(no_action=cases.loc[closed["employee_id"], "exit_window_no_action"].values,
                      cause=cases.loc[closed["employee_id"], "cause"].values)
    by_cause = c.groupby("cause").agg(cases=("employee_id", "size"), expected=("no_action", "sum"),
                                      realized=("stayed", lambda x: int((~x).sum()))).reset_index()
    by_cause["avoided"] = by_cause["expected"] - by_cause["realized"]
    followed = c.groupby("followed")["stayed"].agg(["mean", "size"])

    hris = world["public"]["hris"]
    former = hris[(hris["status"] == "desligado") & (hris["exit_type"] == "voluntário")]
    active = int((hris["status"] == "ativo").sum())
    return dict(
        exits_realized=int(s["exits_realized"]), avoided=float(avoided), saved=float(saved),
        value=float(saved - t0_view["intervention_cost"]), avg_replacement=avg_replacement,
        return_per_real=float(saved / t0_view["intervention_cost"]) if t0_view["intervention_cost"] else float("nan"),
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
    recent = former[(t0 - pd.to_datetime(former["exit_date"])).dt.days <= 365]
    return len(recent) / int((hris["status"] == "ativo").sum())
